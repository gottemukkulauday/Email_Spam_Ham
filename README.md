# Cognizant Hackathon — AI Email Spam Detection & Security Analyzer

Full-stack Flask + vanilla JS application with the existing Cognizant AI Security visual theme.

## Dataset inspection and integration
The two newly uploaded files were inspected before integration:

- `meajor_cleaned_preprocessed.csv` — 108,685 rows, 20 columns.
- `meajor_cleaned_preprocessed.parquet.gzip` — same dataset in Parquet representation; it is **not** a separate HAM-only or SPAM-only dataset.
- Both contain a `label` column with `0` and `1` values.
- Content inspection confirms label `0` is HAM / non-spam and label `1` is SPAM.
- One row has no label and was excluded from training.
- The raw CSV contains 13 exact duplicate rows.
- There are 3,751 repeated subject+body email contents; repeated email contents are deduplicated before training to avoid over-counting.
- Final training corpus: 104,933 unique labeled email messages.

A canonical `data/dataset.csv.gz` is used by the application so the same email is not trained twice simply because it exists in CSV and Parquet form. `data/dataset_manifest.json` records the inspection.

## ML pipeline
Subject and body are combined and transformed with TF-IDF word/bi-gram features. A balanced `SGDClassifier(loss="log_loss")` provides a real `predict_proba()` spam probability. The model was retrained from the inspected dataset with a stratified 80/20 split.

Validation on the held-out split:
- Accuracy: 97.08%
- Precision: 96.59%
- Recall: 96.87%
- F1: 96.73%

These are development metrics on this dataset, not a guarantee on future mail.

## Detection
The Detection page keeps the existing theme but now uses:

- Email Subject
- Email Body
- Analyze Email
- File upload for `.eml`, `.txt`, and `.csv`
- Model-derived SPAM/HAM prediction
- Model-derived spam-risk percentage
- Explainable reasons from observable email features plus model-weighted terms
- URL and contextual signal summaries

The file upload endpoint parses `.eml`, `.txt`, and `.csv`, then populates the Subject and Body fields. The user reviews the extracted content and clicks Analyze.

## Run on Windows
```powershell
python -m venv venv
venv\\Scripts\\activate
pip install -r backend\\requirements.txt
python backend\\app.py
```

Open `http://127.0.0.1:5000`.

If an older virtual environment already has scikit-learn 1.9.0, the included model is compatible with that version. If it has another version, recreate the environment or run:
```powershell
pip install --upgrade --force-reinstall scikit-learn==1.9.0
```

## Configuration
Set `DATASET_PATH` or `MODEL_PATH` if you want to replace the canonical dataset/model.
