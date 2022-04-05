import csv
import datetime
import json
import logging
import os
import queue
import sys
import threading
import uuid
import time

import urllib3

resource_types = ["Condition", "Observation", "Procedure", "MedicationAdministration", "Immunization", "Medication"]

class FHIRClient:

    def __init__(self, url, count):
        self.__client = urllib3.PoolManager(num_pools=20, block=True)
        self.__url = url
        self.__count = count
        self.__request_q = queue.Queue()
        self.result_q = queue.Queue(maxsize=50)
        self.request_tracker = set()

    def search(self, resource):
        logging.info("Starting search for {r} ...".format(r=resource))
        search_string = "{url}/{r}/_search?_count={c}".format(url=self.__url, r=resource, c=self.__count)
        request_id = str(uuid.uuid4())
        self.__request_q.put((request_id, resource, search_string))
        self.request_tracker.add(request_id)
        if len(self.request_tracker) < 20:
            SearchThread(name='', client=self.__client, request_q=self.__request_q, result_q=self.result_q,
                         request_tracker=self.request_tracker).start()


class AnalysisManager:

    def __init__(self, url, count):
        self.__fhir_client = FHIRClient(url, count)
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

        logging.info('Time elapsed: {s} seconds {ms} microseconds'.format(s=d_analysis.seconds,
                                                                          ms=d_analysis.microseconds))
        return self.__results


class SearchThread(threading.Thread):

    def __init__(self, name, client, request_q, result_q, request_tracker):
        super(SearchThread, self).__init__()
        self.__name = name
        self.__client = client
        self.__request_q = request_q
        self.__result_q = result_q
        self.__request_tracker = request_tracker

    def run(self):
        logging.debug("Starting search thread ...")
        while not self.__request_q.empty():
            request_id, resource_type, request_url = self.__request_q.get()
            response = parse_response(self.__client.request('GET', request_url))
            try:
                self.__result_q.put((resource_type, response['entry']))
                next = response['link'][1]
                if next['relation'] == 'next':
                    self.__request_q.put((request_id, resource_type, next['url']))
                else:
                    self.__request_tracker.remove(request_id)
            except (IndexError, KeyError):
                self.__request_tracker.remove(request_id)
        logging.debug("Shutting down search thread")

    def paging_search(self, resource, q):
        # Initial search request
        logging.info("Searching for {r} ...".format(r=resource))
        try:
            response = parse_response(self.search(resource))
            q.put([resource, response['entry']])
            next = response['link'][1]
            while next['relation'] == 'next':
                response = self.__get_next(next['url'])
                q.put((resource, response['entry']))
                next = response['link'][1]
        except IndexError:
            pass
        except KeyError:
            pass
        logging.info("Searching for {r} finished".format(r=resource))


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
        logging.info("AnalyzerThread {n}: Starting up ...".format(n=self.__name))
        while not self.__q.empty or not self.__finish:
            try:
                resource_type, entries = self.__q.get(block=True, timeout=0.1)
                result_for_resource = self.__results[resource_type]
                logging.debug(
                    "AnalyzerThread {n}: Processing {r} ressources ...".format(n=self.__name, r=resource_type))
                code_attr = 'code'
                if resource_type == 'Immunization':
                    code_attr = 'vaccineCode'
                for entry in entries:
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
            except queue.Empty:
                logging.debug("AnalyzerThread {n}: Retrying lock ...".format(n=self.__name))
        logging.info("AnalyzerThread {n}: Finished".format(n=self.__name))


def write_results_as_csv(results):
    for file in os.listdir('output'):
        os.remove('output/' + file)
    for resource_type in resource_types:
        with open('output/{r}.csv'.format(r=resource_type), 'w+', encoding='UTF-8') as file:
            writer = csv.writer(file)
            # Header
            writer.writerow(['system#code', 'count'])
            # Rows
            for key, value in results[resource_type].items():
                writer.writerow([key, value])


def parse_response(response):
    return json.loads(response.data.decode('utf-8'))


if __name__ == '__main__':
    url = sys.argv[1]
    assert url is not None, "A URL has to be provided!"

    count = 20
    if sys.argv[2] is not None:
        count = sys.argv[2]

    logging.basicConfig(level=logging.INFO)
    manager = AnalysisManager(url, count)
    results = manager.run()

    write_results_as_csv(results)
