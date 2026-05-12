from datetime import date
from pydantic import BaseModel

class CNPParseError(Exception):
    """Exception raised when a CNP string is invalid."""
    pass

class CNPData(BaseModel):
    date_of_birth: date
    sex: str
    county_code: str

# Standard Romanian CNP weights for checksum calculation
CNP_WEIGHTS = (2, 7, 9, 1, 4, 6, 3, 5, 8, 2, 7, 9)

def parse_cnp(cnp: str) -> CNPData:
    if not cnp or not isinstance(cnp, str):
        raise CNPParseError(f"Invalid CNP format: '{cnp}'")
    
    cnp_clean = cnp.strip()
    if len(cnp_clean) != 13 or not cnp_clean.isdigit():
        raise CNPParseError(f"Invalid CNP format or length: '{cnp}'")

    # Checksum validation
    checksum = sum(int(cnp_clean[i]) * CNP_WEIGHTS[i] for i in range(12)) % 11
    if checksum == 10:
        checksum = 1
    
    if checksum != int(cnp_clean[12]):
        raise CNPParseError(f"CNP checksum validation failed: '{cnp}'")

    s = int(cnp_clean[0])
    yy = int(cnp_clean[1:3])
    mm = int(cnp_clean[3:5])
    dd = int(cnp_clean[5:7])
    jj = cnp_clean[7:9]

    # Sex and Century rules
    if s in (1, 2):
        century = 1900
        sex = "M" if s == 1 else "F"
    elif s in (3, 4):
        century = 1800
        sex = "M" if s == 3 else "F"
    elif s in (5, 6):
        century = 2000
        sex = "M" if s == 5 else "F"
    elif s in (7, 8, 9):
        # 7/8 foreign residents born in Romania, 9 foreign residents born abroad
        # The prompt says: "7/9 -> foreign resident", we will use 1900 as fallback or standard logic.
        # Actually standard logic: 7/8/9 implies 1900 century (1900-1999) generally for 7/8, and 9 could be 1900 or 2000 depending on exact implementation, but usually 1900.
        # Let's default century to 1900 for foreign residents per simplified rules, or infer from current date if > current year then 1900.
        # But wait, 7/8 usually means born between 1900 and 1999.
        century = 1900
        if s == 9: # Typically 9 does not encode gender strictly or century strictly, but we can infer M/F from the exact CNP structure if needed. Or just generic.
            sex = "M" # Defaulting or could be Unknown.
            century = 1900
        else:
            sex = "M" if s == 7 else "F"
    else:
        raise CNPParseError(f"Invalid CNP sex/century indicator: '{cnp}'")

    year = century + yy

    try:
        dob = date(year, mm, dd)
    except ValueError:
        raise CNPParseError(f"Invalid date of birth in CNP: '{cnp}'")

    return CNPData(
        date_of_birth=dob,
        sex=sex,
        county_code=jj
    )
