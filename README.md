## execute_generator

Pulls respective application from GitHub, generates JAR file and runs is using the following arguments:

### Arguments:

- **String**: either *syntheagecco* or *syntheakds* for generation of data with either application
- **int**: number of patient records to be generated 

## analysis_script

Analyses FHIR instance data on a given FHIR Repository

### Arguments:

- **String**: URL of FHIR server on which data should be analyzed
- **int**: page size of FHIR Search requests. In case of large data volumes setting it to a high value is advisable.
Defaults to 20

## run_test_queries:

Runs benchmark on a NUM node by running an assortement of queries against it. Note that one can add additional queries by putting them into the folders inside the *queries* directory.
The script runs each individual query multiple times and calculates the average time.

### Arguments:

- **String**: URL of the FHIR server (which is part of the NUM node) on which the benchmark shall be performed. (*Default*: *http://locahost/api/v1/query-handler*)
- **String**: User name of the user trying to access the node
- **String**: Password of the user trying to access the node