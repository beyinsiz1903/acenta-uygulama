// Booking status normalization and display helpers
// Canonical status set stays entirely on frontend for now.

/**
 * @typedef {"pending" | "confirmed" | "rejected" | "cancelled" | "completed"} CanonicalStatus
 */

/**
 * Normalize raw backend status string to a small canonical set
 * @param {string | undefined | null} status
 * @returns {CanonicalStatus}
 */
export function normalizeStatus(status) {
  const s = String(status || "").trim().toLowerCase();

  // Approved-ish
  if (["confirmed", "guaranteed", "checked_in"].includes(s)) return "confirmed";

  // Completed-ish
  if (["completed", "checked_out"].includes(s)) return "completed";

  // Rejected-ish
  if (["rejected", "declined"].includes(s)) return "rejected";

  // Cancelled-ish
  if (["cancelled", "canceled"].includes(s)) return "cancelled";

  // Pending-ish (default)
  if (["pending", "created", "requested", "new", "awaiting_confirmation"].includes(s)) return "pending";

  // Unknown -> treat as pending for safety in pilot
  return "pending";
}

/**
 * Map canonical status to user-facing label and tone
 * @param {string | undefined | null} status
 * @returns {{ canonical: CanonicalStatus; text: string; tone: "green" | "red" | "yellow" | "muted" }}
 */
export function statusInfo(status) {
  const canonical = normalizeStatus(status);

  switch (canonical) {
    case "confirmed":
      return { canonical, text: "Otel tarafından onaylandı", tone: "green" };
    case "rejected":
      return { canonical, text: "Otel tarafından reddedildi", tone: "red" };
    case "cancelled":
      return { canonical, text: "İptal edildi", tone: "red" };
    case "completed":
      return { canonical, text: "Konaklama tamamlandı", tone: "muted" };
    case "pending":
    default:
      return { canonical, text: "Talep gönderildi (otel onayı bekleniyor)", tone: "yellow" };
  }
}
