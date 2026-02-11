import re
import sys
import os
import pandas as pd

# =========================================================
# Detect MAP format
# =========================================================
def detect_format(map_file_path):
    with open(map_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if "memory region" in line.lower():
                return "hitech"
            if re.search(r'\|\s*0x[0-9A-Fa-f]+', line):
                return "ctc"
    return "unknown"

# =========================================================
# CTC MAP PARSER
# =========================================================
def parse_map_detailed_ctc(map_file_path):
    symbols = {}
    sizes = {}

    all_regions = []     # Sheet 1
    sub_sections = []    # Sheet 2
    reset_safe = []      # Sheet 3

    with open(map_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # -------- Collect symbols --------
    for line in lines:
        sym_match = re.search(r'\|\s*([A-Za-z0-9_]+)\s*\|\s*(0x[0-9A-Fa-f]+)', line)
        if sym_match:
            symbols[sym_match.group(1).upper()] = int(sym_match.group(2), 16)

        size_match = re.search(r'([A-Za-z0-9_]+_SIZE)\s*\|\s*(0x[0-9A-Fa-f]+)', line)
        if size_match:
            sizes[size_match.group(1).upper()] = int(size_match.group(2), 16)

    # -------- Build regions --------
    for name, start in symbols.items():
        if name.endswith("_START"):
            base = name.replace("_START", "")
            size = sizes.get(base + "_SIZE")
            end = start + size if size else None

            region_row = {
                "Chip": base,
                "Start Address": hex(start),
                "End Address": hex(end) if end else None,
                "Chip Size": hex(size) if size else None,
            }
            all_regions.append(region_row)

            # -------- Sub-sections --------
            for sub_name, sub_start in symbols.items():
                if sub_name.startswith(base) and not sub_name.endswith("_START"):
                    sub_size = sizes.get(sub_name + "_SIZE")

                    sub_row = {
                        "Chip": base,
                        "Group": base.lower(),
                        "Sub-group": sub_name,
                        "Size (MAU)": hex(sub_size) if sub_size else None,
                        "Alignment": None
                    }
                    sub_sections.append(sub_row)

                    # -------- Reset Safe filtering --------
                    if "RST_SAFE" in base or "RST_SAFE" in sub_name:
                        reset_safe.append(sub_row)

            # Parent reset-safe region
            if "RST_SAFE" in base:
                reset_safe.append(region_row)

    return all_regions, sub_sections, reset_safe

# =========================================================
# EXPORT TO EXCEL (3 SHEETS)
# =========================================================
def export_to_excel(all_regions, sub_sections, reset_safe, output_file):
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        pd.DataFrame(all_regions).to_excel(
            writer, sheet_name="All_Memory_Regions", index=False
        )
        pd.DataFrame(sub_sections).to_excel(
            writer, sheet_name="Sub_Sections", index=False
        )
        pd.DataFrame(reset_safe).to_excel(
            writer, sheet_name="Reset_Safe_Area", index=False
        )

    print("Excel generated successfully")
    print(f"Sheet-1 All regions : {len(all_regions)}")
    print(f"Sheet-2 Sub sections: {len(sub_sections)}")
    print(f"Sheet-3 Reset safe  : {len(reset_safe)}")

# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python map_parser_ctc.py <map_file> [output.xlsx]")
        sys.exit(1)

    map_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "memory_layout.xlsx"

    fmt = detect_format(map_file)

    print("=" * 80)
    print("MAP FILE → 3-SHEET EXCEL GENERATOR")
    print("=" * 80)
    print(f"Input  : {map_file}")
    print(f"Output : {output_file}")
    print(f"Format : {fmt}")
    print("=" * 80)

    if fmt != "ctc":
        print("Currently enabled for CTC format (as per your screenshots)")
        sys.exit(1)

    all_regions, sub_sections, reset_safe = parse_map_detailed_ctc(map_file)
    export_to_excel(all_regions, sub_sections, reset_safe, output_file)
