"""SMS utilities for phone number normalization and formatting."""


def normalize_number(number: str) -> str:
    """
    Normalize phone number to E.164 format.
    
    Handles multiple input formats:
    - 0707274525 (leading zero)
    - 254707274525 (country code prefix)
    - 00254707274525 (00 prefix)
    - +254707274525 (already E.164)
    - 707274525 (without country code)
    
    Args:
        number: Phone number in any common format
        
    Returns:
        str: Phone number in E.164 format (e.g., +254707274525)
    """
    # Strip whitespace and remove hyphens/spaces
    number = number.strip().replace(" ", "").replace("-", "")
    
    # Handle leading zero (0707274525 -> +254707274525)
    if number.startswith("0"):
        number = "+254" + number[1:]
    # Handle country code without + (254707274525 -> +254707274525)
    elif number.startswith("254"):
        number = "+" + number
    # Handle 00 prefix (00254707274525 -> +254707274525)
    elif number.startswith("00254"):
        number = "+254" + number[4:]
    # Handle 9-digit without country code (707274525 -> +254707274525)
    elif len(number) == 9 and not number.startswith("+"):
        number = "+254" + number
    # Add + if missing but looks like international
    elif not number.startswith("+") and len(number) > 10:
        number = "+" + number
    
    return number
