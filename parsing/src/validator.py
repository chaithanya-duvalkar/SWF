# src/validator.py


def validate_range(start, end):
    """
    Basic memory range validation
    """

    if not start or not end:
        return "NOT FOUND"

    start_int = int(start, 16)
    end_int = int(end, 16)

    if end_int <= start_int:
        return "INVALID RANGE"

    # alignment check (example 0x40)
    if start_int % 0x40 != 0:
        return "MISALIGNED"

    return "OK"
