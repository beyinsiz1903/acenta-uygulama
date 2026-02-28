/**
 * Safely extract a display string from a value that may be a plain string
 * or a multilingual object like {tr: "...", en: "..."}.
 * @param {string|object} value - The value to display
 * @param {string} [lang="tr"] - Preferred language code
 * @returns {string}
 */
export function safeName(value, lang = "tr") {
  if (!value) return "-";
  if (typeof value === "string") return value;
  if (typeof value === "object") {
    return value[lang] || value.tr || value.en || JSON.stringify(value);
  }
  return String(value);
}

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
