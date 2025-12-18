/**
 * Format ISO datetime string to Turkish locale
 * @param {string} isoString - ISO datetime string
 * @returns {string} Formatted datetime (18.12.2025 11:39)
 */
export function formatDateTime(isoString) {
  if (!isoString) return "-";
  return new Date(isoString).toLocaleString("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Normalize active status across different API responses
 * @param {object} item - API response item
 * @returns {boolean} Normalized active status
 */
export function getActiveStatus(item) {
  return item.is_active ?? item.active ?? false;
}
