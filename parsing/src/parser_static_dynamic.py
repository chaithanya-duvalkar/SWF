import re
import sys
import pandas as pd


# ============================================================
# Parse map file
# ============================================================

def parse_ctc_map(map_file):

    symbols = {}
    sizes = {}

    with open(map_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    # Extract symbols and sizes
    for line in lines:

        sym = re.search(r"\|\s*([A-Za-z0-9_\.]+)\s*\|\s*(0x[0-9A-Fa-f]+)", line)
        if sym:
            symbols[sym.group(1)] = int(sym.group(2), 16)

        sz = re.search(r"([A-Za-z0-9_\.]+_SIZE)\s*\|\s*(0x[0-9A-Fa-f]+)", line)
        if sz:
            sizes[sz.group(1)] = int(sz.group(2), 16)

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
# Create Hierarchical Sheet
# ============================================================

def create_hierarchical_sheet(all_regions, nested_sections):

    rows = []

    for region in all_regions:

        region_name = region["Section"]

        # Region start label
        rows.append({

            "Label": f"_lc_gb_{region_name}",
            "Section": "",
            "Group": "",
            "Address/Size": region["Start_Address"]

        })

        for sub in nested_sections:

            if sub["Parent_Section"] != region_name:
                continue

            full = sub["Sub_Section"]

            upper = full.upper()

            # Ignore unwanted symbols
            if ("IOPT_MEMLOC" in upper or
                upper.endswith("_START") or
                upper.endswith("_END") or
                upper.endswith("_SIZE") or
                "COREMA" in upper):
                continue

            # Remove region prefix
            remaining = full[len(region_name) + 1:]

            # Handle share sections
            if remaining.startswith("."):

                parts = remaining.split(".")

                if len(parts) >= 3:

                    section = "." + ".".join(parts[1:-1])
                    group = parts[-1]

                else:

                    section = remaining
                    group = ""

            else:

                parts = remaining.split("_")

                if parts[-1] in ("EXPLC", "RELOC"):

                    section = "_".join(parts[:-1])
                    group = parts[-1]

                else:

                    section = remaining
                    group = ""

            # Add Section row
            rows.append({

                "Label": "",
                "Section": section,
                "Group": "",
                "Address/Size": sub["Start_Address"]

            })

            # Add Group row
            if group:

                rows.append({

                    "Label": "",
                    "Section": section,
                    "Group": group,
                    "Address/Size": sub["Size"]

                })

        # Region end label
        rows.append({

            "Label": f"_lc_ge_{region_name}",
            "Section": "",
            "Group": "",
            "Address/Size": region["End_Address"]

        })

    return pd.DataFrame(rows)


# ============================================================
# Export Excel safely
# ============================================================

def export_excel(all_regions, nested_sections, output):

    print("Regions found:", len(all_regions))
    print("Subsections found:", len(nested_sections))

    reset_safe = [

        r for r in all_regions
        if "RST_SAFE" in r["Section"].upper()

    ]

    hierarchical = create_hierarchical_sheet(all_regions, nested_sections)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        # Always write at least one sheet
        if all_regions:
            pd.DataFrame(all_regions).to_excel(
                writer,
                sheet_name="All_Memory_Regions",
                index=False
            )
        else:
            pd.DataFrame({"Info": ["No regions found"]}).to_excel(
                writer,
                sheet_name="All_Memory_Regions",
                index=False
            )

        if nested_sections:
            pd.DataFrame(nested_sections).to_excel(
                writer,
                sheet_name="Sub_Sections",
                index=False
            )

        if reset_safe:
            pd.DataFrame(reset_safe).to_excel(
                writer,
                sheet_name="Reset_Safe_Area",
                index=False
            )

        if not hierarchical.empty:
            hierarchical.to_excel(
                writer,
                sheet_name="Hierarchical_Sub_Sections",
                index=False
            )
        else:
            pd.DataFrame({"Info": ["No hierarchical sections found"]}).to_excel(
                writer,
                sheet_name="Hierarchical_Sub_Sections",
                index=False
            )

    print("\nSUCCESS: Excel generated:", output)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) < 2:

        print("Usage:")
        print("python map_parser_ctc.py your.map memory_layout.xlsx")
        sys.exit(1)

    map_file = sys.argv[1]

    output = sys.argv[2] if len(sys.argv) > 2 else "memory_layout.xlsx"

    regions, subsections = parse_ctc_map(map_file)

    export_excel(regions, subsections, output)
