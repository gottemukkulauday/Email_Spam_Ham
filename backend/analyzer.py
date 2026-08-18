"""
════════════════════════════════════════════════════════════════
CORE SPAM ANALYSIS ORCHESTRATION
════════════════════════════════════════════════════════════════

Combines the ML model with rule-based signals into a single result
payload used by the /api/analyze endpoint. This module orchestrates
predictions, scoring, and explainable reasoning.
"""

import re
from urllib.parse import urlparse

from dataset import clean_text
from features import (
    feature_signals,
    sender_analysis,
    ham_domain_category,
    risk_level
)
from model_service import MODEL, model_explanations


# ════════════════════════════════════════════════════════════════
# MAIN ANALYSIS FUNCTION
# ════════════════════════════════════════════════════════════════

def analyze_email(e):
    """
    Analyze one email dictionary and return the full result payload.
    
    Args:
        e (dict): Email data with keys: subject, body, sender, recipient
        
    Returns:
        dict: Complete analysis result with prediction, risk scores, and explanations
        
    Raises:
        ValueError: If email subject or body is missing
        RuntimeError: If spam detection model is not loaded
    """
    # Extract and clean email fields
    subject = clean_text(e.get('subject'))
    body = clean_text(e.get('body'))
    sender = clean_text(e.get('sender'))
    recipient = clean_text(e.get('recipient'))
    text = f'Subject: {subject}\n\n{body}'.strip()

    # Validate input
    if not text:
        raise ValueError('Email subject or body is required')

    # ════════════════════════════════════════════════════════════
    # FEATURE SIGNAL EXTRACTION
    # ════════════════════════════════════════════════════════════
    urls, signal_reasons, safe_reasons = feature_signals(subject, body, sender)

    # Ensure model is available
    if MODEL is None:
        raise RuntimeError('Spam detection model is not available')

    # ════════════════════════════════════════════════════════════
    # ML MODEL PREDICTION
    # ════════════════════════════════════════════════════════════
    probs = MODEL.predict_proba([text])[0]
    classes = list(MODEL.classes_)
    spam_idx = classes.index(1) if 1 in classes else int(probs.argmax())
    spam_risk = float(probs[spam_idx] * 100)
    prediction = 'SPAM' if spam_risk >= 50 else 'HAM'
    confidence = max(spam_risk, 100 - spam_risk)

    # ════════════════════════════════════════════════════════════
    # REASONING & EXPLANATIONS
    # ════════════════════════════════════════════════════════════
    model_terms = model_explanations(text, prediction)
    reasons = list(dict.fromkeys(signal_reasons))
    sender_result = sender_analysis(sender, prediction, signal_reasons)

    # Build reasons based on prediction type
    if sender_result.get('indicators'):
        if prediction == 'SPAM':
            reasons.extend(sender_result['indicators'])

    if prediction == 'SPAM' and model_terms:
        reasons.append('Model-weighted spam indicators: ' + ', '.join(model_terms))

    if prediction == 'HAM':
        # HAM email explanations
        reasons = list(dict.fromkeys(safe_reasons))
        category = ham_domain_category(subject, body)
        if model_terms:
            reasons.append('Model-weighted safe indicators: ' + ', '.join(model_terms))
        if not reasons:
            reasons = ['No strong spam indicators were detected by the analysis pipeline']
    else:
        # SPAM email explanations
        category = None
        if not reasons:
            reasons = ['Model probability indicates this message is more likely to be spam']

    # ════════════════════════════════════════════════════════════
    # RISK SCORING
    # ════════════════════════════════════════════════════════════
    url_risk = min(100, len(urls) * 25)
    context_risk = min(100, len(signal_reasons) * 12)
    overall_risk = round(0.75 * spam_risk + 0.15 * url_risk + 0.10 * context_risk, 1)
    overall_risk = min(100, max(0, overall_risk))

    # ════════════════════════════════════════════════════════════
    # RESULT CONSTRUCTION
    # ════════════════════════════════════════════════════════════
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
            'suspicious_urls': sum(
                1 for u in urls
                if re.search(r'@|\b(login|verify|secure|account|payment)\b', u, re.I)
                or not u.lower().startswith('https://')
            ),
            'items': [
                {
                    'url': u,
                    'domain': urlparse(u).hostname or '',
                    'https': urlparse(u).scheme.lower() == 'https'
                }
                for u in urls
            ],
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
