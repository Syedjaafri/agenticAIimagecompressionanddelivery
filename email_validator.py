import re

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")


def is_valid_email(address: str) -> bool:
    """Return True only for a reasonably formatted email address."""
    if not address or len(address) > 254:
        return False
    return bool(EMAIL_PATTERN.fullmatch(address.strip()))
