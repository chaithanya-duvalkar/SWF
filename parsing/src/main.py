# src/main.py

import json
from parser import get_section_range
from excel_writer import write_excel
from validator import validate_range


MAP_FILE = "input/app.map"
OUTPUT_FILE = "output/memory_layout.xlsx"
CONFIG_FILE = "config/sections.json"


def main():

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    results = []

    for section in config["sections"]:

        ram_section = section["ram_section"]
        ram_name = section["ram_name"]

        start, end = get_section_range(MAP_FILE, ram_name)

        status = validate_range(start, end)

        print(f"{ram_name} → {start} - {end} ({status})")

        results.append({
            "RAM Section": ram_section,
            "RAM Name": ram_name,
            "Start Address": start,
            "End Address": end,
            "Status": status
        })

    write_excel(results, OUTPUT_FILE)

    print("\nExcel generated successfully!")


if __name__ == "__main__":
    main()
