/**
 * ════════════════════════════════════════════════════════════════
 * HISTORY PAGE
 * ════════════════════════════════════════════════════════════════
 * 
 * Displays:
 * - Audit trail of all email detections
 * - Search and filter functionality
 * - View and delete individual records
 */

/**
 * ════════════════════════════════════════════════════════════════
 * HISTORY PAGE RENDER
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Render the history page with audit trail table
 * @returns {string} - HTML content for the history page
 */
async function history() {
  // Fetch detection history from backend
  state.history = await api('/api/history');

  return `
    <div class="wrap">
      <div class="page-title">
        <div>
          
          <h2>History</h2>
        </div>
      </div>

      <!-- Search & Filter Bar -->
      <div class="filters">
        <input 
          id="hs" 
          placeholder="Search sender or subject" 
          oninput="filterHistory()" 
          style="max-width: 340px;"
        >
        <button class="secondary" onclick="filterRows('SPAM')">Spam</button>
        <button class="secondary" onclick="filterRows('HAM')">Ham</button>
        <button class="secondary" onclick="render()">All</button>
      </div>

      <!-- History Table -->
      <div class="panel">
        <div id="historyTable">
          ${historyRows(state.history)}
        </div>
      </div>
    </div>
  `;
}

/**
 * ════════════════════════════════════════════════════════════════
 * TABLE RENDERING
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Generate HTML for history table rows
 * @param {Array} rows - Detection records
 * @returns {string} - HTML for table rows
 */
function historyRows(rows) {
  if (!rows.length) {
    return '<div class="empty">No detections yet.</div>';
  }

  const tableRows = rows
    .map((record, index) => {
      const date = new Date(record.created_at).toLocaleString();
      const isSpam = record.classification === 'SPAM';

      return `
        <tr>
          <td>${index + 1}</td>
          <td>${date}</td>
          <td>${esc(record.subject)}</td>
          <td class="${isSpam ? 'spam' : 'ham'}">
            <b>${record.classification}</b>
          </td>
          <td>${record.spam_risk}%</td>
          <td>${record.confidence}%</td>
          <td>
            <button class="secondary" onclick="showDetail('${record.id}')">View</button>
            <button class="secondary" onclick="del('${record.id}')">Delete</button>
          </td>
        </tr>
      `;
    })
    .join('');

  return `
    <table class="history-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Date</th>
          <th>Subject</th>
          <th>Result</th>
          <th>Spam Risk</th>
          <th>Confidence</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        ${tableRows}
      </tbody>
    </table>
  `;
}

/**
 * ════════════════════════════════════════════════════════════════
 * FILTERING & SEARCH
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Filter history by classification type (SPAM or HAM)
 * @param {string} type - Classification type ('SPAM' or 'HAM')
 */
function filterRows(type) {
  const filtered = state.history.filter(record => record.classification === type);
  document.getElementById('historyTable').innerHTML = historyRows(filtered);
}

/**
 * Filter history by search query (sender or subject)
 */
function filterHistory() {
  const query = document.getElementById('hs').value.toLowerCase();
  const filtered = state.history.filter(record => {
    const searchText = (record.sender + ' ' + record.subject + ' ' + record.body).toLowerCase();
    return searchText.includes(query);
  });
  document.getElementById('historyTable').innerHTML = historyRows(filtered);
}

/**
 * ════════════════════════════════════════════════════════════════
 * HISTORY ACTIONS
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Show detail view of a specific detection record
 * Loads the record into the detection page for viewing
 * @param {string} id - Record ID
 */
function showDetail(id) {
  const record = state.history.find(item => item.id === id);
  if (!record) return;

  // Load record data into detection page
  state.email = {
    sender: record.sender,
    recipient: record.recipient,
    subject: record.subject,
    body: record.body
  };
  state.result = record.features;
  state.page = 'detection';
  render();
}

/**
 * Delete a detection record from history
 * @param {string} id - Record ID
 */
async function del(id) {
  // Delete from backend
  await api('/api/history/' + id, { method: 'DELETE' });

  // Refresh history
  state.history = await api('/api/history');
  render();
}
