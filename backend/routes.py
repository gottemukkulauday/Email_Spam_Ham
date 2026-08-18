"""
════════════════════════════════════════════════════════════════
HTTP ROUTES FOR FLASK APPLICATION
════════════════════════════════════════════════════════════════

Routes are registered onto the app instance created in app.py,
keeping the web layer separate from the analysis logic.

Endpoints:
- GET  /                  - Serve frontend index.html
- GET  /<path>           - Serve static files
- GET  /api/status       - Get dataset/model load status
- GET  /api/email/<i>    - Get specific email by index
- POST /api/analyze      - Analyze an email
- GET  /api/history      - Get detection history
- DELETE /api/history/<id> - Delete history record
- GET  /api/dashboard    - Get dashboard statistics
- POST /api/dataset-upload - Upload new dataset
"""

import json
import os
import uuid
from datetime import datetime, timezone

from flask import request, jsonify, send_from_directory

import config
import dataset
from analyzer import analyze_email
from db import db as get_db
from model_service import MODEL


# ════════════════════════════════════════════════════════════════
# ROUTE REGISTRATION
# ════════════════════════════════════════════════════════════════

def register_routes(app):
    """
    Attach all HTTP endpoints to the Flask app.
    
    Args:
        app: Flask application instance
    """

    # ════════════════════════════════════════════════════════════
    # STATIC FILES & INDEX
    # ════════════════════════════════════════════════════════════

    @app.route('/')
    def index():
        """Serve the main HTML file."""
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/<path:path>')
    def static_files(path):
        """Serve CSS, JS, and other static files."""
        return send_from_directory(app.static_folder, path)

    # ════════════════════════════════════════════════════════════
    # API STATUS
    # ════════════════════════════════════════════════════════════

    @app.get('/api/status')
    def status():
        """
        Get application status (dataset loaded, model loaded).
        
        Returns:
            JSON with:
            - dataset_loaded: bool
            - dataset_count: int
            - label_counts: dict (0/1 label distribution)
            - model_loaded: bool
        """
        labels = (
            dataset._dataset['label'].value_counts(dropna=True).to_dict()
            if dataset._dataset_loaded
            else {}
        )
        return jsonify({
            'dataset_loaded': dataset._dataset_loaded,
            'dataset_count': len(dataset._dataset),
            'label_counts': labels,
            'model_loaded': MODEL is not None
        })

    # ════════════════════════════════════════════════════════════
    # EMAIL RETRIEVAL
    # ════════════════════════════════════════════════════════════

    @app.get('/api/email/<int:i>')
    def get_email(i):
        """
        Retrieve an email from the dataset by index.
        
        Args:
            i (int): Dataset row index
            
        Returns:
            JSON email object or 404 error
        """
        if not dataset._dataset_loaded or i < 0 or i >= len(dataset._dataset):
            return jsonify({'error': 'Dataset index out of range'}), 404

        return jsonify({
            'index': i,
            'total': len(dataset._dataset),
            'email': dataset.row_email(i)
        })

    # ════════════════════════════════════════════════════════════
    # EMAIL ANALYSIS
    # ════════════════════════════════════════════════════════════

    @app.post('/api/analyze')
    def analyze():
        """
        Analyze an email for spam/ham classification.
        
        Request body (JSON):
        {
          "sender": "from@example.com",
          "recipient": "to@example.com",
          "subject": "Email subject",
          "body": "Email body text"
        }
        
        Returns:
            JSON with:
            - id: Analysis record UUID
            - created_at: ISO timestamp
            - result: Full analysis payload
        """
        email = request.get_json(force=True) or {}

        try:
            # Analyze the email
            result = analyze_email(email)
        except (ValueError, RuntimeError) as exc:
            return jsonify({'error': str(exc)}), 400

        # ════════════════════════════════════════════════════════
        # STORE IN HISTORY
        # ════════════════════════════════════════════════════════
        analysis_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conn = get_db()

        conn.execute(
            'INSERT INTO analyses VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
            (
                analysis_id,
                email.get('sender', ''),
                email.get('recipient', ''),
                email.get('subject', ''),
                email.get('body', ''),
                result['prediction'],
                result['spam_risk'],
                result['confidence'],
                result['overall_risk'],
                json.dumps(result['reasons']),
                json.dumps(result),
                now
            )
        )
        conn.commit()
        conn.close()

        return jsonify({
            'id': analysis_id,
            'created_at': now,
            'result': result
        })

    # ════════════════════════════════════════════════════════════
    # DETECTION HISTORY
    # ════════════════════════════════════════════════════════════

    @app.get('/api/history')
    def history():
        """
        Get all detection records from history.
        
        Returns:
            JSON array of analysis records (newest first)
        """
        conn = get_db()
        rows = [
            dict(r)
            for r in conn.execute(
                'SELECT * FROM analyses ORDER BY created_at DESC'
            ).fetchall()
        ]
        conn.close()

        # Parse JSON fields
        for record in rows:
            record['reasons'] = json.loads(record['reasons'])
            record['features'] = json.loads(record['features'])

        return jsonify(rows)

    @app.delete('/api/history/<aid>')
    def delete_history(aid):
        """
        Delete a specific detection record.
        
        Args:
            aid (str): Analysis record UUID
            
        Returns:
            JSON success response
        """
        conn = get_db()
        conn.execute('DELETE FROM analyses WHERE id=?', (aid,))
        conn.commit()
        conn.close()

        return jsonify({'ok': True})

    # ════════════════════════════════════════════════════════════
    # DASHBOARD STATISTICS
    # ════════════════════════════════════════════════════════════

    @app.get('/api/dashboard')
    def dashboard():
        """
        Get dashboard statistics (total, spam, ham, sender breakdown).
        
        Returns:
            JSON with:
            - total: Total emails analyzed
            - spam: Count of spam emails
            - not_spam: Count of ham emails
            - domains: List of sender domain statistics
        """
        conn = get_db()
        rows = [
            dict(r)
            for r in conn.execute(
                'SELECT * FROM analyses ORDER BY created_at DESC'
            ).fetchall()
        ]
        conn.close()

        # Count spam vs ham
        spam_count = sum(1 for r in rows if r['classification'] == 'SPAM')

        # Build domain statistics
        domains = {}
        for record in rows:
            sender = dataset.clean_text(record.get('sender'))

            # Extract domain from sender email
            domain = (
                sender.rsplit('@', 1)[-1].lower()
                if '@' in sender
                else sender or 'Unknown sender'
            )

            # Initialize domain entry if needed
            if domain not in domains:
                domains[domain] = {
                    'domain': domain,
                    'spam': 0,
                    'ham': 0
                }

            # Increment spam/ham count
            if record['classification'] == 'SPAM':
                domains[domain]['spam'] += 1
            else:
                domains[domain]['ham'] += 1

        # Sort by total emails (descending)
        domain_list = sorted(
            domains.values(),
            key=lambda x: x['spam'] + x['ham'],
            reverse=True
        )

        return jsonify({
            'total': len(rows),
            'spam': spam_count,
            'not_spam': len(rows) - spam_count,
            'domains': domain_list
        })

    # ════════════════════════════════════════════════════════════
    # DATASET UPLOAD
    # ════════════════════════════════════════════════════════════

    @app.post('/api/dataset-upload')
    def dataset_upload():
        """
        Upload and load a new dataset file.
        
        Request: multipart/form-data with 'file' parameter
        
        Returns:
            JSON with:
            - ok: bool
            - count: Number of emails loaded
        """
        file = request.files.get('file')

        if not file:
            return jsonify({'error': 'No dataset uploaded'}), 400

        # Save uploaded file
        upload_path = os.path.join(config.ROOT, 'data', 'uploaded_dataset.csv')
        file.save(upload_path)

        # Load the dataset
        dataset.load_dataset(upload_path)

        return jsonify({
            'ok': True,
            'count': len(dataset._dataset)
        })

