## execute_generator

Pulls respective applicationj from GitHub, generates JAR file and runs is using the following arguments:

### Arguments:

- **String**: either *syntheagecco* or *syntheakds* for generation of data with either application
- **int**: number of patient records to be generated 

## analysis_script

Analyses FHIR instance data on a given FHIR Repository

### Arguments:

- **String**: URL of FHIR Server on which data should be analyzed
- **int**: page size of FHIR Search requests. In case of large data volumes setting it to a high value is advisable.
Defaults to 20