"""
════════════════════════════════════════════════════════════════
SQLITE DATABASE PERSISTENCE
════════════════════════════════════════════════════════════════

Manages SQLite database for storing and retrieving detection history.
"""

import sqlite3

from config import DB_PATH


# ════════════════════════════════════════════════════════════════
# DATABASE CONNECTION
# ════════════════════════════════════════════════════════════════

def db():
    """
    Open a connection to the history database.
    
    Configures row factory to return Row objects (dict-like access)
    instead of tuples.
    
    Returns:
        sqlite3.Connection: Database connection object
    """
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


# ════════════════════════════════════════════════════════════════
# DATABASE INITIALIZATION
# ════════════════════════════════════════════════════════════════

def init_db():
    """
    Create the analyses table if it does not exist yet.
    
    Table schema:
    - id (TEXT PRIMARY KEY): UUID of the analysis
    - sender (TEXT): Email sender address
    - recipient (TEXT): Email recipient address
    - subject (TEXT): Email subject
    - body (TEXT): Email body
    - classification (TEXT): 'SPAM' or 'HAM'
    - spam_risk (REAL): Spam risk percentage
    - confidence (REAL): Confidence percentage
    - overall_risk (REAL): Overall risk score
    - reasons (TEXT): JSON array of reason strings
    - features (TEXT): JSON object with full analysis result
    - created_at (TEXT): ISO timestamp of creation
    """
    connection = db()
    connection.execute('''
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            sender TEXT,
            recipient TEXT,
            subject TEXT,
            body TEXT,
            classification TEXT,
            spam_risk REAL,
            confidence REAL,
            overall_risk REAL,
            reasons TEXT,
            features TEXT,
            created_at TEXT
        )
    ''')
    connection.commit()
    connection.close()
