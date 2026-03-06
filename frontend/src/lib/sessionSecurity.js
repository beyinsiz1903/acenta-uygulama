const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("tr-TR", {
  dateStyle: "medium",
  timeStyle: "short",
});

function parseDate(value) {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatSessionTimestamp(value) {
  const date = parseDate(value);
  return date ? DATE_TIME_FORMATTER.format(date) : "-";
}

export function formatSessionRelative(value) {
  const date = parseDate(value);
  if (!date) return "Bilinmiyor";

  const diffSeconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
  if (diffSeconds < 60) return "Az önce";
  if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)} dk önce`;
  if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)} sa önce`;
  if (diffSeconds < 604800) return `${Math.floor(diffSeconds / 86400)} gün önce`;
  return formatSessionTimestamp(value);
}

export function getSessionDeviceInfo(userAgent = "") {
  const ua = String(userAgent || "").trim();
  const raw = ua.toLowerCase();

  if (!ua) {
    return {
      deviceLabel: "Tarayıcı bilgisi alınamadı",
      browser: "Bilinmiyor",
      platform: "Bilinmiyor",
      deviceType: "desktop",
      userAgentLabel: "User-Agent bilgisi gönderilmedi",
    };
  }

  const isMobile = /(android|iphone|ipad|ipod|mobile)/.test(raw);
  const deviceType = isMobile ? "mobile" : "desktop";

  let browser = "Bilinmeyen tarayıcı";
  if (raw.includes("edg/")) browser = "Microsoft Edge";
  else if (raw.includes("headlesschrome")) browser = "Headless Chrome";
  else if (raw.includes("chrome/")) browser = "Google Chrome";
  else if (raw.includes("firefox/")) browser = "Mozilla Firefox";
  else if (raw.includes("safari/") && !raw.includes("chrome/")) browser = "Safari";
  else if (raw.includes("curl/")) browser = "cURL";
  else if (raw.includes("python-requests")) browser = "Python Requests";
  else if (raw.includes("python-httpx")) browser = "Python HTTPX";

  let platform = "Bilinmeyen sistem";
  if (raw.includes("windows")) platform = "Windows";
  else if (raw.includes("android")) platform = "Android";
  else if (raw.includes("iphone") || raw.includes("ipad") || raw.includes("ios")) platform = "iOS";
  else if (raw.includes("mac os x") || raw.includes("macintosh")) platform = "macOS";
  else if (raw.includes("linux") || raw.includes("x11")) platform = "Linux";

  const deviceLabel = `${browser} · ${platform}`;
  return {
    deviceLabel,
    browser,
    platform,
    deviceType,
    userAgentLabel: ua,
  };
}

export function sortSessionsByActivity(sessions, currentSessionId = "") {
  return [...(sessions || [])].sort((left, right) => {
    if (left?.id === currentSessionId) return -1;
    if (right?.id === currentSessionId) return 1;

    const leftTime = new Date(left?.last_used_at || left?.created_at || 0).getTime();
    const rightTime = new Date(right?.last_used_at || right?.created_at || 0).getTime();
    return rightTime - leftTime;
  });
}