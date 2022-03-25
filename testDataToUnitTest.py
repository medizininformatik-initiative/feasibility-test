import os
import uuid

from StructuredQuery import *

from jsonschema import validate


mapped_term_codes = []

scriptDir = os.path.dirname(os.path.realpath(__file__))
testCasesDir = os.path.join(scriptDir, "testCases")

with open(os.path.join(scriptDir, "feasibility-term-code-mapping.json")) as mapping_file:
    mapping_json = json.load(mapping_file)
    for mapping in mapping_json:
        mapped_term_codes.append(TermCode(**mapping['key']))


def safe_get(dictionary, *keys):
    for key in keys:
        try:
            dictionary = dictionary[key]
        except KeyError:
            return None
    return dictionary


def generate_unit_test(bundle):
    os.makedirs(testCasesDir, exist_ok=True)
    for entry in bundle["entry"]:
        resource = entry["resource"]
        resource_type = resource["resourceType"]
        if resource_type == "Condition":
            sq = generate_condition_sq(resource)
        elif resource_type == "Observation":
            if (safe_get(resource, "meta", "profile")[0].split("/")[-1]) == "history-of-travel":
                sq = generate_history_of_travel_sq(resource)
            elif (safe_get(resource, "meta", "profile")[0].split("/")[-1]) == "sofa-score":
                sq = generate_sofa_score_sq(resource)
            else:
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
        if not sq:
            print(resource_type)
            continue
        sq.version = "http://to_be_decided.com/draft-1/schema#"
        write_sq_to_file(sq, resource)


def write_sq_to_file(structured_query, resource, file_name=None):
    if file_name:
        file_name = os.path.join(testCasesDir, file_name + ".json")
    else:
        file_name = os.path.join(testCasesDir, resource["meta"]["profile"][0].split("/")[-1] + "-" +
                                 str(uuid.uuid4()) + ".json")
    # simultaneous reading and writing didnt work.
    file = open(file_name, 'w')
    file.write(structured_query.to_json())
    file.close()
    file = open(file_name, 'r')
    validate(instance=json.load(file), schema=json.load(open("json_schema_sqv2.json")))
    file.close()


def generate_age_sq(patient_resource):
    age_sq = StructuredQuery()
    for extension in patient_resource["extension"]:
        if extension["url"] == "https://www.netzwerk-universitaetsmedizin.de/fhir/StructureDefinition/age":
            for nested_extension in extension["extension"]:
                if nested_extension["url"] == "age":
                    age_term_code = TermCode("http://snomed.info/sct", "424144002", "Current chronological age ("
                                                                                    "observable entity)")
                    value_filter = generate_comparator_filter(nested_extension["valueQuantity"])
                    age_sq.inclusionCriteria.append([Criterion([age_term_code], value_filter)])
                    break
    return age_sq


def generate_ethnic_group_sq(patient_resource):
    ethnic_group_sq = StructuredQuery()
    for extension in patient_resource["extension"]:
        if extension["url"] == "https://www.netzwerk-universitaetsmedizin.de/fhir/StructureDefinition/ethnic-group":
            ethnic_group_term_code = TermCode("http://snomed.info/sct", "372148003", "Ethnic group (ethnic group)")
            value_coding = extension["valueCoding"]
            value_filter = ConceptFilter([TermCode(value_coding["system"], value_coding["code"], "")])
            ethnic_group_sq.inclusionCriteria.append([Criterion([ethnic_group_term_code], value_filter)])
            break
    return ethnic_group_sq


def generate_condition_sq(condition_resource):
    if "modifierExtension" in condition_resource:
        return None
    if "verificationStatus" in condition_resource and not any(
            coding["code"] == "confirmed" for coding in condition_resource["verificationStatus"]["coding"]):
        return None
    condition_sq = StructuredQuery()
    semantic_equivalent = []
    for coding_term_code in get_term_codes(condition_resource["code"]["coding"]):
        value_filter = None
        if "severity" in condition_resource:
            value_filter = generate_concept_filter(condition_resource["severity"])
        semantic_equivalent.append(Criterion([coding_term_code], value_filter))
    condition_sq.inclusionCriteria.append(semantic_equivalent)
    return condition_sq


def generate_observation_sq(observation_resource):
    if "hasMember" in observation_resource:
        return None
    observation_sq = StructuredQuery()
    semantic_equivalent = []
    for coding_term_code in get_term_codes(observation_resource["code"]["coding"]):
        value_filter = ValueFilter
        if "valueCodeableConcept" in observation_resource:
            value_filter = generate_concept_filter(observation_resource["valueCodeableConcept"])
        elif "valueQuantity" in observation_resource:
            value_filter = generate_comparator_filter(observation_resource["valueQuantity"])
        else:
            value_filter = None
        semantic_equivalent.append(Criterion([coding_term_code], value_filter))
    observation_sq.inclusionCriteria.append(semantic_equivalent)
    return observation_sq


def generate_concept_filter(codeable_concept):
    return ConceptFilter(get_term_codes(codeable_concept["coding"]))


def generate_comparator_filter(quantity_value):
    return QuantityComparatorFilter("eq", quantity_value["value"], Unit(quantity_value["code"], quantity_value["unit"]))


def generate_term_code_sq(coding):
    sq = StructuredQuery()
    semantic_equivalent = []
    for coding_term_code in get_term_codes(coding):
        semantic_equivalent.append(Criterion([coding_term_code], None))
    sq.inclusionCriteria.append(semantic_equivalent)
    return sq


def generate_sofa_score_sq(sofa_resource):
    sofa_sq = StructuredQuery()
    for coding_term_code in get_term_codes(sofa_resource["code"]["coding"]):
        value_filter = ValueFilter
        if "valueInteger" in sofa_resource:
            value_filter = QuantityComparatorFilter("eq", sofa_resource["valueInteger"], None)
        sofa_sq.inclusionCriteria.append([Criterion([coding_term_code], value_filter)])
        break
    return sofa_sq


def generate_immunization_sq(immunization_resource):
    if immunization_resource["status"] != "completed":
        return None
    return generate_term_code_sq(immunization_resource["vaccineCode"]["coding"])


def generate_medication_statement_sq(medication_statement_resource):
    return generate_term_code_sq(medication_statement_resource["medicationCodeableConcept"]["coding"])


def generate_procedure_sq(procedure_resource):
    return generate_term_code_sq(procedure_resource["category"]["coding"])


def generate_diagnostic_report_sq(diagnostic_report_resource):
    return generate_term_code_sq(diagnostic_report_resource["code"]["coding"])


def generate_history_of_travel_sq(history_of_travel_resource):
    sq = StructuredQuery()
    semantic_equivalent = []
    for term_code in get_term_codes(history_of_travel_resource["code"]["coding"]):
        selected_concepts = []
        for component in history_of_travel_resource["component"]:
            if codings := safe_get(component, "code", "coding"):
                for coding in codings:
                    coding_term_code = TermCode(coding["system"], coding["code"], "Country of travel")
                    if coding_term_code == TermCode("http://loinc.org", "94651-7", ""):
                        selected_concepts.append(get_country_code(component))
        semantic_equivalent.append(Criterion([term_code], ConceptFilter(selected_concepts)))
    sq.inclusionCriteria.append(semantic_equivalent)
    return sq


def get_country_code(component):
    if codings := safe_get(component, "valueCodeableConcept", "coding"):
        for coding in codings:
            return TermCode(coding["system"], coding["code"], coding["display"])


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
