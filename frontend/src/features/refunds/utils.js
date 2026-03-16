/**
 * Refunds feature — utility functions.
 */

export function isPdfDoc(doc) {
  const ct = (doc?.content_type || "").toLowerCase();
  const fn = (doc?.filename || "").toLowerCase();
  return ct === "application/pdf" || fn.endsWith(".pdf");
}

export function buildCsvRows(rows) {
  return rows.map((it) => {
    const approvedAmount = it.approved?.amount;
    const amount =
      typeof approvedAmount === "number"
        ? approvedAmount
        : typeof it.computed_refundable === "number"
        ? it.computed_refundable
        : typeof it.requested_amount === "number"
        ? it.requested_amount
        : null;

    return {
      refund_case_id: it.case_id,
      booking_id: it.booking_id,
      status: it.status,
      amount,
      currency: it.currency,
      created_at: it.created_at || "",
      updated_at: it.updated_at || "",
      agency_name: it.agency_name || "",
      agency_id: it.agency_id || "",
      reason: it.reason || "",
    };
  });
}

export function exportRefundsCsv(rows, mode) {
  if (!rows.length) return false;

  const mapped = buildCsvRows(rows);
  const headers = [
    "refund_case_id", "booking_id", "status", "amount", "currency",
    "created_at", "updated_at", "agency_name", "agency_id", "reason",
  ];

  const csvLines = [headers.join(",")];
  for (const row of mapped) {
    const line = headers
      .map((h) => {
        const v = row[h];
        if (v == null) return "";
        const s = String(v);
        if (s.includes(",") || s.includes('"') || s.includes("\n")) {
          return `"${s.replace(/"/g, '""')}"`;
        }
        return s;
      })
      .join(",");
    csvLines.push(line);
  }

  const blob = new Blob([csvLines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const ts = new Date().toISOString().replace(/[:.]/g, "-");
  const suffix = mode === "selected" ? "selected" : "filtered";
  a.download = `refunds_${suffix}_${ts}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
  return true;
}

export const TAG_OPTIONS = ["dekont", "iptal_yazisi", "musteri_yazismasi", "kimlik", "diger"];

export const TAG_LABELS = {
  dekont: "Dekont",
  iptal_yazisi: "Iptal yazisi",
  musteri_yazismasi: "Musteri yazismasi",
  kimlik: "Kimlik",
  diger: "Diger",
};
