/**
 * ════════════════════════════════════════════════════════════════
 * DETECTION PAGE
 * ════════════════════════════════════════════════════════════════
 * 
 * Displays:
 * - Email input form (sender, subject, body)
 * - Analysis results with predictions
 * - Risk assessment and explanations
 */

/**
 * ════════════════════════════════════════════════════════════════
 * DETECTION PAGE RENDER
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Render the detection page with input form and results
 * @returns {string} - HTML content for the detection page
 */
function detection() {
  const email = state.email || {};

  return `
    <div class="wrap">
      <div class="page-title">
        <div>
          <h2>Analyze Email</h2>
        </div>
      </div>

      <div class="detect-grid">
        <!-- Email Input Form -->
        <section class="panel">
          <div class="panel-head">
            <h3>Email Input</h3>
            <button class="secondary clear-btn" onclick="clearEmail()">Clear</button>
          </div>

          <div class="input-field">
            <label class="muted">Sender</label>
            <input id="sender" placeholder="Enter sender email" value="${esc(email.sender)}">
          </div>

          <div class="input-field body-field">
            <label class="muted">Email Subject</label>
            <input id="subject" placeholder="Enter email subject" value="${esc(email.subject)}">
          </div>

          <div class="input-field body-field">
            <label class="muted">Email Body</label>
            <textarea id="body" placeholder="Paste or type the email body here...">${esc(email.body)}</textarea>
          </div>

          <button class="detect" type="button" onclick="detect()">ANALYZE EMAIL</button>
        </section>

        <!-- Analysis Results -->
        <section class="panel">
          ${state.result ? resultView() : `
            <div class="ready">
              <div>
                <div style="font-size: 50px;">◎</div>
                <h3>Ready to Analyze</h3>
                <p>Enter an email subject and body to begin analysis.</p>
              </div>
            </div>
          `}
        </section>
      </div>
    </div>
  `;
}

/**
 * ════════════════════════════════════════════════════════════════
 * RESULT DISPLAY
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Render the analysis results
 * @returns {string} - HTML for results display
 */
function resultView() {
  const result = state.result;
  const isHam = result.prediction === 'HAM';

  if (isHam) {
    return `
      <div class="result-top">
        <div>
          <div class="eyebrow">Detection Result</div>
          <div class="badge ham">HAM</div>
          <div class="muted" style="margin-top: 6px;">Not Spam</div>
          <div class="risk" style="margin-top: 14px;">Domain: ${esc(result.domain_category)}</div>
        </div>
      </div>
      <div class="card" style="margin-top: 14px;">
        <h3>Why is this not spam?</h3>
        ${result.reasons.map(reason => `
          <div class="pill" style="display: block; margin: 8px 0;">
            ${esc(reason)}
          </div>
        `).join('')}
      </div>
    `;
  }

  // SPAM result
  return `
    <div class="result-top">
      <div>
        <div class="eyebrow">Detection Result</div>
        <div class="badge spam">SPAM</div>
      </div>
      <div class="confidence">
        <strong>${result.spam_risk}%</strong>
      </div>
    </div>

    <div class="risk-level" style="margin-top: 10px;">
      <b>Risk Level: ${esc(result.risk_level)}</b>
    </div>

    <div class="card" style="margin-top: 14px;">
      <h3>Why is this spam?</h3>
      ${result.reasons.map(reason => `
        <div class="pill" style="display: block; margin: 8px 0;">
          ${esc(reason)}
        </div>
      `).join('')}
    </div>

    <div class="analysis-grid" style="margin-top: 14px;">
      ${score('URL Analysis', '', result.url_analysis.suspicious_urls ? 
        Math.min(100, result.url_analysis.suspicious_urls / result.url_analysis.urls_detected * 100) : 0)}
      ${score('Context Analysis', '', result.context_analysis.score)}
      ${senderMetric(result.sender_analysis)}
    </div>
  `;
}

/**
 * ════════════════════════════════════════════════════════════════
 * METRIC CARDS
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Generate sender analysis metric card
 * @param {Object} sender - Sender analysis data
 * @returns {string} - HTML for sender metric
 */
function senderMetric(sender) {
  const label = sender.domain ? sender.domain : 'Sender';
  const score = Math.min(100, Math.max(0, sender.score || 0));

  return `
    <div class="card metric">
      <h4>Sender Analysis</h4>
      <div class="muted">${esc(label)}</div>
      <div class="num">${score}%</div>
      <div class="bar">
        <i style="width: ${score}%;"></i>
      </div>
      ${sender.indicators?.length ? `
        <div class="muted">${esc(sender.indicators[0])}</div>
      ` : `
        <div class="muted">Sender indicators based on available information.</div>
      `}
    </div>
  `;
}

/**
 * Generate score metric card
 * @param {string} title - Metric title
 * @param {string} icon - Icon (unused in current version)
 * @param {number} value - Score percentage value
 * @returns {string} - HTML for score card
 */
function score(title, icon, value) {
  return `
    <div class="card metric">
      <h4>${title}</h4>
      <div class="num">${Number(value).toFixed(0)}%</div>
      <div class="bar">
        <i style="width: ${Math.min(100, value)}%;"></i>
      </div>
    </div>
  `;
}

/**
 * ════════════════════════════════════════════════════════════════
 * ANALYSIS ACTIONS
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Analyze the email entered in the form
 */
async function detect() {
  const email = {
    sender: document.getElementById('sender').value,
    recipient: '',
    subject: document.getElementById('subject').value,
    body: document.getElementById('body').value
  };

  // Validate input
  if (!email.sender.trim() && !email.subject.trim() && !email.body.trim()) {
    toast('Enter email information first');
    return;
  }

  try {
    // Send analysis request to backend
    const response = await api('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(email)
    });

    // Update state with results
    state.email = email;
    state.result = response.result;
    toast('Detection saved to History and Dashboard');

    // Render updated page
    await render();
  } catch (error) {
    toast(error.message);
  }
}

/**
 * Clear the email form and results
 */
function clearEmail() {
  state.email = { sender: '', recipient: '', subject: '', body: '' };
  state.result = null;
  render();
}
