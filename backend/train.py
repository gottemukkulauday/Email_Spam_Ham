"""
════════════════════════════════════════════════════════════════
MODEL TRAINING & RETRAINING PIPELINE
════════════════════════════════════════════════════════════════

Retrain the spam detection model using TF-IDF + SGDClassifier.

Usage:
    python backend/train.py [extra.csv ...]

Behavior:
- Loads the canonical dataset (data/dataset.csv.gz, or $DATASET_PATH)
- Merges with any extra CSV/Parquet files passed as arguments
- Each file must contain subject/body (or text) and label column
- Cleans, deduplicates by subject+body
- Retrains TF-IDF word/bi-gram → balanced SGDClassifier log_loss
- Evaluates on stratified 80/20 split
- Saves model and merged dataset

Text combination:
    "Subject: {subject}\n\n{body}"
"""

import json
import os
import sys

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

# ════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.environ.get(
    'DATASET_PATH',
    os.path.join(ROOT, 'data', 'dataset.csv.gz')
)
MODEL_PATH = os.environ.get(
    'MODEL_PATH',
    os.path.join(ROOT, 'backend', 'model', 'spam_pipeline.joblib')
)

# ════════════════════════════════════════════════════════════════
# LABEL ALIASES
# ════════════════════════════════════════════════════════════════

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
    Coerce a cell value to a trimmed string.
    
    Args:
        value: Any value from a DataFrame cell
        
    Returns:
        str: Trimmed string, or empty string if NaN/None
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
        columns: List of column names
        candidates: List of desired column names (in preference order)
        
    Returns:
        str: Best matching column name, or None if no match
    """
    # Exact match (case-insensitive)
    low = {str(c).strip().lower(): c for c in columns}
    for name in candidates:
        if name in low:
            return low[name]

    # Substring match
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
        value: Label cell value
        
    Returns:
        int: 0 (HAM), 1 (SPAM), or None
    """
    if pd.isna(value):
        return None

    s = str(value).strip().lower()

    if s in LABEL_ALIASES:
        return LABEL_ALIASES[s]

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

def load_frame(path):
    """
    Read a dataset file into a normalized (subject, body, label) frame.
    
    Handles CSV, Parquet, and gzip files. Auto-detects column names.
    
    Args:
        path (str): Path to dataset file
        
    Returns:
        pd.DataFrame: With columns [subject, body, label]
        
    Raises:
        ValueError: If no body/text column found
    """
    # Load file
    if path.lower().endswith(('.parquet', '.parquet.gzip', '.gzip')):
        try:
            raw = pd.read_parquet(path)
        except Exception:
            raw = pd.read_csv(path)
    else:
        raw = pd.read_csv(path)

    # Detect columns
    subject_col = pick_col(raw.columns, ['subject', 'title'])
    body_col = pick_col(raw.columns, ['body', 'email', 'text', 'message', 'content'])
    label_col = pick_col(raw.columns, ['label', 'spam', 'class', 'target', 'is_spam'])

    if not body_col:
        raise ValueError(f'{path}: no email body/text column found')

    # Build normalized frame
    out = pd.DataFrame()
    out['subject'] = raw[subject_col].map(clean_text) if subject_col else ''
    out['body'] = raw[body_col].map(clean_text)
    out['label'] = raw[label_col].map(normalize_label) if label_col else None

    return out


# ════════════════════════════════════════════════════════════════
# TEXT COMBINATION
# ════════════════════════════════════════════════════════════════

def combine_text(subject, body):
    """
    Combine subject and body into a single text string.
    
    Format: "Subject: {subject}\n\n{body}"
    
    Args:
        subject (str): Email subject
        body (str): Email body
        
    Returns:
        str: Combined text
    """
    subject = clean_text(subject)
    body = clean_text(body)
    return f'Subject: {subject}\n\n{body}'.strip()


# ════════════════════════════════════════════════════════════════
# MAIN TRAINING FUNCTION
# ════════════════════════════════════════════════════════════════

def main():
    """Main training pipeline."""
    extra_paths = sys.argv[1:]

    # ════════════════════════════════════════════════════════════
    # VALIDATE INPUT FILES
    # ════════════════════════════════════════════════════════════
    for path in extra_paths:
        if not os.path.exists(path):
            print(f'ERROR: file not found: {path}')
            sys.exit(1)

    if not os.path.exists(DATASET_PATH):
        print(f'ERROR: canonical dataset not found: {DATASET_PATH}')
        sys.exit(1)

    raw_counts = {}

    # ════════════════════════════════════════════════════════════
    # LOAD DATASETS
    # ════════════════════════════════════════════════════════════
    print('Loading datasets...')

    old = load_frame(DATASET_PATH)
    raw_counts['canonical'] = len(old)
    print(f'  Loaded canonical: {len(old)} rows')

    new_frames = []
    for path in extra_paths:
        frame = load_frame(path)
        new_frames.append(frame)
        raw_counts[os.path.basename(path)] = len(frame)
        print(f'  Loaded {os.path.basename(path)}: {len(frame)} rows')

    # ════════════════════════════════════════════════════════════
    # MERGE & CLEAN
    # ════════════════════════════════════════════════════════════
    df = pd.concat([old] + new_frames, ignore_index=True)
    n_before = len(df)

    # Remove rows without labels
    df = df.dropna(subset=['label'])
    n_labeled = len(df)

    # Keep only valid labels (0 or 1)
    df = df[df['label'].map(lambda x: x in (0, 1))]

    # Remove empty subject+body
    df = df[(df['subject'].str.len() + df['body'].str.len()) > 0]
    n_nonempty = len(df)

    # Deduplicate by subject+body
    df = df.drop_duplicates(
        subset=['subject', 'body'],
        keep='first'
    ).reset_index(drop=True)
    n_unique = len(df)

    print(f'\nCleaning pipeline:')
    print(f'  {n_before} → (missing label) → {n_labeled} → (non-empty) → {n_nonempty} → (unique) → {n_unique}')

    print('\nLabel distribution after dedup:')
    print(df['label'].value_counts().sort_index().to_string())

    # ════════════════════════════════════════════════════════════
    # PREPARE DATA
    # ════════════════════════════════════════════════════════════
    text = df.apply(lambda row: combine_text(row['subject'], row['body']), axis=1)
    y = df['label'].values

    X_train, X_test, y_train, y_test = train_test_split(
        text, y,
        test_size=0.2,
        stratify=y,
        random_state=42
    )

    # ════════════════════════════════════════════════════════════
    # TRAIN MODEL
    # ════════════════════════════════════════════════════════════
    print('\nTraining model...')

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            max_df=0.995,
            max_features=250000,
            min_df=2,
            ngram_range=(1, 2),
            strip_accents='unicode',
            sublinear_tf=True
        )),
        ('clf', SGDClassifier(
            loss='log_loss',
            class_weight='balanced',
            random_state=42
        )),
    ])

    pipeline.fit(X_train, y_train)

    # ════════════════════════════════════════════════════════════
    # EVALUATE
    # ════════════════════════════════════════════════════════════
    y_pred = pipeline.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    print(f'\nValidation (stratified 80/20 split):')
    print(f'  Accuracy:  {acc:.4f}')
    print(f'  Precision: {prec:.4f}')
    print(f'  Recall:    {rec:.4f}')
    print(f'  F1 Score:  {f1:.4f}')
    print(f'  Classes:   {list(pipeline.classes_)}')

    # ════════════════════════════════════════════════════════════
    # SAVE MODEL
    # ════════════════════════════════════════════════════════════
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f'\nSaved model: {MODEL_PATH}')

    # ════════════════════════════════════════════════════════════
    # SAVE MERGED DATASET
    # ════════════════════════════════════════════════════════════
    canonical = pd.DataFrame({
        'sender': old['sender'] if 'sender' in old.columns else '',
        'recipient': old['recipient'] if 'recipient' in old.columns else '',
        'subject': df['subject'],
        'body': df['body'],
        'urls': old['urls'] if 'urls' in old.columns else '',
        'label': df['label'],
    })

    os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
    canonical.to_csv(DATASET_PATH, index=False, compression='gzip')
    print(f'Saved merged dataset: {DATASET_PATH} ({len(canonical)} rows)')

    # ════════════════════════════════════════════════════════════
    # GENERATE SUMMARY
    # ════════════════════════════════════════════════════════════
    print('\n' + '=' * 60)
    print('SUMMARY (for manifest)')
    print('=' * 60)

    summary = {
        'raw_counts': {k: int(v) for k, v in raw_counts.items()},
        'merged_raw_rows': int(n_before),
        'rows_after_label_filter': int(n_labeled),
        'rows_after_nonempty_filter': int(n_nonempty),
        'training_rows_after_dedup': int(n_unique),
        'label_counts': {
            str(k): int(v)
            for k, v in df['label'].value_counts().sort_index().items()
        },
        'metrics': {
            'accuracy': round(float(acc), 4),
            'precision': round(float(prec), 4),
            'recall': round(float(rec), 4),
            'f1': round(float(f1), 4),
        },
        'model_path': MODEL_PATH,
        'dataset_path': DATASET_PATH,
    }

    print(json.dumps(summary, indent=2))


# ════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    main()
