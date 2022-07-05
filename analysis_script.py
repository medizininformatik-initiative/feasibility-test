import csv
import datetime
import json
import logging
from logging import basicConfig
import os
import queue
import sys
import threading
import uuid
import time
import argparse
from pathlib import Path

import urllib3

output_path = os.path.join('output', 'analysis')
log_path = 'log'
log_file = os.path.join(log_path, 'analysis.log')

resource_types = ["Condition", "Observation", "Procedure", "MedicationAdministration", "Immunization", "Medication",
                  "MedicationRequest"]
code_attributes = {"Condition": "code",
                   "Observation": "code",
                   "Procedure": "code",
                   "MedicationAdministration": "medicationCodeableConcept",
                   "Immunization": "vaccineCode",
                   "Medication": "medicationCodeableConcept",
                   "MedicationRequest": "medicationCodeableConcept"}

logger = logging.getLogger('root')


class FHIRClient:

    def __init__(self, url, count, user, pw, cert_reqs=None):
        self.__client = urllib3.PoolManager(num_pools=20, block=True, cert_reqs=cert_reqs)
        self.__url = url
        self.__count = count
        if user is None or pw is None:
            self.__headers = None
        else:
            self.__headers = urllib3.make_headers(basic_auth='{u}:{p}'.format(u=user, p=pw))
        self.__request_q = queue.Queue()
        self.result_q = queue.Queue(maxsize=50)
        self.request_tracker = set()

    def search(self, resource):
        logger.info("Starting search for {r} ...".format(r=resource))
        search_string = "{url}/{r}?_count={c}".format(url=self.__url, r=resource, c=self.__count)
        request_id = str(uuid.uuid4())
        self.__request_q.put((request_id, resource, search_string))
        self.request_tracker.add(request_id)
        if len(self.request_tracker) < 20:
            SearchThread(name='', client=self.__client, headers=self.__headers, request_q=self.__request_q,
                         result_q=self.result_q,
                         request_tracker=self.request_tracker).start()


class AnalysisManager:

    def __init__(self, url, count, user, pw, ignore_cert_reqs):
        cert_reqs = None
        if ignore_cert_reqs:
            cert_reqs = 'CERT_NONE'
        self.__fhir_client = FHIRClient(url, count, user, pw, cert_reqs)
        self.__results = self.__init_result_dict()

    @staticmethod
    def __init_result_dict():
        results = {}
        for resource_type in resource_types:
            results[resource_type] = {}
        return results

    def run(self):
        analyzer_threads = []
        num_threads = 4

        t1 = datetime.datetime.now()
        for resource_type in resource_types:
            self.__fhir_client.search(resource_type)

        for i in range(num_threads):
            t = AnalyzerThread(str(i), q=self.__fhir_client.result_q, results=self.__results)
            t.start()
            analyzer_threads.append(t)

        while not (self.__fhir_client.result_q.empty() and len(self.__fhir_client.request_tracker) <= 0):
            time.sleep(0.1)

        for t in analyzer_threads:
            t.finish_once_empty(True)
        for t in analyzer_threads:
            t.join()
        t2 = datetime.datetime.now()
        d_analysis = t2 - t1

        logger.info('Time elapsed: {s} seconds {ms} microseconds'.format(s=d_analysis.seconds,
                                                                         ms=d_analysis.microseconds))
        return self.__results


class SearchThread(threading.Thread):

    def __init__(self, name, client, headers, request_q, result_q, request_tracker):
        super(SearchThread, self).__init__()
        self.__name = name
        self.__client = client
        self.__headers = headers
        self.__request_q = request_q
        self.__result_q = result_q
        self.__request_tracker = request_tracker

    def run(self):
        logger.debug("Starting search thread ...")
        while not self.__request_q.empty():
            request_id, resource_type, request_url = self.__request_q.get()
            logger.debug("Requesting {r} instances".format(r=resource_type))
            response = parse_response(self.__client.request('GET', request_url, headers=self.__headers))
            try:
                self.__result_q.put((resource_type, response['entry']))
                next = response['link'][1]
                if next['relation'] == 'next':
                    modified_next_url = url + '/' + '/'.join(next['url'].split('/')[-2:])
                    self.__request_q.put((request_id, resource_type, modified_next_url))
                else:
                    logger.info('Finished requesting {r} instances'.format(r=resource_type))
                    self.__request_tracker.remove(request_id)
            except (IndexError, KeyError):
                logger.info('Finished requesting {r} instances'.format(r=resource_type))
                self.__request_tracker.remove(request_id)
        logger.info("Shutting down search thread")


class AnalyzerThread(threading.Thread):

    def __init__(self, name, q, results):
        super(AnalyzerThread, self).__init__()
        self.__finish = False
        self.__name = name
        self.__q = q
        self.__results = results

    def finish_once_empty(self, finish):
        self.__finish = finish

    def run(self):
        logger.info("AnalyzerThread {n}: Starting up ...".format(n=self.__name))
        while not self.__q.empty or not self.__finish:
            try:
                resource_type, entries = self.__q.get(block=True, timeout=0.1)
                result_for_resource = self.__results[resource_type]
                logger.debug("AnalyzerThread {n}: Processing {r} ressources ...".format(n=self.__name, r=resource_type))
                code_attr = code_attributes[resource_type]
                for entry in entries:
                    try:
                        coding = entry['resource'][code_attr]['coding']
                        for code in coding:
                            try:
                                code_string = code['system'] + '#' + code['code']
                                if code_string in result_for_resource:
                                    result_for_resource[code_string] += 1
                                else:
                                    result_for_resource[code_string] = 1
                            except KeyError:
                                pass
                    except KeyError:
                        print(entry)
            except queue.Empty:
                logger.debug("AnalyzerThread {n}: Retrying lock ...".format(n=self.__name))
        logger.info("AnalyzerThread {n}: Finished".format(n=self.__name))


def write_results_as_csv(results):
    for file in os.listdir(output_path):
        os.remove(os.path.join(output_path, file))
    for resource_type in resource_types:
        with open(os.path.join(output_path, resource_type + '.csv'), 'w+', encoding='UTF-8') as file:
            writer = csv.writer(file)
            # Header
            writer.writerow(['system#code', 'count'])
            # Rows
            for key, value in results[resource_type].items():
                writer.writerow([key, value])


def parse_response(response):
    return json.loads(response.data.decode('utf-8'))


def config_logging():
    Path(log_path).mkdir(parents=True, exist_ok=True)
    open(log_file, 'w+')

    formatter = logging.Formatter('%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s')

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    file_handler = logging.FileHandler(filename=log_file, mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)


def config_arg_parser():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('url', action='store', help='URL of the server to which requests are sent')
    arg_parser.add_argument('-c', '--count', action='store', default=100, type=int, help='Number of returned '
                                                                                         'resources per request')
    arg_parser.add_argument('-a', '--authentication', action='store', nargs=2, default=[None, None], help='User name '
                                                                                                          'and '
                                                                                                          'password '
                                                                                                          'for basic '
                                                                                                          'auth if '
                                                                                                          'required')
    arg_parser.add_argument('-i', '--ignore-certificates', action='store_true', help='If provided, all certificates '
                                                                                     'are ignored when connecting '
                                                                                     'with the server. Only use this '
                                                                                     'if you know that it is safe!')
    return arg_parser


if __name__ == '__main__':
    Path(output_path).mkdir(parents=True, exist_ok=True)

    config_logging()
    logging.basicConfig(level=logging.INFO)

    parser = config_arg_parser()
    args = parser.parse_args()
    print(vars(args))

    url = args.url
    count = args.count
    user, password = args.authentication
    ignore_cert_reqs = args.ignore_certificates

    manager = AnalysisManager(url, count, user, password, ignore_cert_reqs)
    results = manager.run()

    write_results_as_csv(results)
