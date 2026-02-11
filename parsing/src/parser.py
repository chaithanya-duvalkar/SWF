# # # src/parser.py

# # import re


# # def extract_section_addresses(map_file_path, section_name):
# #     """
# #     Extract start and end address for a given section
# #     Example: DATA_DLMU_2
# #     """

# #     start_addr = None
# #     end_addr = None

# #     begin_pattern = re.compile(rf"{section_name}.*begin", re.IGNORECASE)
# #     end_pattern = re.compile(rf"{section_name}.*end", re.IGNORECASE)
# #     address_pattern = re.compile(r"0x[0-9A-Fa-f]+")

# #     with open(map_file_path, "r", errors="ignore") as f:
# #         lines = f.readlines()

# #     for i, line in enumerate(lines):

# #         # find begin
# #         if begin_pattern.search(line):
# #             for j in range(i + 1, len(lines)):
# #                 match = address_pattern.search(lines[j])
# #                 if match:
# #                     start_addr = match.group()
# #                     break

# #         # find end
# #         if end_pattern.search(line):
# #             for j in range(i + 1, len(lines)):
# #                 match = address_pattern.search(lines[j])
# #                 if match:
# #                     end_addr = match.group()
# #                     break

# #     return start_addr, end_addr


# import re


# def get_section_range(map_file_path, section_name):
#     """
#     Returns start and end addresses of section
#     """

#     start_addr = None
#     end_addr = None

#     with open(map_file_path, "r", errors="ignore") as f:
#         lines = f.readlines()

#     address_pattern = re.compile(r"0x[0-9A-Fa-f]+")

#     for i, line in enumerate(lines):

#         # detect BEGIN line
#         if "begin" in line.lower() and section_name in line:
#             for j in range(i + 1, len(lines)):
#                 match = address_pattern.search(lines[j])
#                 if match:
#                     start_addr = match.group()
#                     break

#         # detect END line
#         if "end" in line.lower() and section_name in line:
#             for j in range(i + 1, len(lines)):
#                 match = address_pattern.search(lines[j])
#                 if match:
#                     end_addr = match.group()
#                     break

#     return start_addr, end_addr


import re
import sys
import os
import pandas as pd

# =========================================================
# Detect MAP file format (HiTech / CTC)
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
# Hi-Tech MAP parser (Main + Nested)
# =========================================================
def parse_map_detailed_hitech(map_file_path):
    sections = []
    nested_sections = []

    with open(map_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i]

        section_match = re.search(
            r'([A-Za-z0-9_]+)\s+memory region\s*->\s*(DATA_[A-Z_0-9]+)',
            line,
            re.IGNORECASE
        )

        if section_match:
            section_name = section_match.group(1)
            ram_section = section_match.group(2).replace("DATA_", "")

            address = None
            size_on_same_line = None

            for j in range(i + 1, min(i + 15, len(lines))):
                two_hex = re.search(r'(0x[0-9A-Fa-f]+)\s+(0x[0-9A-Fa-f]+)', lines[j])
                one_hex = re.search(r'(0x[0-9A-Fa-f]+)', lines[j])

                if two_hex:
                    address = two_hex.group(1)
                    size_on_same_line = two_hex.group(2)
                    break
                elif one_hex:
                    address = one_hex.group(1)
                    break

            if address:
                end_addr = None
                if size_on_same_line:
                    end_addr = hex(int(address, 16) + int(size_on_same_line, 16))

                sections.append({
                    "Section": section_name,
                    "Start Address": address,
                    "End Address": end_addr,
                    "Size (Hex)": size_on_same_line,
                    "RAM Section": ram_section
                })

                # -------- Nested parsing --------
                usage = 0
                for k in range(i + 1, min(i + 20, len(lines))):
                    sub_match = re.match(
                        r'\s*([A-Za-z0-9_]+)\s+(0x[0-9A-Fa-f]+)\s+(0x[0-9A-Fa-f]+)',
                        lines[k]
                    )
                    if sub_match:
                        sub_name = sub_match.group(1)
                        sub_size = int(sub_match.group(2), 16)
                        align = int(sub_match.group(3), 16)

                        sub_start = int(address, 16) + usage
                        sub_end = sub_start + sub_size
                        usage += sub_size

                        nested_sections.append({
                            "Parent Section": section_name,
                            "Sub-Region": sub_name,
                            "Start Address": hex(sub_start),
                            "End Address": hex(sub_end),
                            "Size (Hex)": hex(sub_size),
                            "Usage": f"{sub_size} B",
                            "Alignment": hex(align)
                        })

        i += 1

    return sections, nested_sections

# =========================================================
# CTC MAP parser (Main + Nested)
# =========================================================
def parse_map_detailed_ctc(map_file_path):
    symbols = {}
    sizes = {}
    sections = []
    nested_sections = []

    with open(map_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # -------- Pass 1: Collect symbols --------
    for line in lines:
        match = re.search(r'\|\s*([A-Za-z0-9_]+)\s*\|\s*(0x[0-9A-Fa-f]+)', line)
        if match:
            symbols[match.group(1).upper()] = int(match.group(2), 16)

        size_match = re.search(r'([A-Za-z0-9_]+_SIZE)\s*\|\s*(0x[0-9A-Fa-f]+)', line)
        if size_match:
            sizes[size_match.group(1).upper()] = int(size_match.group(2), 16)

    # -------- Pass 2: Build sections --------
    for name, start_addr in symbols.items():
        if name.endswith("_START"):
            base = name.replace("_START", "")
            size = sizes.get(base + "_SIZE")
            end_addr = start_addr + size if size else None
            usage = size
            free = None

            sections.append({
                "Section": base,
                "Start Address": hex(start_addr),
                "End Address": hex(end_addr) if end_addr else None,
                "Total Size (Hex)": hex(size) if size else None,
                "Total Size (Dec)": f"{size} B" if size else None,
                "Usage": f"{usage} B" if usage else None,
                "Free Space": f"{free} B" if free else None
            })

            # -------- Nested Sections --------
            for sub_name, sub_start in symbols.items():
                if sub_name.startswith(base) and not sub_name.endswith("_START"):
                    sub_size = sizes.get(sub_name + "_SIZE")
                    sub_end = sub_start + sub_size if sub_size else None

                    nested_sections.append({
                        "Parent Section": base,
                        "Sub-Region": sub_name,
                        "Start Address": hex(sub_start),
                        "End Address": hex(sub_end) if sub_end else None,
                        "Size (Hex)": hex(sub_size) if sub_size else None,
                        "Usage": f"{sub_size} B" if sub_size else None,
                        "Free Space": None
                    })

    return sections, nested_sections

# =========================================================
# Export to Excel (2 Sheets)
# =========================================================
def export_to_excel(sections, nested_sections, output_file):
    if not sections:
        print("No memory sections found")
        return

    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        pd.DataFrame(sections).to_excel(
            writer,
            sheet_name="Memory Sections",
            index=False
        )
        pd.DataFrame(nested_sections).to_excel(
            writer,
            sheet_name="Nested Sections",
            index=False
        )

    print(f"Excel file created: {output_file}")
    print(f"Main sections: {len(sections)}")
    print(f"Nested sections: {len(nested_sections)}")

# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python map_parser_ctc.py <map_file> [output.xlsx]")
        sys.exit(1)

    map_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "memory_sections.xlsx"

    fmt = detect_format(map_file)

    print("=" * 80)
    print("Enhanced Map File Parser (Main + Nested Sections)")
    print("=" * 80)
    print(f"Input  : {map_file}")
    print(f"Output : {output_file}")
    print(f"Format : {fmt}")
    print("=" * 80)

    if fmt == "hitech":
        sections, nested_sections = parse_map_detailed_hitech(map_file)
    elif fmt == "ctc":
        sections, nested_sections = parse_map_detailed_ctc(map_file)
    else:
        print("Unknown MAP file format")
        sys.exit(1)

    export_to_excel(sections, nested_sections, output_file)
