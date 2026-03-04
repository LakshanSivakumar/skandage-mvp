import re
import pandas as pd
from datetime import datetime
from dateutil import parser as dateutil_parser


# ---------------------------------------------------------------------------
# PRIORITY COLUMN LISTS — checked in order, first match wins.
# These are checked as EXACT matches against normalised column names.
# ---------------------------------------------------------------------------
EMAIL_PRIORITY = [
    'email', 'email_address', 'e-mail', 'e_mail', 'emailaddress',
    'primary_email', 'work_email', 'personal_email', 'contact_email',
    'client_email', 'subscriber_email',
]

# Columns that contain "email" but are NOT actual email addresses
EMAIL_EXCLUSIONS = [
    'status', 'confidence', 'source', 'verification', 'sent', 'open',
    'bounced', 'catch', 'secondary', 'tertiary', 'for_email', 'company',
    'owner', 'last_verified', 'qualify',
]

FULL_NAME_PRIORITY = [
    'name', 'full_name', 'fullname', 'client_name', 'contact_name',
    'subscriber_name', 'display_name',
]

FIRST_NAME_PRIORITY = [
    'first_name', 'firstname', 'given_name', 'givenname', 'first',
]

LAST_NAME_PRIORITY = [
    'last_name', 'lastname', 'surname', 'family_name', 'familyname', 'last',
]

DOB_PRIORITY = [
    'dob', 'date_of_birth', 'birthday', 'birth_date', 'birthdate',
    'date_birth', 'd.o.b', 'd.o.b.', 'born', 'birth',
]

RACE_PRIORITY = [
    'race', 'ethnicity', 'race_ethnicity', 'race/ethnicity', 'ethnic_group',
    'nationality',
]

GENDER_PRIORITY = ['gender', 'sex']

# ---------------------------------------------------------------------------
# ADDITIONAL COLUMN PRIORITY LISTS
# ---------------------------------------------------------------------------
PHONE_PRIORITY = [
    'phone', 'mobile', 'phone_number', 'mobile_number', 'cell',
    'contact_number', 'tel', 'telephone', 'handphone', 'hp',
]

ADDRESS_PRIORITY = [
    'address', 'address_1', 'full_address', 'street_address',
    'residential_address', 'home_address', 'mailing_address',
]

STATUS_PRIORITY = [
    'status', 'pipeline_status', 'client_status', 'lead_status',
    'relationship_status',
]

# "Last review / last updated" — the starting anchor for date calculation
LAST_REVIEW_PRIORITY = [
    'last_updated',           # Skandage CRM Excel
    'last_review_date',
    'last_review',
    'last_updated_date',
    'date_of_last_review',
    'last_contact_date',
    'last_meeting_date',
    'previous_review_date',
    'review_date',
]

# "Next review date" — use directly if present, no calculation needed
NEXT_REVIEW_PRIORITY = [
    'next_review_date',
    'next_review',
    'follow_up_date',
    'due_date',
    'review_due_date',
    'review_due',
    'next_followup',
    'next_follow_up',
    'scheduled_review',
]

# "Duration / frequency" — in months, used to calculate next review date
REVIEW_FREQ_PRIORITY = [
    'review_freq_(months)',   # Skandage CRM Excel: "Review Freq (months)"
    'review_freq_months',
    'review_freq',
    'review_frequency',
    'follow_up_freq',
    'follow_up_frequency',
    'followup_freq',
    'followup_frequency',
    'freq_months',
    'interval_months',
    'follow_up_interval',
    'review_interval',
    'frequency',
    'duration',
]

# CMIO keyword matching
RACE_KEYWORDS = {
    'C': ['chinese', 'chi', 'cn', 'han'],
    'M': ['malay', 'mal', 'melayu'],
    'I': ['indian', 'ind', 'tamil', 'hindi', 'sikh', 'punjabi', 'gujarati'],
}

GENDER_MALE = {'m', 'male', 'boy', 'man', 'mr', 'gentleman'}
GENDER_FEMALE = {'f', 'female', 'girl', 'woman', 'ms', 'mrs', 'miss', 'madam', 'mdm', 'lady'}

# Values that mean "no data"
NULL_VALUES = {'', 'nan', 'none', 'null', 'n/a', 'na', 'nil', '-', '--', '—'}


def _normalise_col(col):
    """Lowercase, strip, replace spaces/hyphens/dots with underscores."""
    col = str(col).lower().strip()
    col = re.sub(r'[\s\-\.]+', '_', col)
    return col.strip('_')


def _find_column(df_columns, priority_list):
    """Find the first column from priority_list that exists in the dataframe."""
    col_set = set(df_columns)
    for candidate in priority_list:
        if candidate in col_set:
            return candidate
    return None


def _find_email_column(df_columns):
    """
    Find the actual email column, avoiding false positives like
    'company_name_for_emails', 'email_status', 'email_confidence', etc.
    """
    col_list = list(df_columns)

    # Pass 1: exact match from priority list
    for candidate in EMAIL_PRIORITY:
        if candidate in col_list:
            return candidate

    # Pass 2: substring match, but exclude metadata columns
    for col in col_list:
        if 'email' not in col:
            continue
        # Skip if any exclusion keyword is present
        if any(ex in col for ex in EMAIL_EXCLUSIONS):
            continue
        return col

    return None


def _find_name_column(df_columns):
    """Find a name column, avoiding 'company_name', 'plan_name', etc."""
    col_list = list(df_columns)

    # Pass 1: exact match
    for candidate in FULL_NAME_PRIORITY:
        if candidate in col_list:
            return candidate

    # Pass 2: substring match with exclusions
    exclusions = ['company', 'plan', 'policy', 'account', 'file', 'host']
    for col in col_list:
        if 'name' not in col:
            continue
        if any(ex in col for ex in exclusions):
            continue
        return col

    return None


def _safe_val(row, col):
    """Get a string value from a row, returning '' for nulls."""
    if col is None:
        return ''
    val = str(row.get(col, '')).strip()
    if val.lower() in NULL_VALUES:
        return ''
    return val


def _parse_date(raw):
    """
    Parse a date string into (display DD/MM/YYYY, db YYYY-MM-DD).
    Handles ISO, DD/MM/YYYY, MM/DD/YYYY, Excel serials, and more.
    CRITICAL: Tries ISO format FIRST to avoid dayfirst misinterpretation.
    """
    if not raw or raw.lower() in NULL_VALUES:
        return None, None

    # Excel serial date (e.g. 44927.0)
    try:
        serial = float(raw)
        if 1000 < serial < 100000:
            from datetime import timedelta
            base = datetime(1899, 12, 30)
            dt = base + timedelta(days=serial)
            return dt.strftime('%d/%m/%Y'), dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        pass

    # Try ISO format FIRST (YYYY-MM-DD) — this is unambiguous
    iso_match = re.match(r'^(\d{4})[\-/](\d{1,2})[\-/](\d{1,2})$', raw)
    if iso_match:
        try:
            y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
            dt = datetime(y, m, d)
            return dt.strftime('%d/%m/%Y'), dt.strftime('%Y-%m-%d')
        except ValueError:
            pass

    # Try common explicit formats (DD/MM/YYYY priority for SG context)
    explicit_formats = [
        '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',        # DD/MM/YYYY
        '%d/%m/%y', '%d-%m-%y', '%d.%m.%y',         # DD/MM/YY
        '%m/%d/%Y', '%m-%d-%Y',                       # US fallback
        '%d %b %Y', '%d %B %Y',                       # 15 Jan 2000
        '%d-%b-%Y', '%d-%b-%y',                        # 15-Jan-2000
        '%b %d, %Y', '%B %d, %Y',                     # Jan 15, 2000
        '%Y%m%d',                                       # 20000115
    ]
    for fmt in explicit_formats:
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.year < 100:
                dt = dt.replace(year=dt.year + 2000 if dt.year <= 30 else dt.year + 1900)
            return dt.strftime('%d/%m/%Y'), dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    # Final fallback: dateutil (handles "January 15, 2000", etc.)
    try:
        dt = dateutil_parser.parse(raw, dayfirst=True)
        return dt.strftime('%d/%m/%Y'), dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError, OverflowError):
        pass

    return None, None


def _parse_race(raw):
    """Map raw race string to CMIO code."""
    raw = raw.lower().strip()
    if not raw:
        return 'O'
    for code, keywords in RACE_KEYWORDS.items():
        for kw in keywords:
            if kw in raw:
                return code
    return 'O'


def _parse_gender(raw):
    """Map raw gender string to M/F/U code."""
    raw = raw.lower().strip()
    if raw in GENDER_MALE:
        return 'M'
    elif raw in GENDER_FEMALE:
        return 'F'
    return 'U'


def _read_file(file_obj, header_row=0):
    """Read CSV or Excel, handling encodings. Returns a DataFrame with dtype=str."""
    file_obj.seek(0)
    try:
        if file_obj.name.endswith('.csv'):
            return pd.read_csv(file_obj, encoding='utf-8-sig', dtype=str, header=header_row)
        else:
            return pd.read_excel(file_obj, dtype=str, engine='openpyxl', header=header_row)
    except UnicodeDecodeError:
        file_obj.seek(0)
        return pd.read_csv(file_obj, encoding='cp1252', dtype=str, header=header_row)
    except Exception:
        file_obj.seek(0)
        return pd.read_csv(file_obj, encoding='latin1', dtype=str, header=header_row)


def _detect_header_row(file_obj):
    """
    Detect which row contains the real column headers.
    Some Excel exports have a title row (e.g. filename) before the headers.
    We scan the first 5 rows looking for one that contains known column keywords.
    """
    file_obj.seek(0)
    try:
        if file_obj.name.endswith('.csv'):
            df_raw = pd.read_csv(file_obj, encoding='utf-8-sig', dtype=str, header=None, nrows=10)
        else:
            df_raw = pd.read_excel(file_obj, dtype=str, engine='openpyxl', header=None, nrows=10)
    except Exception:
        return 0

    # Keywords that indicate a header row (checked in normalised form)
    header_keywords = {'name', 'email', 'dob', 'date_of_birth', 'race', 'gender',
                       'first_name', 'last_name', 'phone', 'birthday', 'ethnicity',
                       'client_id', 'sex', 'email_address', 'full_name'}

    for row_idx in range(min(5, len(df_raw))):
        row_vals = [_normalise_col(str(v)) for v in df_raw.iloc[row_idx].values if str(v).strip()]
        matches = sum(1 for v in row_vals if v in header_keywords)
        # If 3+ columns match known headers, this is the header row
        if matches >= 3:
            return row_idx

    return 0  # Default: first row is the header


def smart_parse_clients(file_obj):
    """
    Reads CSV/Excel, auto-detects columns, parses demographics, and deduplicates.
    Handles Apollo, HubSpot, Salesforce, Skandage CRM, Google Contacts exports.
    Also handles Excel files with a title row before the real headers.
    """
    # 1. Detect which row has the real headers (handles title rows)
    header_row = _detect_header_row(file_obj)

    # 2. Read file with the correct header row
    df = _read_file(file_obj, header_row=header_row)

    # 3. Clean NaN remnants
    df = df.fillna('')
    df = df.replace({'nan': '', 'NaN': '', 'NaT': '', 'None': ''})

    # 4. Normalise column names
    df.columns = [_normalise_col(c) for c in df.columns]

    # 4. Identify the correct column for each field ONCE (not per-row)
    email_col = _find_email_column(df.columns)
    name_col = _find_name_column(df.columns)
    first_name_col = _find_column(df.columns, FIRST_NAME_PRIORITY)
    last_name_col = _find_column(df.columns, LAST_NAME_PRIORITY)
    dob_col = _find_column(df.columns, DOB_PRIORITY)
    race_col = _find_column(df.columns, RACE_PRIORITY)
    gender_col = _find_column(df.columns, GENDER_PRIORITY)

    # --- NEW: HQ / Review Date columns ---
    phone_col = _find_column(df.columns, PHONE_PRIORITY)
    address_col = _find_column(df.columns, ADDRESS_PRIORITY)
    status_col = _find_column(df.columns, STATUS_PRIORITY)
    last_review_col = _find_column(df.columns, LAST_REVIEW_PRIORITY)
    next_review_col = _find_column(df.columns, NEXT_REVIEW_PRIORITY)
    review_freq_col = _find_column(df.columns, REVIEW_FREQ_PRIORITY)

    # 5. Parse rows
    parsed_clients = []
    seen_emails = set()
    seen_names = set()

    for _, row in df.iterrows():
        # --- EMAIL ---
        email = _safe_val(row, email_col).lower()
        # Validate: must contain @ to be a real email
        if email and '@' not in email:
            email = ''

        # --- NAME ---
        first_name = _safe_val(row, first_name_col)
        last_name = _safe_val(row, last_name_col)
        full_name = _safe_val(row, name_col)

        if first_name or last_name:
            name = f"{first_name} {last_name}".strip()
        elif full_name:
            name = full_name
        else:
            name = ''

        # Skip rows with neither email nor name
        if not email and not name:
            continue

        if not name:
            name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()

        # --- INTRA-FILE DEDUPLICATION ---
        if email:
            if email in seen_emails:
                continue
            seen_emails.add(email)
        else:
            if name.lower() in seen_names:
                continue
            seen_names.add(name.lower())

        # --- DATE OF BIRTH ---
        dob_raw = _safe_val(row, dob_col)
        dob_display, dob_db = _parse_date(dob_raw)

        # --- RACE & GENDER ---
        race_code = _parse_race(_safe_val(row, race_col))
        gender_code = _parse_gender(_safe_val(row, gender_col))

        # --- HQ FIELDS ---
        phone_raw = _safe_val(row, phone_col)
        address_raw = _safe_val(row, address_col)
        status_raw = _safe_val(row, status_col)

        # --- REVIEW DATE FIELDS ---
        # next_review: direct date (no calculation needed)
        next_review_raw = _safe_val(row, next_review_col)

        # last_review: date of last review — base for calculation
        last_review_raw = _safe_val(row, last_review_col)

        # review_freq: integer months until next review
        review_freq_raw = _safe_val(row, review_freq_col)
        # Normalise: strip any non-numeric suffix (e.g. "12 months" → "12")
        if review_freq_raw:
            import re as _re
            _m = _re.match(r'^(\d+(?:\.\d+)?)', review_freq_raw.strip())
            review_freq_raw = _m.group(1) if _m else review_freq_raw

        parsed_clients.append({
            'name': name,
            'email': email,
            'dob_display': dob_display,
            'dob_db': dob_db,
            'race': race_code,
            'gender': gender_code,
            # HQ fields
            'phone': phone_raw,
            'address': address_raw,
            'status': status_raw,
            # Review date fields (standardised lowercase keys)
            'next_review_date': next_review_raw,   # direct value if column exists
            'last_review': last_review_raw,         # base date for calculation
            'review_freq': review_freq_raw,         # duration in months
        })

    return parsed_clients
