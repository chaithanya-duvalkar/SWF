import re
import sys
import os
import pandas as pd


# ============================================================
# Detect format (CTC supported)
# ============================================================

def detect_format(map_file):

    with open(map_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if re.search(r"\|\s*0x[0-9A-Fa-f]+", line):
                return "ctc"

    return "unknown"


# ============================================================
# Parse CTC map file
# ============================================================

def parse_ctc_map(map_file):

    symbols = {}
    sizes = {}

    with open(map_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    # --------------------------
    # Collect symbols
    # --------------------------

    for line in lines:

        sym = re.search(r"\|\s*([A-Za-z0-9_]+)\s*\|\s*(0x[0-9A-Fa-f]+)", line)
        if sym:
            symbols[sym.group(1).upper()] = int(sym.group(2), 16)

        sz = re.search(r"([A-Za-z0-9_]+_SIZE)\s*\|\s*(0x[0-9A-Fa-f]+)", line)
        if sz:
            sizes[sz.group(1).upper()] = int(sz.group(2), 16)

    all_regions = []
    nested_sections = []

    # --------------------------
    # Build regions
    # --------------------------

    for name, start in symbols.items():

        if not name.endswith("_START"):
            continue

        base = name.replace("_START", "")

        total_size = sizes.get(base + "_SIZE", 0)

        end = start + total_size

        usage = 0

        # --------------------------
        # Subsections
        # --------------------------

        for sub, sub_start in symbols.items():

            if sub.startswith(base) and not sub.endswith("_START"):

                sub_size = sizes.get(sub + "_SIZE", 0)

                sub_end = sub_start + sub_size

                usage += sub_size

                nested_sections.append({

                    "Parent_Section": base,
                    "Sub_Section": sub,
                    "Start_Address": hex(sub_start),
                    "End_Address": hex(sub_end),
                    "Size": hex(sub_size)

                })

        if usage == 0:
            usage = total_size

        free_space = total_size - usage

        all_regions.append({

            "Section": base,
            "Start_Address": hex(start),
            "End_Address": hex(end),
            "Total_Size": hex(total_size),
            "Usage": hex(usage),
            "Free_Space": hex(free_space)

        })

    return all_regions, nested_sections


# ============================================================
# Create hierarchical sheet (TEAM LEAD FORMAT)
# ============================================================

def create_hierarchical_sheet(all_regions, nested_sections):

    hierarchical = []

    region_map = {}

    for region in all_regions:

        region_name = region["Section"]

        region_map[region_name] = {

            "start": region["Start_Address"],
            "end": region["End_Address"],
            "sections": {}

        }

    for sub in nested_sections:

        parent = sub["Parent_Section"]
        sub_name = sub["Sub_Section"]

        parts = sub_name.split("_")

        if len(parts) >= 3:

            section = "_".join(parts[:3])
            group = "_".join(parts[3:])

        else:

            section = sub_name
            group = ""

        if parent not in region_map:
            continue

        if section not in region_map[parent]["sections"]:

            region_map[parent]["sections"][section] = []

        region_map[parent]["sections"][section].append({

            "group": group,
            "addr": sub["Start_Address"],
            "size": sub["Size"]

        })

    # Build hierarchical format

    for region, data in region_map.items():

        hierarchical.append({

            "Label": "_lc_gb_" + region,
            "Section": "",
            "Group": "",
            "Address/Size": data["start"]

        })

        for section, groups in data["sections"].items():

            hierarchical.append({

                "Label": "",
                "Section": section,
                "Group": "",
                "Address/Size": groups[0]["addr"]

            })

            for g in groups:

                hierarchical.append({

                    "Label": "",
                    "Section": section,
                    "Group": g["group"],
                    "Address/Size": g["size"]

                })

        hierarchical.append({

            "Label": "_lc_ge_" + region,
            "Section": "",
            "Group": "",
            "Address/Size": data["end"]

        })

    return pd.DataFrame(hierarchical)


# ============================================================
# Export Excel
# ============================================================

def export_excel(all_regions, nested_sections, output_file):

    reset_safe = [

        r for r in all_regions
        if "RST_SAFE" in r["Section"].upper()

    ]

    hierarchical_df = create_hierarchical_sheet(all_regions, nested_sections)

    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:

        pd.DataFrame(all_regions).to_excel(
            writer,
            sheet_name="All_Memory_Regions",
            index=False
        )

        pd.DataFrame(nested_sections).to_excel(
            writer,
            sheet_name="Sub_Sections",
            index=False
        )

        pd.DataFrame(reset_safe).to_excel(
            writer,
            sheet_name="Reset_Safe_Area",
            index=False
        )

        hierarchical_df.to_excel(
            writer,
            sheet_name="Hierarchical_Sub_Sections",
            index=False
        )

    print("\nExcel generated successfully")
    print(f"All regions  : {len(all_regions)}")
    print(f"Subsections  : {len(nested_sections)}")
    print(f"Reset Safe   : {len(reset_safe)}")
    print(f"Hierarchical : {len(hierarchical_df)}")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) < 2:

        print("Usage:")
        print("python map_parser_ctc.py <map_file> [output.xlsx]")
        sys.exit(1)

    map_file = sys.argv[1]

    output = sys.argv[2] if len(sys.argv) > 2 else "memory_layout.xlsx"

    if detect_format(map_file) != "ctc":

        print("Only CTC format supported")
        sys.exit(1)

    regions, nested = parse_ctc_map(map_file)

    export_excel(regions, nested, output)
