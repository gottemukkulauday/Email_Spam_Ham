"""
════════════════════════════════════════════════════════════════
DATASET LOADING & NORMALIZATION
════════════════════════════════════════════════════════════════

Handles CSV / Parquet / gzip inputs, column detection, text cleaning,
label normalization, and deduplication. The loaded dataset is kept in
module state so Flask routes can read emails.
"""

import logging
import os

import pandas as pd

from config import DATASET_PATH

log = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════
# MODULE STATE
# ════════════════════════════════════════════════════════════════

# Loaded dataset DataFrame
_dataset = pd.DataFrame()

# Flag indicating whether dataset has been loaded
_dataset_loaded = False

# ════════════════════════════════════════════════════════════════
# LABEL ALIASES
# ════════════════════════════════════════════════════════════════

# Mappings for converting various label formats to 0 (HAM) or 1 (SPAM)
LABEL_ALIASES = {
    'spam': 1, 'sp': 1, '1': 1, 'true': 1, 'yes': 1,
    'ham': 0, 'not spam': 0, 'not_spam': 0, 'non-spam': 0,
    'nonspam': 0, '0': 0, 'false': 0, 'no': 0,
}


# ════════════════════════════════════════════════════════════════
# TEXT CLEANING
# ════════════════════════════════════════════════════════════════

def clean_text(value):
    """
    Coerce a cell value to a trimmed string (empty string for NaN/None).
    
    Args:
        value: Any value from a DataFrame cell
        
    Returns:
        str: Trimmed string, or empty string if value is NaN/None
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ''
    return str(value).strip()


# ════════════════════════════════════════════════════════════════
# COLUMN DETECTION
# ════════════════════════════════════════════════════════════════

def pick_col(columns, candidates):
    """
    Find the column that best matches one of the candidate names.
    
    Args:
        columns: List of column names from DataFrame
        candidates: List of desired column names (in preference order)
        
    Returns:
        str: Best matching column name, or None if no match found
    """
    # First pass: exact match (case-insensitive)
    low = {str(c).strip().lower(): c for c in columns}
    for name in candidates:
        if name in low:
            return low[name]

    # Second pass: substring match
    for c in columns:
        cl = str(c).strip().lower()
        if any(name in cl for name in candidates):
            return c

    return None


# ════════════════════════════════════════════════════════════════
# LABEL NORMALIZATION
# ════════════════════════════════════════════════════════════════

def normalize_label(value):
    """
    Convert a label cell (spam/ham/0/1/...) to 0 or 1, or None.
    
    Args:
        value: Label cell value from DataFrame
        
    Returns:
        int: 0 (HAM), 1 (SPAM), or None if label cannot be normalized
    """
    if pd.isna(value):
        return None

    s = str(value).strip().lower()

    # Check against known aliases
    if s in LABEL_ALIASES:
        return LABEL_ALIASES[s]

    # Try parsing as numeric
    try:
        n = float(s)
        if n in (0, 1):
            return int(n)
    except Exception:
        pass

    return None


# ════════════════════════════════════════════════════════════════
# DATASET LOADING
# ════════════════════════════════════════════════════════════════

def load_dataset(path=DATASET_PATH):
    """
    Load, clean, and deduplicate the email corpus into module state.
    
    Handles multiple file formats (CSV, Parquet, gzip), auto-detects
    column names, normalizes labels, and deduplicates by subject+body.
    
    Args:
        path (str): Path to dataset file (CSV, Parquet, or gzip)
    """
    global _dataset, _dataset_loaded

    # Check if file exists
    if not os.path.exists(path):
        _dataset = pd.DataFrame()
        _dataset_loaded = False
        return

    try:
        # ════════════════════════════════════════════════════════
        # LOAD RAW DATA
        # ════════════════════════════════════════════════════════
        if path.lower().endswith(('.parquet', '.parquet.gzip', '.gzip')):
            try:
                raw = pd.read_parquet(path)
            except Exception:
                raw = pd.read_csv(path)
        else:
            raw = pd.read_csv(path)

        # ════════════════════════════════════════════════════════
        # DETECT & EXTRACT COLUMNS
        # ════════════════════════════════════════════════════════
        cols = {str(c).strip().lower(): c for c in raw.columns}

        # Find email content columns
        subject_col = pick_col(raw.columns, ['subject', 'title'])
        body_col = pick_col(raw.columns, ['body', 'email', 'text', 'message', 'content'])
        label_col = pick_col(raw.columns, ['label', 'spam', 'class', 'target', 'is_spam'])

        if not body_col:
            raise ValueError('No email body/text column found in dataset')

        # ════════════════════════════════════════════════════════
        # BUILD CLEANED DATAFRAME
        # ════════════════════════════════════════════════════════
        out = pd.DataFrame()
        out['subject'] = raw[subject_col].map(clean_text) if subject_col else ''
        out['body'] = raw[body_col].map(clean_text)

        # Add sender/recipient if available
        sender_col = pick_col(raw.columns, ['sender', 'from', 'from_email', 'email_from'])
        recipient_col = pick_col(raw.columns, ['recipient', 'receiver', 'to', 'to_email'])
        out['sender'] = raw[sender_col].map(clean_text) if sender_col else ''
        out['recipient'] = raw[recipient_col].map(clean_text) if recipient_col else ''

        # Add URLs if available
        urls_col = pick_col(raw.columns, ['urls', 'url', 'links'])
        out['urls'] = raw[urls_col].map(clean_text) if urls_col else ''

        # Normalize labels
        out['label'] = raw[label_col].map(normalize_label) if label_col else None

        # ════════════════════════════════════════════════════════
        # CLEAN & DEDUPLICATE
        # ════════════════════════════════════════════════════════
        # Remove rows with empty subject and body
        out = out[(out['subject'].str.len() + out['body'].str.len()) > 0].copy()

        # Deduplicate by subject+body (keep first occurrence)
        out = out.drop_duplicates(
            subset=['subject', 'body'],
            keep='first'
        ).reset_index(drop=True)

        _dataset = out
        _dataset_loaded = True

    except Exception as exc:
        log.exception('Dataset load failed: %s', exc)
        _dataset = pd.DataFrame()
        _dataset_loaded = False



def row_email(i):
    """Return dataset row i as a plain dict for the API."""
    r = _dataset.iloc[i]
    return {k: clean_text(r[k]) for k in ['sender', 'recipient', 'subject', 'body', 'urls']} | {'dataset_label': None if pd.isna(r['label']) else int(r['label'])}
