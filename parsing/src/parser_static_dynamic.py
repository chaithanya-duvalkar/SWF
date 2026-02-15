import re
import sys
import os
import pandas as pd


# ============================================================
# Detect format
# ============================================================

def detect_format(map_file):

    with open(map_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if re.search(r"\|\s*0x[0-9A-Fa-f]+", line):
                return "ctc"

    return "unknown"


# ============================================================
# Parse CTC Map File
# (NO CHANGE TO YOUR EXISTING LOGIC)
# ============================================================

def parse_ctc_map(map_file):

    symbols = {}
    sizes = {}

    with open(map_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    # Collect symbols
    for line in lines:

        sym = re.search(r"\|\s*([A-Za-z0-9_\.]+)\s*\|\s*(0x[0-9A-Fa-f]+)", line)
        if sym:
            symbols[sym.group(1).upper()] = int(sym.group(2), 16)

        sz = re.search(r"([A-Za-z0-9_\.]+_SIZE)\s*\|\s*(0x[0-9A-Fa-f]+)", line)
        if sz:
            sizes[sz.group(1).upper()] = int(sz.group(2), 16)

    all_regions = []
    nested_sections = []

    # Build regions
    for name, start in symbols.items():

        if not name.endswith("_START"):
            continue

        base = name.replace("_START", "")

        total_size = sizes.get(base + "_SIZE", 0)

        end = start + total_size

        usage = 0

        # Find subsections
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
# Hierarchical Sheet Generator (FIXED VERSION)
# ============================================================

def create_hierarchical_sheet(all_regions, nested_sections):

    hierarchical = []

    for region in all_regions:

        region_name = region["Section"]
        start_addr = region["Start_Address"]
        end_addr = region["End_Address"]

        # Clean name like DLMU1, DSPR2
        clean_name = region_name.split("_")[-1]

        # Start label
        hierarchical.append({

            "Label": f"_lc_gb_{clean_name}",
            "Section": "",
            "Group": "",
            "Address/Size": start_addr

        })

        # Subsections for this region
        region_subs = [

            sub for sub in nested_sections
            if sub["Parent_Section"] == region_name

        ]

        for sub in region_subs:

            full_name = sub["Sub_Section"]

            # Ignore corema entries
            if "COREMA" in full_name.upper():
                continue

            # Handle .bss.share, .rodata.share, etc.
            if full_name.startswith("."):

                parts = full_name.split(".")

                if len(parts) >= 3:
                    section = "." + parts[1] + "." + parts[2]
                    group = parts[-1]
                else:
                    section = full_name
                    group = ""

            else:

                parts = full_name.split("_")

                if len(parts) >= 3:
                    section = "_".join(parts[:3])
                    group = "_".join(parts[3:])
                else:
                    section = full_name
                    group = ""

            # Section row
            hierarchical.append({

                "Label": "",
                "Section": section,
                "Group": "",
                "Address/Size": sub["Start_Address"]

            })

            # Group row
            if group:

                hierarchical.append({

                    "Label": "",
                    "Section": section,
                    "Group": group,
                    "Address/Size": sub["Size"]

                })

        # End label
        hierarchical.append({

            "Label": f"_lc_ge_{clean_name}",
            "Section": "",
            "Group": "",
            "Address/Size": end_addr

        })

    return pd.DataFrame(hierarchical)


# ============================================================
# Export Excel (4 sheets)
# ============================================================

def export_excel(all_regions, nested_sections, output_file):

    reset_safe = [

        r for r in all_regions
        if "RST_SAFE" in r["Section"].upper()

    ]

    hierarchical_df = create_hierarchical_sheet(all_regions, nested_sections)

    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:

        # Sheet 1
        pd.DataFrame(all_regions).to_excel(
            writer,
            sheet_name="All_Memory_Regions",
            index=False
        )

        # Sheet 2
        pd.DataFrame(nested_sections).to_excel(
            writer,
            sheet_name="Sub_Sections",
            index=False
        )

        # Sheet 3
        pd.DataFrame(reset_safe).to_excel(
            writer,
            sheet_name="Reset_Safe_Area",
            index=False
        )

        # Sheet 4 (TEAM LEAD FORMAT)
        hierarchical_df.to_excel(
            writer,
            sheet_name="Hierarchical_Sub_Sections",
            index=False
        )

    print("\nExcel generated successfully")
    print(f"All regions     : {len(all_regions)}")
    print(f"Sub sections    : {len(nested_sections)}")
    print(f"Reset Safe      : {len(reset_safe)}")
    print(f"Hierarchical    : {len(hierarchical_df)}")


# ============================================================
# MAIN
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

    regions, nested_sections = parse_ctc_map(map_file)

    export_excel(regions, nested_sections, output)
