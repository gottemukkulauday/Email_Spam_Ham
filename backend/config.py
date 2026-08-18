"""
Application configuration: file paths and environment overrides.

Every path can be overridden with an environment variable so the app can be
pointed at different datasets, models, or databases without code changes.
"""

# ════════════════════════════════════════════════════════════════
# IMPORTS
# ════════════════════════════════════════════════════════════════

import os

# ════════════════════════════════════════════════════════════════
# PROJECT ROOT
# ════════════════════════════════════════════════════════════════

# Project root: the parent of the backend/ directory
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ════════════════════════════════════════════════════════════════
# DATA & MODEL PATHS
# ════════════════════════════════════════════════════════════════

# Dataset path (can be overridden with DATASET_PATH environment variable)
DATASET_PATH = os.environ.get(
    'DATASET_PATH',
    os.path.join(ROOT, 'data', 'dataset.csv.gz')
)

# Trained ML model path (can be overridden with MODEL_PATH environment variable)
MODEL_PATH = os.environ.get(
    'MODEL_PATH',
    os.path.join(ROOT, 'backend', 'model', 'spam_pipeline.joblib')
)

# SQLite database path (can be overridden with DB_PATH environment variable)
DB_PATH = os.environ.get(
    'DB_PATH',
    os.path.join(ROOT, 'backend', 'history.db')
)

# ════════════════════════════════════════════════════════════════
# STATIC FILES
# ════════════════════════════════════════════════════════════════

# Static files directory (vanilla-JS frontend served by Flask)
FRONTEND_DIR = os.path.join(ROOT, 'frontend')
