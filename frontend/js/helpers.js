/**
 * ════════════════════════════════════════════════════════════════
 * SHARED HELPER UTILITIES
 * ════════════════════════════════════════════════════════════════
 * 
 * Provides:
 * - HTML escaping for security
 * - API wrapper for async requests
 * - Toast notification system
 */

/**
 * ════════════════════════════════════════════════════════════════
 * HTML ESCAPING & SANITIZATION
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Escape HTML special characters to prevent XSS attacks
 * @param {*} s - Value to escape
 * @returns {string} - Escaped string
 */
const esc = (s) => String(s ?? '')
  .replace(/[&<>"']/g, (c) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[c]));

/**
 * ════════════════════════════════════════════════════════════════
 * API COMMUNICATION
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Wrapper for fetch API with JSON parsing and error handling
 * @param {string} url - Endpoint URL
 * @param {Object} opt - Fetch options (method, body, headers, etc.)
 * @returns {Promise<Object>} - Parsed JSON response
 * @throws {Error} - If request fails or returns error status
 */
async function api(url, opt) {
  const response = await fetch(url, opt);
  const data = await response.json();
  
  if (!response.ok) {
    throw Error(data.error || 'Request failed');
  }
  
  return data;
}

/**
 * ════════════════════════════════════════════════════════════════
 * TOAST NOTIFICATIONS
 * ════════════════════════════════════════════════════════════════
 */

/**
 * Display a temporary toast notification message
 * @param {string} message - Message to display
 * @param {number} duration - Duration in milliseconds (default: 2400)
 */
function toast(message, duration = 2400) {
  const element = document.createElement('div');
  element.className = 'toast';
  element.textContent = message;
  document.body.appendChild(element);
  
  // Auto-remove after duration
  setTimeout(() => element.remove(), duration);
}
