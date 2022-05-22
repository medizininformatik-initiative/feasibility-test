import json
import os
import urllib3
import sys
import time

query_location = 'queries'
query_types = ['single_criteria', 'complex', 'frequent', 'special']
colors = {'green': '\033[92m',
          'blue': '\033[94m',
          'cyan': '\033[96m',
          'red': '\033[1,31m',
          'endc': '\033[0m'}


def load_queries():
    queries = dict()
    for query_type in query_types:
        query_type_dir = os.path.join(query_location, query_type)
        queries[str(query_type)] = [(query, open(os.path.join(query_type_dir, query), 'r').read()) for query in
                                    os.listdir(query_type_dir)]
    return queries


def color_string(str, color):
    try:
        return colors[color] + str + colors['endc']
    except KeyError:
        print(colors['red'] + 'No matching color found for name {name}!'.format(name=color))
        return str


class ABIDEClient:
    __url = 'http://locahost/api/v1/query-handler'
    __headers = None
    __client = urllib3.PoolManager(num_pools=1, block=True, cert_reqs='CERT_NONE')

    def __init__(self, url, credentials):
        self.__url = url + '/api/v1/query-handler'
        self.__credentials = credentials
        self.__headers = urllib3.make_headers(basic_auth='{u}:{pw}'.format(u=credentials[0], pw=credentials[1]))
        self.__headers['Content-Type'] = 'application/json'

    def run_query(self, query_json_str):
        return self.__client.request(method='POST', url=self.__url + '/run-query', headers=self.__headers,
                                     body=query_json_str)

    def get_result(self, result_url):
        return self.__client.request(method='GET', url=result_url, headers=self.__headers)

    def run_query_and_get_result(self, query_json_str):
        response = self.run_query(query_json_str)
        result_url = response.headers['Location']
        result = self.get_result(result_url)
        return json.loads(result.data.decode('utf-8'))

    # TODO: add round trip time as a consideration
    def benchmark_query(self, query_json_str):
        start = time.perf_counter()
        self.run_query_and_get_result(query_json_str)
        end = time.perf_counter()
        return end - start


class Benchmark:

    __runs = 10
    __categories = query_types
    __client = None

    def __init__(self, runs, categories, url, credentials):
        self.__runs = runs
        self.__categories = categories
        self.__client = ABIDEClient(url, credentials)

    def run(self):
        queries = load_queries()
        factor = 1000/self.__runs
        print(color_string('[#] Running benchmark ...', 'blue'))
        print('\tNumber of runs: ' + str(self.__runs))
        print('\tOn categories: ' + ', '.join(category for category in self.__categories))
        for k, v in queries.items():
            print(color_string('[#] Running queries of type ', 'blue') + color_string(k, 'green'))
            for t in v:
                total_time = 0
                for _ in range(0, self.__runs):
                    total_time += self.__client.benchmark_query(t[1])
                print('\t\t{query_name}: {time_elapsed} ms'.format(query_name=t[0], time_elapsed=total_time * factor))


if __name__ == '__main__':
    # Currently enabled since the certificate is self-signed
    urllib3.disable_warnings()

    benchmark = Benchmark(10, query_types, sys.argv[1], (sys.argv[2], sys.argv[3]))
    benchmark.run()
