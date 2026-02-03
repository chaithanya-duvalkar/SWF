import pandas as pd


def safe_hex_to_int(value):
    """
    Converts hex string to int safely
    Returns None if invalid
    """
    if isinstance(value, str) and value.startswith("0x"):
        return int(value, 16)
    return None


def write_excel(data, output_file):

    df = pd.DataFrame(data)

    sizes = []

    for _, row in df.iterrows():

        start_int = safe_hex_to_int(row["Start Address"])
        end_int = safe_hex_to_int(row["End Address"])

        if start_int is not None and end_int is not None:
            sizes.append(end_int - start_int + 1)
        else:
            sizes.append("N/A")

    df["Size (Bytes)"] = sizes

    df.to_excel(output_file, index=False)

    print("Excel written successfully:", output_file)
