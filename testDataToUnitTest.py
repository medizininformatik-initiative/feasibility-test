import os
from StructuredQuery import *

mapped_term_codes = []

scriptDir = os.path.dirname(os.path.realpath(__file__))
testCasesDir = os.path.join(scriptDir, "testCases")

with open(os.path.join(scriptDir, "TermCodeMapping.json")) as mapping_file:
    mapping_json = json.load(mapping_file)
    for mapping in mapping_json:
        mapped_term_codes.append(TermCode(**mapping['key']))


def generate_unit_test(bundle):
    os.makedirs(testCasesDir, exist_ok = True)

    for entry in bundle["entry"]:
        resource = entry["resource"]
        resource_type = resource["resourceType"]
        sq = StructuredQuery()
        if resource_type == "Condition":
            sq = generate_condition_sq(resource)
        elif resource_type == "Observation":
            sq = generate_observation_sq(resource)
        elif resource_type == "Immunization":
            sq = generate_immunization_sq(resource)
        elif resource_type == "MedicationStatement":
            sq = generate_medication_statement_sq(resource)
        elif resource_type == "Procedure":
            sq = generate_procedure_sq(resource)
        elif resource_type == "DiagnosticReport":
            sq = generate_diagnostic_report_sq(resource)
        elif resource_type == "Patient":
            sq_age = generate_age_sq(resource)
            sq_age.version = "http://to_be_decided.com/draft-1/schema#"
            write_sq_to_file(sq_age, resource, "1-age")
            sq_ethnic_group = generate_ethnic_group_sq(resource)
            sq_ethnic_group.version = "http://to_be_decided.com/draft-1/schema#"
            write_sq_to_file(sq_ethnic_group, resource, "1-ethnic_group")
            continue
        elif resource_type == "Organization":
            continue
        elif resource_type == "Encounter":
            continue
        elif resource_type == "Consent":
            continue
        else:
            print(resource_type)
            continue
        sq.version = "http://to_be_decided.com/draft-1/schema#"
        write_sq_to_file(sq, resource)


def write_sq_to_file(structured_query, resource, file_name = None):
    if file_name:
        file = open(os.path.join(testCasesDir, file_name + ".json"), 'w')
    else:
        file = open(os.path.join(testCasesDir, resource["identifier"][0]["value"].split(".")[-1] + ".json"), 'w')
    file.write(structured_query.to_json())
    file.close()


def generate_age_sq(patient_resource):
    age_sq = StructuredQuery()
    for extension in patient_resource["extension"]:
        if extension["url"] == "https://www.netzwerk-universitaetsmedizin.de/fhir/StructureDefinition/age":
            for nested_extension in extension["extension"]:
                if nested_extension["url"] == "age":
                    age_term_code = TermCode("http://snomed.info/sct", "424144002", "Current chronological age ("
                                                                                    "observable entity)")
                    value_filter = generate_comparator_filter(nested_extension["valueAge"])
                    age_sq.inclusionCriteria.append(Criterion(age_term_code, value_filter))
    return age_sq


def generate_ethnic_group_sq(patient_resource):
    ethnic_group_sq = StructuredQuery()
    for extension in patient_resource["extension"]:
        if extension["url"] == "https://www.netzwerk-universitaetsmedizin.de/fhir/StructureDefinition/ethnic-group":
            ethnic_group_term_code = TermCode("http://snomed.info/sct", "372148003", "Ethnic group (ethnic group)")
            value_coding = extension["valueCoding"]
            value_filter = ConceptFilter([TermCode(value_coding["system"], value_coding["code"], "")])
            ethnic_group_sq.inclusionCriteria.append(Criterion(ethnic_group_term_code, value_filter))
            break
    return ethnic_group_sq


def generate_condition_sq(condition_resource):
    condition_sq = StructuredQuery()
    for coding_term_code in get_term_codes(condition_resource["code"]["coding"]):
        value_filter = None
        if "severity" in condition_resource:
            value_filter = generate_concept_filter(condition_resource["severity"])
        condition_sq.inclusionCriteria.append(Criterion(coding_term_code, value_filter))
    return condition_sq


def generate_observation_sq(observation_resource):
    observation_sq = StructuredQuery()
    for coding_term_code in get_term_codes(observation_resource["code"]["coding"]):
        value_filter = ValueFilter
        if "valueCodeableConcept" in observation_resource:
            value_filter = generate_concept_filter(observation_resource["valueCodeableConcept"])
        elif "valueQuantity" in observation_resource:
            value_filter = generate_comparator_filter(observation_resource["valueQuantity"])
        else:
            value_filter = None
        observation_sq.inclusionCriteria.append(Criterion(coding_term_code, value_filter))
    return observation_sq


def generate_concept_filter(codeable_concept):
    return ConceptFilter(get_term_codes(codeable_concept["coding"]))


def generate_comparator_filter(quantity_value):
    return QuantityComparatorFilter("eq", quantity_value["value"], Unit(quantity_value["code"], quantity_value["unit"]))


def generate_immunization_sq(immunization_resource):
    immunization_sq = StructuredQuery()
    for coding_term_code in get_term_codes(immunization_resource["vaccineCode"]["coding"]):
        immunization_sq.inclusionCriteria.append(Criterion(coding_term_code, None))
    return immunization_sq


def generate_medication_statement_sq(medication_statement_resource):
    medication_statement_sq = StructuredQuery()
    for coding_term_code in get_term_codes(medication_statement_resource["medicationCodeableConcept"]["coding"]):
        medication_statement_sq.inclusionCriteria.append(Criterion(coding_term_code, None))
    return medication_statement_sq


def generate_procedure_sq(procedure_resource):
    procedure_sq = StructuredQuery()
    for coding_term_code in get_term_codes(procedure_resource["code"]["coding"]):
        procedure_sq.inclusionCriteria.append(Criterion(coding_term_code, None))
    return procedure_sq


def generate_diagnostic_report_sq(diagnostic_report_resource):
    diagnostic_report_sq = StructuredQuery()
    for coding_term_code in get_term_codes(diagnostic_report_resource["code"]["coding"]):
        diagnostic_report_sq.inclusionCriteria.append(Criterion(coding_term_code, None))
    return diagnostic_report_sq


def get_term_codes(codings):
    mapped_results = []
    result = []
    for coding in codings:
        coding_term_code = TermCode(coding["system"], coding["code"], "")
        if coding_term_code in mapped_term_codes:
            mapped_results.append(coding_term_code)
        result.append(coding_term_code)
    if not mapped_results:
        return result
    return mapped_results

