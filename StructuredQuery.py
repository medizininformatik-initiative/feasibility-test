import json


class TermCode:
    def __init__(self, system, code, display, version=None):
        self.system = system
        self.code = code
        self.version = version
        self.display = display

    def __eq__(self, other):
        return self.system == other.system and self.code == other.code

    def __hash__(self):
        return hash(self.system + self.code)

    def __lt__(self, other):
        return self.code < other.code

    def __repr__(self):
        return self.display + " " + self.code + " " + self.system


def del_none(dictionary):
    """
    Delete keys with the value ``None`` in a dictionary, recursively.

    This alters the input so you may wish to ``copy`` the dict first.
    """
    for key, value in list(dictionary.items()):
        if value is None:
            del dictionary[key]
        elif value is []:
            del dictionary[key]
        elif isinstance(value, dict):
            del_none(value)
    return dictionary


def del_keys(dictionary, keys):
    for k in keys:
        dictionary.pop(k, None)
    return dictionary


class StructuredQuery:
    DO_NOT_SERIALIZE = ["DO_NOT_SERIALIZE"]

    def __init__(self):
        self.version = ""
        self.inclusionCriteria = []
        self.exclusionCriteria = []

    def to_json(self):
        return json.dumps(self, default=lambda o: del_none(
            del_keys(o.__dict__, self.DO_NOT_SERIALIZE)),
                          sort_keys=True, indent=4)


class Unit:
    def __init__(self, code, display):
        self.code = code
        self.display = display


class ValueFilter:
    def __init__(self, value_type):
        self.type = value_type


class ConceptFilter(ValueFilter):
    def __init__(self, selected_concepts=None):
        super().__init__("concept")
        if selected_concepts is None:
            selected_concepts = []
        self.selectedConcepts = selected_concepts


class QuantityComparatorFilter(ValueFilter):
    def __init__(self, comparator, value, unit: Unit):
        super().__init__("quantity-comparator")
        self.comparator = comparator
        self.value = value
        self.unit = unit


class QuantityRangeFilter(ValueFilter):
    def __init__(self, min_value, max_value, unit: Unit):
        super().__init__("quantity-range")
        self.minValue = min_value
        self.maxValue = max_value
        self.unit = unit


class Criterion:
    def __init__(self, term_code: TermCode, value_filter: ValueFilter):
        self.termCode = term_code
        self.valueFilter = value_filter
