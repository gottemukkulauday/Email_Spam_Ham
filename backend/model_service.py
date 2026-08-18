"""
════════════════════════════════════════════════════════════════
MACHINE LEARNING MODEL LOADING & PREDICTION EXPLANATIONS
════════════════════════════════════════════════════════════════

Handles loading the pre-trained spam detection pipeline and
extracting top model-weighted terms for explainability.
"""

import os

import joblib

from config import MODEL_PATH


# ════════════════════════════════════════════════════════════════
# MODEL INITIALIZATION
# ════════════════════════════════════════════════════════════════

# Loaded once at startup; None when the model file is missing
MODEL = (
    joblib.load(MODEL_PATH)
    if os.path.exists(MODEL_PATH)
    else None
)


# ════════════════════════════════════════════════════════════════
# PREDICTION EXPLANATIONS
# ════════════════════════════════════════════════════════════════

def model_explanations(text, classification):
    """
    Extract the top model-weighted terms that pushed the prediction.
    
    Uses the TF-IDF vectorizer and classifier coefficients to identify
    which words contributed most to the classification decision.
    
    Args:
        text (str): Email text (subject + body combined)
        classification (str): 'SPAM' or 'HAM'
        
    Returns:
        list: Top 5 feature terms that contributed to prediction,
              or empty list if model unavailable or error occurs
    """
    if MODEL is None:
        return []

    try:
        # Extract pipeline components
        vectorizer = MODEL.named_steps.get('tfidf')
        classifier = MODEL.named_steps.get('clf')

        # Validate components
        if (vectorizer is None or classifier is None or
            not hasattr(classifier, 'coef_')):
            return []

        # Vectorize the text
        x_vect = vectorizer.transform([text])

        # Get feature names
        feature_names = vectorizer.get_feature_names_out()

        # Calculate contributions (TF-IDF weight × classifier coefficient)
        contributions = x_vect.multiply(classifier.coef_[0])
        scores = contributions.toarray()[0]

        # Sort indices by contribution (highest first for SPAM, lowest for HAM)
        if classification == 'SPAM':
            indices = scores.argsort()[::-1]
        else:
            indices = scores.argsort()

        # Extract top terms
        top_terms = []
        for i in indices:
            # Skip terms that oppose the classification
            if (classification == 'SPAM' and scores[i] <= 0) or \
               (classification != 'SPAM' and scores[i] >= 0):
                break

            term = feature_names[i]

            # Filter by minimum length and duplicates
            if len(term) >= 3 and term not in top_terms:
                top_terms.append(term)

            # Limit to top 5 terms
            if len(top_terms) >= 5:
                break

        return top_terms

    except Exception:
        # Gracefully handle any errors during explanation extraction
        return []
