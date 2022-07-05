## execute_generator

Pulls respective application from GitHub, generates JAR file and runs is using the following arguments:

### Arguments:

- **String**: either *syntheagecco* or *syntheakds* for generation of data with either application
- **int**: number of patient records to be generated 

## analysis_script

Analyses FHIR instance data on a given FHIR Repository

### Arguments:
- **Note**: All positional and optional arguments can be viewed with description using the *-h* option

**Positional arguments:**

| Name | Type | Description |
| :---: | :---: | :---: |
| url | String | URL of the server to which requests are sent |

**Optional arguments:**

| Short | Long | Arguments | Description |
| :---: | :---: | :---: | :---: |
| -h | --help |  | See **Note** |
| -c | --count | <count: *int*> | Number of returned resources per request (default: 100)|
| -a | --authentication | <user: *string*> <password: *string*> | User name and password for basic auth if required |
| -i | --ignore-certificates |  | If provided, all certificates are ignored when connecting with the server. **Only use this if you know that it is safe!** |

## run_test_queries:

Runs benchmark on a NUM node by running an assortement of queries against it. Note that one can add additional queries by putting them into the folders inside the *queries* directory.
The script runs each individual query multiple times and calculates the average time.

### Arguments:

- **String**: URL of the FHIR server (which is part of the NUM node) on which the benchmark shall be performed. (*Default*: *http://locahost/api/v1/query-handler*)
- **String**: User name of the user trying to access the node
- **String**: Password of the user trying to access the node