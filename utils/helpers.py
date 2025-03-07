import csv
import json


def get_inputs():
    """Reads input CSV file and returns a list of dictionaries.
    
    Example:
        Given inputs.csv with content:
        keyword,avoid_categories
        clinics,pharmacy;
        
        Returns:
        [
            {
                'keyword': 'clinics',
                'avoid_categories': 'pharmacy;'
            }
        ]
    """
    with open(
        "./inputs/inputs.csv", mode="r", newline="", encoding="utf-8"
    ) as inputs_file:
        csv_reader = csv.reader(inputs_file)
        header = next(csv_reader)
        tmp = []
        for row in csv_reader:
            tmp_2 = {header[i]: col for i, col in enumerate(row) if col}
            tmp.append(tmp_2)
        return tmp


def get_non_allowed_categories(keyword):
    tmp = []
    with open("./inputs/google_maps_businesses.json", "r") as json_file:
        all_businesses = json_file["businesses"]
        for b in all_businesses:
            b = b.lower()
            b_list = b.split()
            if keyword.lower() in b_list:
                tmp.append(b)

    return tmp
