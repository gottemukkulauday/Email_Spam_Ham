/**
 * ════════════════════════════════════════════════════════════════
 * HOME PAGE
 * ════════════════════════════════════════════════════════════════
 * 
 * Displays:
 * - Hero section with project overview
 * - Feature cards
 * - How-it-works steps
 * - Model performance metrics
 */

/**
 * Render the home page
 * @returns {string} - HTML content for the home page
 */
function about() {
  // Feature cards data
  const features = [
    ['URL Analysis'],
    ['Context Analysis'],
    ['Sender Analysis'],
    ['Risk Assessment']
  ];

  // How-it-works steps
  const steps = [
    'Type Email',
    'Analyze',
    'Explain Signals',
    'View Results'
  ];

  // Model performance metrics
  const metrics = [
    ['Precision', 96.59],
    ['Recall', 96.97],
    ['Accuracy', 97.12],
    ['F1 Score', 96.78]
  ];

  // Feature cards HTML
  const featureCards = features
    .map(feature => `
      <div class="card">
        <h3>${feature[0]}</h3>
        <div class="muted">Explainable signals for every message.</div>
      </div>
    `)
    .join('');

  // Steps HTML
  const stepsHTML = steps
    .map((step, index) => `
      <div class="step">
        <b>${index + 1}</b>
        <div style="margin-top: 8px;">${step}</div>
      </div>
    `)
    .join('');

  // Performance metrics HTML
  const metricsHTML = metrics
    .map(([label, value]) => `
      <div class="card performance-card home-metric">
        <div class="performance-label">${label}</div>
        <div class="performance-value">${value.toFixed(2)}%</div>
      </div>
    `)
    .join('');

  // Combine all sections
  return `
    <div class="wrap">
      <!-- Hero Section -->
      <section class="hero">
        <h1>Email Spam Detection</h1>
        <p>Detect spam, phishing, and suspicious emails using intelligent AI-powered analysis.</p>
      </section>

      <!-- Feature Cards -->
      <div class="grid4">
        ${featureCards}
      </div>

      <!-- How It Works -->
      <div class="card" style="margin-top: 20px;">
        <h3>How it works</h3>
        <div class="steps">
          ${stepsHTML}
        </div>
      </div>

      <!-- Model Performance Section -->
      <section class="home-performance">
        <div class="section-label">Model Performance</div>
        <div class="home-metrics">
          ${metricsHTML}
        </div>
      </section>
    </div>
  `;
}
