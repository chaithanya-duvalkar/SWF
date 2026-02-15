import re
import sys
import os
import pandas as pd


# ============================================================
# Detect format (UNCHANGED)
# ============================================================

def detect_format(map_file):

    with open(map_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if re.search(r"\|\s*0x[0-9A-Fa-f]+", line):
                return "ctc"

    return "unknown"


# ============================================================
# Parse map file (UNCHANGED LOGIC)
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

        for sub, sub_start in symbols.items():

            if sub.startswith(base) and sub != name:

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
# NEW FUNCTION: Hierarchical Sheet Builder (ONLY ADDITION)
# ============================================================

def build_hierarchical_sheet(all_regions, nested_sections):

    rows = []

    region_sections = {}

    for sub in nested_sections:

        parent = sub["Parent_Section"]
        full = sub["Sub_Section"]

        # Ignore unwanted linker control symbols
        if (
            "_IOPT_MEMLOC" in full or
            full.endswith("_START") or
            full.endswith("_END") or
            full.endswith("_SIZE") or
            "_COREMA" in full
        ):
            continue

        # Remove prefix like DLMU1_
        if full.startswith(parent + "_"):
            remaining = full[len(parent) + 1:]
        else:
            remaining = full

        parts = remaining.split("_")

        if parts[-1] in ["EXPLC", "RELOC"]:

            section = "_".join(parts[:-1])
            group = parts[-1]

        else:

            section = remaining
            group = None

        region_sections.setdefault(parent, {})
        region_sections[parent].setdefault(section, [])
        region_sections[parent][section].append({

            "group": group,
            "addr": sub["Start_Address"],
            "size": sub["Size"]

        })

    # Build hierarchical rows
    for region in all_regions:

        region_name = region["Section"]

        # Start label
        rows.append({

            "Label": "_lc_gb_" + region_name,
            "Section": "",
            "Group": "",
            "Address/Size": region["Start_Address"]

        })

        if region_name in region_sections:

            for section_name, entries in region_sections[region_name].items():

                # main section row
                main_entry = None

                for e in entries:
                    if e["group"] is None:
                        main_entry = e
                        break

                if main_entry:

                    rows.append({

                        "Label": "",
                        "Section": section_name,
                        "Group": "",
                        "Address/Size": main_entry["addr"]

                    })

                # group rows
                for e in entries:

                    if e["group"] is not None:

                        rows.append({

                            "Label": "",
                            "Section": section_name,
                            "Group": e["group"],
                            "Address/Size": e["size"]

                        })

        # End label
        rows.append({

            "Label": "_lc_ge_" + region_name,
            "Section": "",
            "Group": "",
            "Address/Size": region["End_Address"]

        })

    return pd.DataFrame(rows)


# ============================================================
# Export Excel (ONLY ADD HIERARCHICAL SHEET)
# ============================================================

def export_excel(all_regions, nested_sections, output_file):

    reset_safe = [

        r for r in all_regions
        if "RST_SAFE" in r["Section"].upper()

    ]

    hierarchical_df = build_hierarchical_sheet(all_regions, nested_sections)

    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:

        # EXISTING SHEETS (UNCHANGED)
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

        # NEW SHEET
        hierarchical_df.to_excel(
            writer,
            sheet_name="Hierarchical_Sub_Sections",
            index=False
        )

    print("Excel generated successfully:", output_file)


# ============================================================
# MAIN (UNCHANGED)
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) < 2:

        print("Usage:")
        print("python map_parser_ctc.py <map_file> [output.xlsx]")
        sys.exit(1)

    map_file = sys.argv[1]

    output = sys.argv[2] if len(sys.argv) > 2 else "memory_layout.xlsx"

    if detect_format(map_file) != "ctc":

        print("Only CTC format supported.")
        sys.exit(1)

    regions, nested = parse_ctc_map(map_file)

    export_excel(regions, nested, output)
