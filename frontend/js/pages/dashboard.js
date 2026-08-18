/**
 * ════════════════════════════════════════════════════════════════
 * DASHBOARD PAGE
 * ════════════════════════════════════════════════════════════════
 * 
 * Displays:
 * - Summary statistics (total, spam, ham)
 * - Sender analysis cards
 * - Interactive sender visualization modal with bar chart
 */

/**
 * ════════════════════════════════════════════════════════════════
 * MODEL METRICS & STATE
 * ════════════════════════════════════════════════════════════════
 */

// Trained model performance metrics
const MODEL_METRICS = {
  precision: 96.59,
  recall: 96.97,
  accuracy: 97.12,
  f1: 96.78
};

// Current sender modal state
let senderModal = null;

/**
 * ════════════════════════════════════════════════════════════════
 * DASHBOARD PAGE RENDER
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Render the dashboard page with stats and sender cards
 * @returns {string} - HTML content for the dashboard page
 */
function dashboard() {
  const dashData = state.dash || {
    total: 0,
    spam: 0,
    not_spam: 0,
    domains: []
  };

  // Summary statistics
  const stats = [
    ['Total Emails Analysed', dashData.total],
    ['Spam Emails', dashData.spam],
    ['HAM Emails', dashData.not_spam]
  ];

  const statCards = stats
    .map(([label, value]) => `
      <div class="card stat">
        <div class="muted">${label}</div>
        <strong>${value}</strong>
      </div>
    `)
    .join('');

  // Sender cards
  const senderCardsHTML = (dashData.domains || []).length
    ? dashData.domains.map((domain, index) => senderCard(domain, index)).join('')
    : '<div class="card empty">No sender/domain analysis data yet.</div>';

  return `
    <div class="wrap">
      <div class="page-title">
        <div>
          <h2>Dashboard</h2>
        </div>
      </div>

      <!-- Summary Statistics -->
      <div class="stats three-stats">
        ${statCards}
      </div>

      <!-- Sender Analysis Section -->
      <section class="sender-analysis-section">
        <div class="section-label">Sender Analysis</div>
        <div class="sender-grid">
          ${senderCardsHTML}
        </div>
      </section>
    </div>
  `;
}

/**
 * ════════════════════════════════════════════════════════════════
 * SENDER CARDS
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Generate HTML for a sender domain card
 * @param {Object} domain - Domain data object
 * @param {number} index - Card index
 * @returns {string} - HTML for sender card
 */
function senderCard(domain, index) {
  const totalEmails = domain.spam + domain.ham;

  return `
    <div class="card sender-card">
      <div class="sender-card-head">
        <div>
          <h3>${esc(domain.domain)}</h3>
          <div class="muted">Total Emails: ${totalEmails}</div>
        </div>
        <button class="visualise-btn" type="button" onclick="visualiseSender(${index})">
          Visualise
        </button>
      </div>
      <div class="sender-counts">
        <span><b class="spam">Spam</b> ${domain.spam}</span>
        <span><b class="ham">HAM</b> ${domain.ham}</span>
      </div>
    </div>
  `;
}

/**
 * ════════════════════════════════════════════════════════════════
 * SENDER MODAL & VISUALIZATION
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Open visualization modal for a sender domain
 * @param {number} index - Domain index in dashboard data
 */
function visualiseSender(index) {
  const dashData = state.dash || {};
  const domain = (dashData.domains || [])[index];

  if (!domain) return;

  openSenderModal(domain);
}

/**
 * Open the sender visualization modal
 * @param {Object} domain - Domain data object
 */
function openSenderModal(domain) {
  senderModal = { x: domain };
  renderModal();
}

/**
 * Close the sender visualization modal
 */
function closeSenderModal() {
  senderModal = null;
  renderModal();
}

/**
 * ════════════════════════════════════════════════════════════════
 * CHART RENDERING
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Render the sender modal with SVG bar chart
 * Creates an interactive bar chart showing spam vs ham email distribution
 */
function renderModal() {
  // Remove existing modal if present
  const oldModal = document.getElementById('senderModal');
  if (oldModal) oldModal.remove();

  // Exit early if no modal is open
  if (!senderModal) return;

  const domain = senderModal.x;
  const spam = Number(domain.spam) || 0;
  const ham = Number(domain.ham) || 0;
  const total = spam + ham;

  // Calculate percentages
  const spamPct = total ? (spam / total) * 100 : 0;
  const hamPct = total ? (ham / total) * 100 : 0;

  // Chart dimensions and positioning
  const chartW = 460;
  const chartH = 250;
  const left = 58;
  const right = 18;
  const top = 24;
  const bottom = 52;

  const plotW = chartW - left - right;
  const plotH = chartH - top - bottom;
  const barW = 90;
  const gap = 85;

  // Bar positions
  const spamX = left + (plotW - (barW * 2 + gap)) / 2;
  const hamX = spamX + barW + gap;

  // Y-axis calculator
  const maxValue = Math.max(spam, ham, 1);
  const y = (value) => top + plotH - (value / maxValue) * plotH;

  // Generate grid lines and axis labels
  const ticks = [0, 0.25, 0.5, 0.75, 1].map(ratio => Math.round(maxValue * ratio));
  const grid = ticks
    .map(value => {
      const yy = y(value);
      return `
        <line x1="${left}" y1="${yy}" x2="${chartW - right}" y2="${yy}" class="sender-chart-grid-line"/>
        <text x="${left - 9}" y="${yy + 4}" text-anchor="end" class="sender-chart-axis-text">${value}</text>
      `;
    })
    .join('');

  // Calculate bar heights
  const spamHeight = (spam / maxValue) * plotH;
  const hamHeight = (ham / maxValue) * plotH;

  // Create modal element
  const modal = document.createElement('div');
  modal.id = 'senderModal';
  modal.className = 'modal-backdrop';
  modal.innerHTML = `
    <div class="modal-card sender-viz-modal" role="dialog" aria-modal="true" aria-label="Sender visualization">
      <button class="modal-close" onclick="closeSenderModal()" aria-label="Close">×</button>
      
      <div class="eyebrow">Sender Analysis</div>
      <h3>Sender: ${esc(domain.domain)}</h3>
      <div class="modal-title">Spam vs Ham</div>

      <!-- SVG Bar Chart -->
      <div class="sender-bar-chart-wrap">
        <svg 
          class="sender-bar-chart" 
          viewBox="0 0 ${chartW} ${chartH}" 
          role="img" 
          aria-label="Bar graph for ${esc(domain.domain)} showing ${spam} spam emails and ${ham} HAM emails"
        >
          <!-- Grid lines -->
          ${grid}

          <!-- Axis lines -->
          <line x1="${left}" y1="${top + plotH}" x2="${chartW - right}" y2="${top + plotH}" class="sender-chart-axis-line"/>
          <line x1="${left}" y1="${top}" x2="${left}" y2="${top + plotH}" class="sender-chart-axis-line"/>

          <!-- Bars -->
          <rect 
            x="${spamX}" 
            y="${y(spam)}" 
            width="${barW}" 
            height="${spamHeight}" 
            rx="7" 
            class="sender-bar-spam"
          />
          <rect 
            x="${hamX}" 
            y="${y(ham)}" 
            width="${barW}" 
            height="${hamHeight}" 
            rx="7" 
            class="sender-bar-ham"
          />

          <!-- Value labels on bars -->
          <text 
            x="${spamX + barW / 2}" 
            y="${Math.max(top + 15, y(spam) - 8)}" 
            text-anchor="middle" 
            class="sender-chart-value"
          >${spam}</text>
          <text 
            x="${hamX + barW / 2}" 
            y="${Math.max(top + 15, y(ham) - 8)}" 
            text-anchor="middle" 
            class="sender-chart-value"
          >${ham}</text>

          <!-- Bar labels -->
          <text 
            x="${spamX + barW / 2}" 
            y="${chartH - 25}" 
            text-anchor="middle" 
            class="sender-chart-label"
          >Spam</text>
          <text 
            x="${hamX + barW / 2}" 
            y="${chartH - 25}" 
            text-anchor="middle" 
            class="sender-chart-label"
          >HAM</text>

          <!-- Axis titles -->
          <text 
            x="18" 
            y="${top + plotH / 2}" 
            text-anchor="middle" 
            transform="rotate(-90 18 ${top + plotH / 2})" 
            class="sender-chart-axis-title"
          >Email Count</text>
          <text 
            x="${chartW / 2}" 
            y="${chartH - 4}" 
            text-anchor="middle" 
            class="sender-chart-axis-title"
          >Classification</text>
        </svg>
      </div>

      <!-- Statistics -->
      <div class="sender-percentages">
        <div>
          <span class="spam">Spam Percentage</span>
          <strong>${spamPct.toFixed(2)}%</strong>
        </div>
        <div>
          <span class="ham">Ham Percentage</span>
          <strong>${hamPct.toFixed(2)}%</strong>
        </div>
      </div>
    </div>
  `;

  // Close modal when clicking backdrop
  modal.addEventListener('click', (event) => {
    if (event.target === modal) closeSenderModal();
  });

  // Append modal to body
  document.body.appendChild(modal);
}
