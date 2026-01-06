from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth import require_super_admin_only
from app.db import get_db
from app.utils import now_utc

router = APIRouter(prefix="/api/admin/reports/match-risk", tags=["admin-match-risk-reports"])


async def _load_last_snapshots(db, organization_id: str, snapshot_key: str = "match_risk_daily", limit: int = 2) -> List[Dict[str, Any]]:
  cursor = (
    db.risk_snapshots.find({"organization_id": organization_id, "snapshot_key": snapshot_key})
    .sort("generated_at", -1)
    .limit(limit)
  )
  docs = await cursor.to_list(length=limit)
  return docs


def _compute_delta_metric(prev_val: Optional[float], last_val: Optional[float]) -> Dict[str, Any]:
  start = float(prev_val or 0.0)
  end = float(last_val or 0.0)
  abs_change = end - start
  if start == 0.0:
    pct_change = None
  else:
    pct_change = (abs_change / start) * 100.0
  if abs_change > 0:
    direction = "up"
  elif abs_change < 0:
    direction = "down"
  else:
    direction = "flat"
  return {
    "start": start,
    "end": end,
    "abs_change": abs_change,
    "pct_change": pct_change,
    "direction": direction,
  }


def _render_match_risk_pdf_html(context: Dict[str, Any]) -> str:
  org_name = context.get("org_name") or ""
  snapshot_date = context.get("snapshot_date") or "-"
  window = context.get("window") or {}
  window_days = window.get("days")
  window_min_total = window.get("min_total")

  high = context.get("high_risk_rate") or {}
  ver = context.get("verified_share") or {}

  def fmt_pct(x: Optional[float]) -> str:
    if x is None:
      return "n/a"
    return f"{round(x * 100)}%"

  def fmt_points(x: float) -> str:
    pts = round(x * 100)
    sign = "+" if pts > 0 else "" if pts < 0 else ""
    return f"{sign}{pts} puan"

  def fmt_delta(delta: Dict[str, Any]) -> str:
    if not delta:
      return "Değişim: n/a"
    pct = delta.get("pct_change")
    abs_change = float(delta.get("abs_change") or 0.0)
    if pct is None:
      return "Değişim: n/a"
    pts = fmt_points(abs_change)
    pct_str = f"{round(pct)}%"
    return f"Değişim: {pts} ({pct_str})"

  offenders: List[Dict[str, Any]] = context.get("top_offenders") or []

  def fmt_rate(v: Optional[float]) -> str:
    if v is None:
      return "-"
    return f"{round(v * 100)}%"

  def html_escape(s: Any) -> str:
    if s is None:
      return ""
    return (
      str(s)
      .replace("&", "&amp;")
      .replace("<", "&lt;")
      .replace(">", "&gt;")
    )

  if not context.get("has_snapshot"):
    return """<html><head><meta charset='utf-8' /></head><body>
<h1>Match Risk – Executive Summary</h1>
<p>Bu organizasyon için henüz risk snapshot'ı oluşturulmadı.</p>
</body></html>"""

  window_str = ""
  if window_days is not None:
    window_str = f"Son {window_days} gün"
    if window_min_total is not None:
      window_str += f", min_total={window_min_total}"

  rows_html = "".join(
    f"<tr>"
    f"<td>{idx + 1}</td>"
    f"<td>{html_escape(off.get('agency_name') or off.get('agency_id') or '-')} — {html_escape(off.get('hotel_name') or off.get('hotel_id') or '-')}</td>"
    f"<td>{fmt_rate(off.get('no_show_rate'))}</td>"
    f"<td>{off.get('repeat_no_show_7') or 0}</td>"
    f"<td>{fmt_rate(off.get('verified_share'))}</td>"
    f"<td>{', '.join(off.get('high_risk_reasons') or [])}</td>"
    f"</tr>"
    for idx, off in enumerate(offenders)
  )

  return f"""<html><head><meta charset='utf-8' />
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 12px; color: #111827; }}
    h1 {{ font-size: 20px; margin-bottom: 4px; }}
    h2 {{ font-size: 14px; margin-top: 16px; margin-bottom: 4px; }}
    .muted {{ color: #6B7280; font-size: 11px; }}
    .section {{ margin-top: 12px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 4px; }}
    th, td {{ border: 1px solid #E5E7EB; padding: 4px 6px; text-align: left; }}
    th {{ background-color: #F9FAFB; font-weight: 600; }}
  </style>
</head><body>
<h1>Match Risk – Executive Summary</h1>
<p class='muted'>{html_escape(org_name)} · {snapshot_date} · {html_escape(window_str)}</p>

<div class='section'>
  <h2>Trend Özeti</h2>
  <p><strong>High risk rate:</strong> Son: {fmt_pct(high.get('end'))} (Önce: {fmt_pct(high.get('start'))})<br/>
  {fmt_delta(high)}</p>
  <p><strong>Verified share avg:</strong> Son: {fmt_pct(ver.get('end'))} (Önce: {fmt_pct(ver.get('start'))})<br/>
  {fmt_delta(ver)}</p>
</div>

<div class='section'>
  <h2>Top offenders</h2>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Agency – Hotel</th>
        <th>No-show rate</th>
        <th>Repeat no-show (7g)</th>
        <th>Verified share</th>
        <th>Reasons</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</div>

</body></html>"""


@router.get("/executive-summary.pdf", dependencies=[Depends(require_super_admin_only())])
async def download_match_risk_executive_pdf(response: Response, db=Depends(get_db), user=Depends(require_super_admin_only())):
  org_id = user.get("organization_id")
  org_name = user.get("organization_name") or ""

  docs = await _load_last_snapshots(db, org_id, "match_risk_daily", limit=2)
  if not docs:
    html = _render_match_risk_pdf_html({"has_snapshot": False})
  else:
    last = docs[0]
    prev = docs[1] if len(docs) > 1 else None
    metrics_last = (last.get("metrics") or {})
    metrics_prev = (prev.get("metrics") or {}) if prev else {}

    high_delta = _compute_delta_metric(metrics_prev.get("high_risk_rate"), metrics_last.get("high_risk_rate"))
    ver_delta = _compute_delta_metric(metrics_prev.get("verified_share_avg"), metrics_last.get("verified_share_avg"))

    window = last.get("window") or {}
    generated_at = last.get("generated_at")
    snapshot_date = generated_at.date().isoformat() if hasattr(generated_at, "date") else "-"

    top_offenders = (last.get("top_offenders") or [])[:10]

    html = _render_match_risk_pdf_html(
      {
        "has_snapshot": True,
        "org_name": org_name,
        "snapshot_date": snapshot_date,
        "window": window,
        "high_risk_rate": high_delta,
        "verified_share": ver_delta,
        "top_offenders": top_offenders,
      }
    )

  # Lazy import WeasyPrint to avoid startup issues if libpangoft2 missing
  from weasyprint import HTML  # type: ignore

  pdf_bytes = HTML(string=html).write_pdf()

  today_str = now_utc().date().isoformat()
  filename = f"match-risk-executive-summary_{today_str}.pdf"

  return Response(
    content=pdf_bytes, 
    media_type="application/pdf",
    headers={
      "Content-Type": "application/pdf",
      "Content-Disposition": f"attachment; filename=\"{filename}\""
    }
  )
