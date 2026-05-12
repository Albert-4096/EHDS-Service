import re

# Matches digit(s) + comma + digit(s) but ensures it's not followed by space+3 digits (which might be a thousand separator in some formats, though rare in Romanian context, we follow the prompt strictly)
# The prompt explicitly specifies the pattern: r"(\d+),(\d+)(?!\s*\d{3})"
DECIMAL_COMMA_REGEX = re.compile(r"(\d+),(\d+)(?!\s*\d{3})")

def normalise_romanian_decimal(value_str: str) -> str:
    """
    Replace comma decimal separator ONLY in numeric contexts.
    Pattern matches: digit(s) + comma + digit(s) (not followed by space+digit)
    """
    if not isinstance(value_str, str):
        return value_str
    
    return DECIMAL_COMMA_REGEX.sub(r"\1.\2", value_str)
