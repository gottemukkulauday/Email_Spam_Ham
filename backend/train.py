"""Retrain the spam detection pipeline.

Usage:
    python backend/train.py [extra.csv ...]

- Loads the canonical dataset (data/dataset.csv.gz by default, or $DATASET_PATH).
- Loads every extra CSV/Parquet passed as an argument. Each must contain
  subject/body (or text) and a label column (0/1, ham/spam, etc.).
- Merges, cleans, deduplicates by subject+body, retrains the same pipeline the
  app uses (TF-IDF word/bi-gram -> balanced SGDClassifier log_loss), evaluates
  on a stratified 80/20 split, and saves:
      - model  : $MODEL_PATH  (default backend/model/spam_pipeline.joblib)
      - dataset: $DATASET_PATH (default data/dataset.csv.gz) as the merged canonical copy

Text is combined exactly like app.py: "Subject: {subject}\n\n{body}".
"""
import os
import sys

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.environ.get('DATASET_PATH', os.path.join(ROOT, 'data', 'dataset.csv.gz'))
MODEL_PATH = os.environ.get('MODEL_PATH', os.path.join(ROOT, 'backend', 'model', 'spam_pipeline.joblib'))

LABEL_ALIASES = {
    'spam': 1, 'sp': 1, '1': 1, 'true': 1, 'yes': 1,
    'ham': 0, 'not spam': 0, 'not_spam': 0, 'non-spam': 0,
    'nonspam': 0, '0': 0, 'false': 0, 'no': 0,
}


def clean_text(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ''
    return str(value).strip()


def pick_col(columns, candidates):
    low = {str(c).strip().lower(): c for c in columns}
    for name in candidates:
        if name in low:
            return low[name]
    for c in columns:
        cl = str(c).strip().lower()
        if any(name in cl for name in candidates):
            return c
    return None


def normalize_label(value):
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


def load_frame(path):
    """Read a dataset file into a normalized (subject, body, label) frame."""
    if path.lower().endswith(('.parquet', '.parquet.gzip', '.gzip')):
        try:
            raw = pd.read_parquet(path)
        except Exception:
            raw = pd.read_csv(path)
    else:
        raw = pd.read_csv(path)
    subject_col = pick_col(raw.columns, ['subject', 'title'])
    body_col = pick_col(raw.columns, ['body', 'email', 'text', 'message', 'content'])
    label_col = pick_col(raw.columns, ['label', 'spam', 'class', 'target', 'is_spam'])
    if not body_col:
        raise ValueError(f'{path}: no email body/text column found')
    out = pd.DataFrame()
    out['subject'] = raw[subject_col].map(clean_text) if subject_col else ''
    out['body'] = raw[body_col].map(clean_text)
    out['label'] = raw[label_col].map(normalize_label) if label_col else None
    return out


def combine_text(subject, body):
    subject = clean_text(subject)
    body = clean_text(body)
    return f'Subject: {subject}\n\n{body}'.strip()


def main():
    extra_paths = sys.argv[1:]
    for p in extra_paths:
        if not os.path.exists(p):
            print(f'ERROR: file not found: {p}')
            sys.exit(1)

    if not os.path.exists(DATASET_PATH):
        print(f'ERROR: canonical dataset not found: {DATASET_PATH}')
        sys.exit(1)

    raw_counts = {}

    old = load_frame(DATASET_PATH)
    raw_counts['canonical'] = len(old)
    print(f'Loaded canonical: {len(old)} rows')

    new_frames = []
    for p in extra_paths:
        f = load_frame(p)
        new_frames.append(f)
        raw_counts[os.path.basename(p)] = len(f)
        print(f'Loaded {os.path.basename(p)}: {len(f)} rows')

    df = pd.concat([old] + new_frames, ignore_index=True)
    n_before = len(df)

    df = df.dropna(subset=['label'])
    n_labeled = len(df)
    df = df[df['label'].map(lambda x: x in (0, 1))]
    df = df[(df['subject'].str.len() + df['body'].str.len()) > 0]
    n_nonempty = len(df)
    df = df.drop_duplicates(subset=['subject', 'body'], keep='first').reset_index(drop=True)
    n_unique = len(df)

    print(f'\nCleaning: {n_before} -> missing label -> {n_labeled} -> non-empty -> {n_nonempty} -> unique -> {n_unique}')
    print('Label distribution after dedup:')
    print(df['label'].value_counts().sort_index().to_string())

    text = df.apply(lambda r: combine_text(r['subject'], r['body']), axis=1)
    y = df['label'].values

    X_train, X_test, y_train, y_test = train_test_split(
        text, y, test_size=0.2, stratify=y, random_state=42)

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            max_df=0.995, max_features=250000, min_df=2, ngram_range=(1, 2),
            strip_accents='unicode', sublinear_tf=True)),
        ('clf', SGDClassifier(loss='log_loss', class_weight='balanced', random_state=42)),
    ])

    print('\nTraining...')
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    print(f'\nValidation (stratified 80/20):')
    print(f'  Accuracy : {acc:.4f}')
    print(f'  Precision: {prec:.4f}')
    print(f'  Recall   : {rec:.4f}')
    print(f'  F1       : {f1:.4f}')
    print(f'  Classes  : {list(pipeline.classes_)}')

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f'Saved model: {MODEL_PATH}')

    # Save the merged canonical dataset (sender/recipient/urls empty for new rows)
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

    print('\n--- SUMMARY (for manifest) ---')
    import json
    summary = {
        'raw_counts': {k: int(v) for k, v in raw_counts.items()},
        'merged_raw_rows': int(n_before),
        'rows_after_label_filter': int(n_labeled),
        'rows_after_nonempty_filter': int(n_nonempty),
        'training_rows_after_dedup': int(n_unique),
        'label_counts': {str(k): int(v) for k, v in df['label'].value_counts().sort_index().items()},
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


if __name__ == '__main__':
    main()
