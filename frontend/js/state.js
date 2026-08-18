/**
 * ════════════════════════════════════════════════════════════════
 * GLOBAL APPLICATION STATE & NAVIGATION
 * ════════════════════════════════════════════════════════════════
 * 
 * Manages:
 * - Global application state
 * - Page navigation and routing
 * - Navigation bar rendering
 */

/**
 * ════════════════════════════════════════════════════════════════
 * APP CONTAINER & STATE
 * ════════════════════════════════════════════════════════════════
 */

// Main application container element
const app = document.getElementById('app');

// Global application state object
let state = {
  page: 'home',           // Current page ('home', 'detection', 'history', 'dashboard')
  email: {},              // Current email data for analysis
  result: null,           // Last analysis result
  history: [],            // Detection history
  dash: null              // Dashboard data
};

/**
 * ════════════════════════════════════════════════════════════════
 * PAGE ROUTING
 * ════════════════════════════════════════════════════════════════
 */

// Available pages and their labels
const PAGES = [
  ['home', 'Home'],
  ['detection', 'Detection'],
  ['history', 'History'],
  ['dashboard', 'Dashboard']
];

/**
 * ════════════════════════════════════════════════════════════════
 * NAVIGATION BAR
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Generate HTML for the navigation bar
 * @returns {string} - Navigation bar HTML
 */
function nav() {
  const menuItems = PAGES
    .map(([pageKey, label]) => {
      const isActive = state.page === pageKey ? 'active' : '';
      return `<button class="menu-item ${isActive}" onclick="go('${pageKey}')">${label}</button>`;
    })
    .join('');

  return `
    <nav class="nav">
      <div class="brand">SpamSense</div>
      <div class="nav-links">
        ${menuItems}
      </div>
    </nav>
  `;
}

/**
 * ════════════════════════════════════════════════════════════════
 * PAGE RENDERING
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Render the current page based on state.page
 * Calls the appropriate page function and updates the DOM
 */
async function render() {
  let pageContent = '';

  // Determine which page to render
  if (state.page === 'home') {
    pageContent = about();
  } else if (state.page === 'detection') {
    pageContent = detection();
  } else if (state.page === 'history') {
    pageContent = await history();
  } else if (state.page === 'dashboard') {
    pageContent = await dashboard();
  }

  // Update the app container with nav + page content
  app.innerHTML = nav() + pageContent;
}

/**
 * ════════════════════════════════════════════════════════════════
 * PAGE NAVIGATION
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Navigate to a different page
 * @param {string} pageKey - Page identifier ('home', 'detection', 'history', 'dashboard')
 */
async function go(pageKey) {
  // Update current page
  state.page = pageKey;

  // Load dashboard data if navigating to dashboard
  if (pageKey === 'dashboard') {
    state.dash = await api('/api/dashboard');
  }

  // Render the new page
  await render();
}
