"""
════════════════════════════════════════════════════════════════
EMAIL FEATURE SIGNALS FOR EXPLAINABLE ANALYSIS
════════════════════════════════════════════════════════════════

Hand-crafted rule-based heuristics (URLs, language patterns, sender shape)
that complement the ML model and feed the human-readable reasons shown
to the user.
"""

import re
from urllib.parse import urlparse

from dataset import clean_text


# ════════════════════════════════════════════════════════════════
# URL EXTRACTION
# ════════════════════════════════════════════════════════════════

def extract_urls(text):
    """
    Extract all http(s) URLs from the text.
    
    Args:
        text (str): Email subject or body text
        
    Returns:
        list: URLs found in text
    """
    return re.findall(
        r'https?://[^\s<>"\']+',
        text or '',
        flags=re.I
    )


# ════════════════════════════════════════════════════════════════
# RISK LEVEL CLASSIFICATION
# ════════════════════════════════════════════════════════════════

def risk_level(score):
    """
    Map a 0-100 score to a risk level label.
    
    Args:
        score (float): Risk score from 0 to 100
        
    Returns:
        str: Risk level ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')
    """
    if score >= 85:
        return 'CRITICAL'
    elif score >= 65:
        return 'HIGH'
    elif score >= 35:
        return 'MEDIUM'
    else:
        return 'LOW'


# ════════════════════════════════════════════════════════════════
# FEATURE SIGNAL DETECTION
# ════════════════════════════════════════════════════════════════

def feature_signals(subject, body, sender=''):
    """
    Inspect an email and return rule-based warning and safe signals.
    
    Args:
        subject (str): Email subject
        body (str): Email body
        sender (str): Sender email address (optional)
        
    Returns:
        tuple: (urls, warning_reasons, safe_reasons)
            - urls: List of URLs found
            - warning_reasons: List of spam-suspicious signals
            - safe_reasons: List of ham-supporting signals
    """
    text = f'{subject}\n{body}'
    lower = text.lower()
    urls = []
    seen = set()

    # ════════════════════════════════════════════════════════════
    # EXTRACT & DEDUPLICATE URLs
    # ════════════════════════════════════════════════════════════
    for url in extract_urls(text):
        # Remove trailing punctuation
        url = url.rstrip('.,);]')
        if url not in seen:
            urls.append(url)
            seen.add(url)

    reasons = []
    safe_reasons = []

    # ════════════════════════════════════════════════════════════
    # LANGUAGE & PATTERN ANALYSIS
    # ════════════════════════════════════════════════════════════

    # Define suspicious patterns
    patterns = [
        ('Urgent or threatening language detected',
         r'\b(urgent|immediately|act now|final notice|expires?|within \d+ hours|suspend|locked|blocked|terminate|legal action)\b'),

        ('Requests for passwords or credentials detected',
         r'\b(password|passcode|otp|one[- ]time password|username|credentials|login details|security code)\b'),

        ('Account verification or login request detected',
         r'\b(verify|verification|confirm).{0,60}\b(account|identity|login|profile)\b|\b(sign in|log in|login)\b'),

        ('Financial or payment request detected',
         r'\b(payment|invoice|bank|wire|transfer|credit card|debit card|refund|money|cash)\b'),

        ('Prize or scam language detected',
         r'\b(congratulations|winner|prize|lottery|free money|claim your|you have won)\b'),

        ('Promotional or sales-heavy language detected',
         r'\b(offer|discount|sale|limited time|promotion|cheap|free|buy now|special deal|unsubscribe)\b'),

        ('Suspicious call-to-action language detected',
         r'\b(click here|verify now|download|open attachment|enable|reply immediately|call now)\b'),
    ]

    for label, pattern in patterns:
        if re.search(pattern, lower, re.I):
            reasons.append(label)

    # ════════════════════════════════════════════════════════════
    # URL ANALYSIS
    # ════════════════════════════════════════════════════════════
    if urls:
        reasons.append(f'{len(urls)} external URL(s) detected')

        for url in urls:
            try:
                parsed = urlparse(url)
                host = parsed.hostname or ''

                # Check for non-HTTPS
                if parsed.scheme.lower() != 'https':
                    reasons.append('HTTP URL detected (not HTTPS)')
                    break

                # Check for IP address host
                if re.match(r'^\d{1,3}(?:\.\d{1,3}){3}$', host):
                    reasons.append('URL uses an IP-address host')
                    break

                # Check for sensitive action patterns
                if ('@' in url or
                    any(k in url.lower() for k in
                        ['login', 'verify', 'secure', 'account', 'payment'])):
                    reasons.append('URL contains a potentially sensitive-action pattern')
                    break

            except Exception:
                reasons.append('Invalid URL pattern detected')
                break

    # ════════════════════════════════════════════════════════════
    # TEXT FORMATTING ANALYSIS
    # ════════════════════════════════════════════════════════════
    letters = [c for c in text if c.isalpha()]
    if len(letters) >= 20 and sum(c.isupper() for c in letters) / len(letters) > 0.35:
        reasons.append('Excessive capital-letter usage detected')

    if len(re.findall(r'!{2,}|\?{2,}', text)) >= 2:
        reasons.append('Excessive punctuation detected')

    if re.search(r'\b(gift card|keep this confidential|do not tell|secret)\b', lower):
        reasons.append('Social-engineering language detected')

    # ════════════════════════════════════════════════════════════
    # SAFE EMAIL INDICATORS
    # ════════════════════════════════════════════════════════════
    if not urls:
        safe_reasons.append('No external URLs detected')

    if not any('promotional' in x.lower() or 'prize' in x.lower() for x in reasons):
        safe_reasons.append('No strong promotional/prize language detected')

    if not any('password' in x.lower() or 'credential' in x.lower() or
               'account' in x.lower() for x in reasons):
        safe_reasons.append('No suspicious credential/account request detected')

    if not sender:
        safe_reasons.append('Sender information was not provided')

    return urls, reasons, safe_reasons


# ════════════════════════════════════════════════════════════════
# HAM EMAIL CATEGORIZATION
# ════════════════════════════════════════════════════════════════

def ham_domain_category(subject, body):
    """
    Guess the domain (Education, Work, Finance, etc.) of a HAM email.
    
    Args:
        subject (str): Email subject
        body (str): Email body
        
    Returns:
        str: Category name or 'General' if no match
    """
    text = f'{subject} {body}'.lower()

    categories = [
        ('Education',
         r'\b(class|course|lecture|student|teacher|professor|university|college|school|assignment|exam|education|academic|scholarship|admission)\b'),

        ('Work',
         r'\b(meeting|project|office|client|team|deadline|agenda|work|job|interview|colleague|manager|employee|report)\b'),

        ('Finance',
         r'\b(bank|statement|salary|account balance|transaction|tax|investment|loan|invoice|budget|finance)\b'),

        ('Personal',
         r'\b(family|friend|birthday|dinner|lunch|vacation|travel|personal|photos|weekend)\b'),

        ('Social',
         r'\b(event|community|club|social|party|invite|invitation|volunteer|networking)\b'),

        ('Promotion',
         r'\b(newsletter|catalog|announcement|offer|discount|sale|promotion|deal)\b'),
    ]

    for name, pattern in categories:
        if re.search(pattern, text, re.I):
            return name

    return 'General'


# ════════════════════════════════════════════════════════════════
# SENDER ANALYSIS
# ════════════════════════════════════════════════════════════════

def sender_analysis(sender, prediction, signal_reasons):
    """
    Score the sender address and collect explainable indicators.
    
    Args:
        sender (str): Sender email address
        prediction (str): 'SPAM' or 'HAM'
        signal_reasons (list): List of detected signal reasons
        
    Returns:
        dict: Sender analysis with score and indicators
    """
    sender = clean_text(sender)

    if not sender:
        return {
            'sender': '',
            'domain': '',
            'score': 0,
            'verification': 'Sender verification unavailable'
        }

    # Extract domain from sender email
    domain = (
        sender.rsplit('@', 1)[-1].lower()
        if '@' in sender
        else ''
    )

    score = 0
    indicators = []

    # ════════════════════════════════════════════════════════════
    # EMAIL ADDRESS FORMAT CHECKS
    # ════════════════════════════════════════════════════════════
    if '@' not in sender:
        score += 60
        indicators.append('Sender does not contain a standard email address format')
    elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', sender):
        score += 45
        indicators.append('Sender has an unusual email address format')

    # ════════════════════════════════════════════════════════════
    # DOMAIN CHECKS
    # ════════════════════════════════════════════════════════════
    if domain:
        if re.match(r'^\d', domain) or '.' not in domain:
            score += 35
            indicators.append('Sender domain has an unusual structure')

        local = sender.split('@', 1)[0].lower()
        if re.search(r'(noreply|no-reply|mailer|marketing|promo|support|admin)', local):
            indicators.append('Sender uses a role-based or automated mailbox pattern')

        if any(x in domain for x in
               ['verify', 'secure-login', 'account-alert', 'payment']):
            score += 35
            indicators.append('Sender domain contains a sensitive-action keyword')

    # ════════════════════════════════════════════════════════════
    # CONTEXTUAL SCORING
    # ════════════════════════════════════════════════════════════
    if prediction == 'SPAM' and signal_reasons:
        score += min(25, len(signal_reasons) * 4)

    return {
        'sender': sender,
        'domain': domain,
        'score': round(min(100, score), 1),
        'verification': 'Domain reputation verification unavailable',
        'indicators': indicators
    }
