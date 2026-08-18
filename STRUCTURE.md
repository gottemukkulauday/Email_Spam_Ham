# Project Structure

This project is organized to make it easy to find and understand the code.
The backend is a modular Flask app; the frontend is a set of small vanilla-JS
modules loaded in order. No data files were changed by this restructuring.

```
emaildetection
├── backend/                     # Flask (Python) backend
│   ├── app.py                   # Entry point: creates the Flask app, initializes state, starts the server
│   ├── config.py                # File paths (dataset, model, DB) + environment overrides
│   ├── dataset.py               # Loads/cleans the email corpus (CSV/Parquet/gzip, dedup, labels)
│   ├── features.py              # Rule-based signals: URLs, language patterns, sender checks
│   ├── model_service.py         # Loads the ML model + extracts model-weighted explanation terms
│   ├── analyzer.py              # Orchestrates one analysis: model prediction + signals -> result payload
│   ├── routes.py                # All HTTP endpoints (register_routes): status, analyze, history, dashboard...
│   ├── db.py                    # SQLite helpers for the detection history table
│   ├── model/spam_pipeline.joblib  # Trained TF-IDF + SGDClassifier model
│   ├── history.db               # SQLite database of past detections
│   ├── train.py                 # Retraining script for the spam model
│   └── app.py.orig              # Backup of the original monolithic app.py (informational)
├── frontend/                    # Vanilla-JS frontend served by Flask
│   ├── index.html               # Loads the JS modules in dependency order
│   ├── style.css                # All styling (dark AI-security theme)
│   ├── assets/bg.jpg            # Background image
│   ├── js/
│   │   ├── helpers.js           # esc(), api(), toast() — shared utilities
│   │   ├── state.js             # Global state, nav bar, render()/go() page switching
│   │   ├── main.js              # Boot: renders the home page on load
│   │   ├── pages/
│   │   │   ├── home.js          # Home page (hero, features, model performance)
│   │   │   ├── detection.js     # Detection page (email form + results)
│   │   │   ├── history.js       # History page (audit table, search, filters)
│   │   │   └── dashboard.js     # Dashboard page (stats, sender cards, bar-chart modal)
│   │   └── (app.js.bak is the backup of the original single-file app.js)
├── data/                        # Training corpus
│   ├── dataset.csv.gz           # Canonical labeled email dataset
│   └── dataset_manifest.json    # Inspection/validation record
├── docs/                        # Documentation
├── run.bat / run.sh / run_project.py  # Launch scripts
└── README.md                    # Project overview & ML pipeline details
```

## How the backend fits together

```
app.py  →  creates Flask app
        →  dataset.load_dataset()   (loads data/dataset.csv.gz)
        →  db.init_db()             (creates the history table)
        →  register_routes(app)     (routes.py attaches all endpoints)

/api/analyze  →  routes.analyze  →  analyzer.analyze_email
                                       ├─ features.feature_signals      (rule-based signals)
                                       ├─ model_service.MODEL.predict  (ML probability)
                                       └─ model_service.model_explanations (top terms)
```

## How the frontend loads

Scripts load in this order in `index.html` (each is a plain script sharing globals):

```
helpers.js  →  state.js  →  pages/home.js → pages/detection.js
            →  pages/history.js  →  pages/dashboard.js  →  main.js (boot)
```

`state.js` decides which page function to render based on `state.page`:
`home → about()`, `detection → detection()`, `history → history()`, `dashboard → dashboard()`.
