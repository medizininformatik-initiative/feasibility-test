import json
from testDataToUnitTest import generate_unit_test

if __name__ == '__main__':
    with open(f"testData.json", encoding="utf-8") as json_file:
        test_data = json.load(json_file)
        generate_unit_test(test_data)
