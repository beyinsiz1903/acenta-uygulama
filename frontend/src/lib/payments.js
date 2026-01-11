// Helpers for Stripe payment UI (FAZ 2)

// Deterministic Idempotency-Key generator
// Format: bookingId|action|amountCents|bucket
// where bucket is a time bucket (e.g. 30s) to avoid infinite reuse.
export function makeIdempotencyKey({ bookingId, action, amountCents }) {
  const ts = Date.now();
  const bucketSizeMs = 30_000; // 30 seconds buckets
  const bucket = Math.floor(ts / bucketSizeMs);
  const raw = `${bookingId || "unknown"}|${action || "unknown"}|${amountCents || 0}|${bucket}`;

  try {
    if (typeof btoa !== "undefined") {
      return btoa(raw);
    }
  } catch {
    // ignore
  }

  // Fallback: simple hex encoding
  return Buffer.from(raw, "utf-8").toString("hex");
}
