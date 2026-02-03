# # src/parser.py

# import re


# def extract_section_addresses(map_file_path, section_name):
#     """
#     Extract start and end address for a given section
#     Example: DATA_DLMU_2
#     """

#     start_addr = None
#     end_addr = None

#     begin_pattern = re.compile(rf"{section_name}.*begin", re.IGNORECASE)
#     end_pattern = re.compile(rf"{section_name}.*end", re.IGNORECASE)
#     address_pattern = re.compile(r"0x[0-9A-Fa-f]+")

#     with open(map_file_path, "r", errors="ignore") as f:
#         lines = f.readlines()

#     for i, line in enumerate(lines):

#         # find begin
#         if begin_pattern.search(line):
#             for j in range(i + 1, len(lines)):
#                 match = address_pattern.search(lines[j])
#                 if match:
#                     start_addr = match.group()
#                     break

#         # find end
#         if end_pattern.search(line):
#             for j in range(i + 1, len(lines)):
#                 match = address_pattern.search(lines[j])
#                 if match:
#                     end_addr = match.group()
#                     break

#     return start_addr, end_addr


import re


def get_section_range(map_file_path, section_name):
    """
    Returns start and end addresses of section
    """

    start_addr = None
    end_addr = None

    with open(map_file_path, "r", errors="ignore") as f:
        lines = f.readlines()

    address_pattern = re.compile(r"0x[0-9A-Fa-f]+")

    for i, line in enumerate(lines):

        # detect BEGIN line
        if "begin" in line.lower() and section_name in line:
            for j in range(i + 1, len(lines)):
                match = address_pattern.search(lines[j])
                if match:
                    start_addr = match.group()
                    break

        # detect END line
        if "end" in line.lower() and section_name in line:
            for j in range(i + 1, len(lines)):
                match = address_pattern.search(lines[j])
                if match:
                    end_addr = match.group()
                    break

    return start_addr, end_addr
