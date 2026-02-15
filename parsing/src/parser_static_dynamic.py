import re
import sys
import pandas as pd


# ============================================================
# Parse map file (same as your working extraction)
# ============================================================

def parse_ctc_map(map_file):

    symbols = {}
    sizes = {}

    with open(map_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    for line in lines:

        sym = re.search(r"\|\s*([A-Za-z0-9_\.]+)\s*\|\s*(0x[0-9A-Fa-f]+)", line)
        if sym:
            symbols[sym.group(1)] = int(sym.group(2), 16)

        sz = re.search(r"([A-Za-z0-9_\.]+_SIZE)\s*\|\s*(0x[0-9A-Fa-f]+)", line)
        if sz:
            sizes[sz.group(1)] = int(sz.group(2), 16)

    all_regions = []
    nested_sections = []

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

        free = total_size - usage

        all_regions.append({

            "Section": base,
            "Start_Address": hex(start),
            "End_Address": hex(end),
            "Total_Size": hex(total_size),
            "Usage": hex(usage),
            "Free_Space": hex(free)

        })

    return all_regions, nested_sections


# ============================================================
# Hierarchical sheet generator (EXACT TEAM LEAD FORMAT)
# ============================================================

def create_hierarchical_sheet(all_regions, nested_sections):

    rows = []

    for region in all_regions:

        region_name = region["Section"]

        # Start label
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

            # Ignore unwanted linker symbols
            if ("IOPT_MEMLOC" in upper or
                upper.endswith("_START") or
                upper.endswith("_END") or
                upper.endswith("_SIZE") or
                "COREMA" in upper):
                continue

            # Remove prefix DLMU0_
            remaining = full[len(region_name) + 1:]

            # SHARE sections
            if remaining.startswith("."):

                parts = remaining.split(".")

                section = "." + ".".join(parts[1:-1])
                group = parts[-1]

            else:

                parts = remaining.split("_")

                if parts[-1] in ("EXPLC", "RELOC"):

                    section = "_".join(parts[:-1])
                    group = parts[-1]

                else:

                    section = remaining
                    group = ""

            # Section row
            rows.append({

                "Label": "",
                "Section": section,
                "Group": "",
                "Address/Size": sub["Start_Address"]

            })

            # Group row
            if group:

                rows.append({

                    "Label": "",
                    "Section": section,
                    "Group": group,
                    "Address/Size": sub["Size"]

                })

        # End label
        rows.append({
            "Label": f"_lc_ge_{region_name}",
            "Section": "",
            "Group": "",
            "Address/Size": region["End_Address"]
        })

    return pd.DataFrame(rows)


# ============================================================
# Export Excel (4 sheets)
# ============================================================

def export_excel(all_regions, nested_sections, output):

    reset_safe = [
        r for r in all_regions
        if "RST_SAFE" in r["Section"].upper()
    ]

    hierarchical = create_hierarchical_sheet(all_regions, nested_sections)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        pd.DataFrame(all_regions).to_excel(writer,
                                           "All_Memory_Regions",
                                           index=False)

        pd.DataFrame(nested_sections).to_excel(writer,
                                               "Sub_Sections",
                                               index=False)

        pd.DataFrame(reset_safe).to_excel(writer,
                                          "Reset_Safe_Area",
                                          index=False)

        hierarchical.to_excel(writer,
                              "Hierarchical_Sub_Sections",
                              index=False)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    map_file = sys.argv[1]

    output = sys.argv[2] if len(sys.argv) > 2 else "memory_layout.xlsx"

    regions, subsections = parse_ctc_map(map_file)

    export_excel(regions, subsections, output)

    print("SUCCESS: Excel generated correctly.")
