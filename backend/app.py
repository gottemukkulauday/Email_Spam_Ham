import os, re, io, json, sqlite3, uuid
from email import policy
from email.parser import BytesParser
from datetime import datetime, timezone
from urllib.parse import urlparse

import joblib
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.environ.get('DATASET_PATH', os.path.join(ROOT, 'data', 'dataset.csv.gz'))
MODEL_PATH = os.environ.get('MODEL_PATH', os.path.join(ROOT, 'backend', 'model', 'spam_pipeline.joblib'))
DB_PATH = os.environ.get('DB_PATH', os.path.join(ROOT, 'backend', 'history.db'))

app = Flask(__name__, static_folder=os.path.join(ROOT, 'frontend'), static_url_path='')
MODEL = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None
_dataset = pd.DataFrame()
_dataset_loaded = False

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


def load_dataset(path=DATASET_PATH):
    global _dataset, _dataset_loaded
    if not os.path.exists(path):
        _dataset = pd.DataFrame()
        _dataset_loaded = False
        return
    try:
        if path.lower().endswith(('.parquet', '.parquet.gzip', '.gzip')):
            try:
                raw = pd.read_parquet(path)
            except Exception:
                raw = pd.read_csv(path)
        else:
            raw = pd.read_csv(path)
        cols = {str(c).strip().lower(): c for c in raw.columns}
        subject_col = pick_col(raw.columns, ['subject', 'title'])
        body_col = pick_col(raw.columns, ['body', 'email', 'text', 'message', 'content'])
        label_col = pick_col(raw.columns, ['label', 'spam', 'class', 'target', 'is_spam'])
        if not body_col:
            raise ValueError('No email body/text column found in dataset')
        out = pd.DataFrame()
        out['subject'] = raw[subject_col].map(clean_text) if subject_col else ''
        out['body'] = raw[body_col].map(clean_text)
        sender_col = pick_col(raw.columns, ['sender', 'from', 'from_email', 'email_from'])
        recipient_col = pick_col(raw.columns, ['recipient', 'receiver', 'to', 'to_email'])
        out['sender'] = raw[sender_col].map(clean_text) if sender_col else ''
        out['recipient'] = raw[recipient_col].map(clean_text) if recipient_col else ''
        urls_col = pick_col(raw.columns, ['urls', 'url', 'links'])
        out['urls'] = raw[urls_col].map(clean_text) if urls_col else ''
        out['label'] = raw[label_col].map(normalize_label) if label_col else None
        out = out[(out['subject'].str.len() + out['body'].str.len()) > 0].copy()
        out = out.drop_duplicates(subset=['subject', 'body'], keep='first').reset_index(drop=True)
        _dataset = out
        _dataset_loaded = True
    except Exception as exc:
        app.logger.exception('Dataset load failed: %s', exc)
        _dataset = pd.DataFrame()
        _dataset_loaded = False


load_dataset()


def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    c = db()
    c.execute('''CREATE TABLE IF NOT EXISTS analyses(
      id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, subject TEXT, body TEXT,
      classification TEXT, spam_risk REAL, confidence REAL, overall_risk REAL,
      reasons TEXT, features TEXT, created_at TEXT)''')
    c.commit(); c.close()


init_db()


def extract_urls(text):
    return re.findall(r'https?://[^\s<>"\']+', text or '', flags=re.I)


def risk_level(x):
    return 'CRITICAL' if x >= 85 else 'HIGH' if x >= 65 else 'MEDIUM' if x >= 35 else 'LOW'


def feature_signals(subject, body, sender=''):
    text = f'{subject}\n{body}'
    lower = text.lower()
    urls = []
    seen = set()
    for u in extract_urls(text):
        u = u.rstrip('.,);]')
        if u not in seen:
            urls.append(u); seen.add(u)

    reasons = []
    safe_reasons = []

    patterns = [
        ('Urgent or threatening language detected', r'\b(urgent|immediately|act now|final notice|expires?|within \d+ hours|suspend|locked|blocked|terminate|legal action)\b'),
        ('Requests for passwords or credentials detected', r'\b(password|passcode|otp|one[- ]time password|username|credentials|login details|security code)\b'),
        ('Account verification or login request detected', r'\b(verify|verification|confirm).{0,60}\b(account|identity|login|profile)\b|\b(sign in|log in|login)\b'),
        ('Financial or payment request detected', r'\b(payment|invoice|bank|wire|transfer|credit card|debit card|refund|money|cash)\b'),
        ('Prize or scam language detected', r'\b(congratulations|winner|prize|lottery|free money|claim your|you have won)\b'),
        ('Promotional or sales-heavy language detected', r'\b(offer|discount|sale|limited time|promotion|cheap|free|buy now|special deal|unsubscribe)\b'),
        ('Suspicious call-to-action language detected', r'\b(click here|verify now|download|open attachment|enable|reply immediately|call now)\b'),
    ]
    for label, pattern in patterns:
        if re.search(pattern, lower, re.I):
            reasons.append(label)

    if urls:
        reasons.append(f'{len(urls)} external URL(s) detected')
        for u in urls:
            try:
                p = urlparse(u)
                host = p.hostname or ''
                if p.scheme.lower() != 'https':
                    reasons.append('HTTP URL detected (not HTTPS)')
                    break
                if re.match(r'^\d{1,3}(?:\.\d{1,3}){3}$', host):
                    reasons.append('URL uses an IP-address host')
                    break
                if '@' in u or any(k in u.lower() for k in ['login', 'verify', 'secure', 'account', 'payment']):
                    reasons.append('URL contains a potentially sensitive-action pattern')
                    break
            except Exception:
                reasons.append('Invalid URL pattern detected')
                break

    letters = [c for c in text if c.isalpha()]
    if len(letters) >= 20 and sum(c.isupper() for c in letters) / len(letters) > 0.35:
        reasons.append('Excessive capital-letter usage detected')
    if len(re.findall(r'!{2,}|\?{2,}', text)) >= 2:
        reasons.append('Excessive punctuation detected')
    if re.search(r'\b(gift card|keep this confidential|do not tell|secret)\b', lower):
        reasons.append('Social-engineering language detected')

    if not urls:
        safe_reasons.append('No external URLs detected')
    if not any('promotional' in x.lower() or 'prize' in x.lower() for x in reasons):
        safe_reasons.append('No strong promotional/prize language detected')
    if not any('password' in x.lower() or 'credential' in x.lower() or 'account' in x.lower() for x in reasons):
        safe_reasons.append('No suspicious credential/account request detected')
    if not sender:
        safe_reasons.append('Sender information was not provided')

    return urls, reasons, safe_reasons


def model_explanations(text, classification):
    if MODEL is None:
        return []
    try:
        vectorizer = MODEL.named_steps.get('tfidf')
        clf = MODEL.named_steps.get('clf')
        if vectorizer is None or clf is None or not hasattr(clf, 'coef_'):
            return []
        x = vectorizer.transform([text])
        names = vectorizer.get_feature_names_out()
        contributions = x.multiply(clf.coef_[0])
        arr = contributions.toarray()[0]
        idxs = arr.argsort()[::-1] if classification == 'SPAM' else arr.argsort()
        out = []
        for i in idxs:
            if (classification == 'SPAM' and arr[i] <= 0) or (classification != 'SPAM' and arr[i] >= 0):
                break
            term = names[i]
            if len(term) >= 3 and term not in out:
                out.append(term)
            if len(out) >= 5:
                break
        return out
    except Exception:
        return []


def ham_domain_category(subject, body):
    text = f'{subject} {body}'.lower()
    categories = [
        ('Education', r'\b(class|course|lecture|student|teacher|professor|university|college|school|assignment|exam|education|academic|scholarship|admission)\b'),
        ('Work', r'\b(meeting|project|office|client|team|deadline|agenda|work|job|interview|colleague|manager|employee|report)\b'),
        ('Finance', r'\b(bank|statement|salary|account balance|transaction|tax|investment|loan|invoice|budget|finance)\b'),
        ('Personal', r'\b(family|friend|birthday|dinner|lunch|vacation|travel|personal|photos|weekend)\b'),
        ('Social', r'\b(event|community|club|social|party|invite|invitation|volunteer|networking)\b'),
        ('Promotion', r'\b(newsletter|catalog|announcement|offer|discount|sale|promotion|deal)\b'),
    ]
    for name, pattern in categories:
        if re.search(pattern, text, re.I):
            return name
    return 'General'


def sender_analysis(sender, prediction, signal_reasons):
    sender = clean_text(sender)
    if not sender:
        return {'sender': '', 'domain': '', 'score': 0, 'verification': 'Sender verification unavailable'}
    domain = sender.rsplit('@', 1)[-1].lower() if '@' in sender else ''
    score = 0
    indicators = []
    if '@' not in sender:
        score += 60; indicators.append('Sender does not contain a standard email address format')
    elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', sender):
        score += 45; indicators.append('Sender has an unusual email address format')
    if domain:
        if re.match(r'^\d', domain) or '.' not in domain:
            score += 35; indicators.append('Sender domain has an unusual structure')
        local = sender.split('@',1)[0].lower()
        if re.search(r'(noreply|no-reply|mailer|marketing|promo|support|admin)', local):
            indicators.append('Sender uses a role-based or automated mailbox pattern')
        if any(x in domain for x in ['verify','secure-login','account-alert','payment']):
            score += 35; indicators.append('Sender domain contains a sensitive-action keyword')
    if prediction == 'SPAM' and signal_reasons:
        score += min(25, len(signal_reasons) * 4)
    return {'sender': sender, 'domain': domain, 'score': round(min(100, score),1), 'verification': 'Domain reputation verification unavailable', 'indicators': indicators}


def analyze_email(e):
    subject = clean_text(e.get('subject'))
    body = clean_text(e.get('body'))
    sender = clean_text(e.get('sender'))
    recipient = clean_text(e.get('recipient'))
    text = f'Subject: {subject}\n\n{body}'.strip()
    if not text:
        raise ValueError('Email subject or body is required')

    urls, signal_reasons, safe_reasons = feature_signals(subject, body, sender)
    if MODEL is None:
        raise RuntimeError('Spam detection model is not available')

    probs = MODEL.predict_proba([text])[0]
    classes = list(MODEL.classes_)
    spam_idx = classes.index(1) if 1 in classes else int(probs.argmax())
    spam_risk = float(probs[spam_idx] * 100)
    prediction = 'SPAM' if spam_risk >= 50 else 'HAM'
    confidence = max(spam_risk, 100 - spam_risk)

    model_terms = model_explanations(text, prediction)
    reasons = list(dict.fromkeys(signal_reasons))
    sender_result = sender_analysis(sender, prediction, signal_reasons)
    if sender_result.get('indicators'):
        if prediction == 'SPAM':
            reasons.extend(sender_result['indicators'])
    if prediction == 'SPAM' and model_terms:
        reasons.append('Model-weighted spam indicators: ' + ', '.join(model_terms))
    if prediction == 'HAM':
        reasons = list(dict.fromkeys(safe_reasons))
        category = ham_domain_category(subject, body)
        if model_terms:
            reasons.append('Model-weighted safe indicators: ' + ', '.join(model_terms))
        if not reasons:
            reasons = ['No strong spam indicators were detected by the analysis pipeline']
    else:
        category = None
        if not reasons:
            reasons = ['Model probability indicates this message is more likely to be spam']

    url_risk = min(100, len(urls) * 25)
    context_risk = min(100, len(signal_reasons) * 12)
    overall_risk = round(0.75 * spam_risk + 0.15 * url_risk + 0.10 * context_risk, 1)
    overall_risk = min(100, max(0, overall_risk))

    return {
        'prediction': prediction,
        'classification': prediction,
        'spam_risk': round(spam_risk, 1),
        'confidence': round(confidence, 1),
        'overall_risk': overall_risk,
        'risk_level': risk_level(overall_risk),
        'domain_category': category,
        'reasons': list(dict.fromkeys(reasons)),
        'url_analysis': {
            'urls_detected': len(urls),
            'suspicious_urls': sum(1 for u in urls if re.search(r'@|\b(login|verify|secure|account|payment)\b', u, re.I) or not u.lower().startswith('https://')),
            'items': [{'url': u, 'domain': urlparse(u).hostname or '', 'https': urlparse(u).scheme.lower() == 'https'} for u in urls],
            'reputation': 'Reputation verification unavailable',
        },
        'context_analysis': {
            'score': round(context_risk, 1),
            'level': risk_level(context_risk),
            'indicators': signal_reasons,
        },
        'sender_analysis': sender_result,
        'explanation': ''
    }


def row_email(i):
    r = _dataset.iloc[i]
    return {k: clean_text(r[k]) for k in ['sender', 'recipient', 'subject', 'body', 'urls']} | {'dataset_label': None if pd.isna(r['label']) else int(r['label'])}


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)


@app.get('/api/status')
def status():
    labels = _dataset['label'].value_counts(dropna=True).to_dict() if _dataset_loaded else {}
    return jsonify({'dataset_loaded': _dataset_loaded, 'dataset_count': len(_dataset), 'label_counts': labels, 'model_loaded': MODEL is not None})


@app.get('/api/email/<int:i>')
def get_email(i):
    if not _dataset_loaded or i < 0 or i >= len(_dataset):
        return jsonify({'error': 'Dataset index out of range'}), 404
    return jsonify({'index': i, 'total': len(_dataset), 'email': row_email(i)})


@app.post('/api/analyze')
def analyze():
    e = request.get_json(force=True) or {}
    try:
        result = analyze_email(e)
    except (ValueError, RuntimeError) as exc:
        return jsonify({'error': str(exc)}), 400
    aid = str(uuid.uuid4()); now = datetime.now(timezone.utc).isoformat()
    c = db()
    c.execute('INSERT INTO analyses VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (
        aid, e.get('sender',''), e.get('recipient',''), e.get('subject',''), e.get('body',''),
        result['prediction'], result['spam_risk'], result['confidence'], result['overall_risk'],
        json.dumps(result['reasons']), json.dumps(result), now))
    c.commit(); c.close()
    return jsonify({'id': aid, 'created_at': now, 'result': result})


@app.get('/api/history')
def history():
    c = db(); rows = [dict(r) for r in c.execute('SELECT * FROM analyses ORDER BY created_at DESC').fetchall()]; c.close()
    for r in rows:
        r['reasons'] = json.loads(r['reasons'])
        r['features'] = json.loads(r['features'])
    return jsonify(rows)


@app.delete('/api/history/<aid>')
def delete_history(aid):
    c = db(); c.execute('DELETE FROM analyses WHERE id=?', (aid,)); c.commit(); c.close(); return jsonify({'ok': True})


@app.get('/api/dashboard')
def dashboard():
    c = db(); rows = [dict(r) for r in c.execute('SELECT * FROM analyses ORDER BY created_at DESC').fetchall()]; c.close()
    spam = sum(r['classification'] == 'SPAM' for r in rows)
    domains = {}
    for r in rows:
        sender = clean_text(r.get('sender'))
        domain = sender.rsplit('@', 1)[-1].lower() if '@' in sender else sender or 'Unknown sender'
        if domain not in domains:
            domains[domain] = {'domain': domain, 'spam': 0, 'ham': 0}
        if r['classification'] == 'SPAM': domains[domain]['spam'] += 1
        else: domains[domain]['ham'] += 1
    domain_list = sorted(domains.values(), key=lambda x: x['spam'] + x['ham'], reverse=True)
    return jsonify({'total': len(rows), 'spam': spam, 'not_spam': len(rows)-spam, 'domains': domain_list})


@app.post('/api/dataset-upload')
def dataset_upload():
    f = request.files.get('file')
    if not f: return jsonify({'error': 'No dataset uploaded'}), 400
    path = os.path.join(ROOT, 'data', 'uploaded_dataset.csv')
    f.save(path); load_dataset(path)
    return jsonify({'ok': True, 'count': len(_dataset)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
