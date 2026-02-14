import React, { useMemo } from "react";

/**
 * data format:
 * [{ date: "YYYY-MM-DD", pending: 1, confirmed: 2, cancelled: 0, total: 3 }, ...]
 *
 * Pure SVG (no recharts) -> Emergent'te dependency riski yok.
 */
export function TrendChart({ data = [], height = 220, testId }) {
  const { pointsConfirmed, pointsPending, labels, maxY } = useMemo(() => {
    const safe = Array.isArray(data) ? data : [];
    const maxVal = safe.reduce((m, r) => {
      const a = Number(r?.confirmed || 0);
      const b = Number(r?.pending || 0);
      return Math.max(m, a, b);
    }, 0);

    const maxY2 = Math.max(1, maxVal);
    const xs = safe.map((_, i) => i);

    const mkPoints = (key) =>
      safe.map((r, i) => ({
        x: i,
        y: Number(r?.[key] || 0),
      }));

    const lbls = safe.map((r) => String(r?.date || ""));

    return {
      pointsConfirmed: mkPoints("confirmed"),
      pointsPending: mkPoints("pending"),
      labels: lbls,
      maxY: maxY2,
      xs,
    };
  }, [data]);

  const w = 1000; // internal viewBox width
  const h = height;
  const padL = 48;
  const padR = 18;
  const padT = 14;
  const padB = 34;

  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const n = Math.max(1, (data || []).length);
  const xScale = (i) => padL + (n === 1 ? plotW / 2 : (i * plotW) / (n - 1));
  const yScale = (v) => padT + plotH - (v * plotH) / maxY;

  const poly = (pts) =>
    pts
      .map((p, i) => `${i === 0 ? "M" : "L"} ${xScale(p.x)} ${yScale(p.y)}`)
      .join(" ");

  const ticks = 4;
  const yTicks = Array.from({ length: ticks + 1 }, (_, i) => Math.round((maxY * i) / ticks));

  const xLabelEvery = n <= 10 ? 1 : n <= 20 ? 2 : Math.ceil(n / 10);

  return (
    <div className="rounded-xl border bg-card p-4" data-testid={testId}>
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm font-medium">📈 Son Günler Trend</div>
        <div className="text-xs text-muted-foreground">
          confirmed / pending
        </div>
      </div>

      <div className="mt-3 w-full overflow-hidden">
        {n === 0 ? (
          <div className="text-sm text-muted-foreground py-10 text-center">
            Bu dönemde veri yok.
          </div>
        ) : (
          <svg
            viewBox={`0 0 ${w} ${h}`}
            className="w-full h-auto"
            role="img"
            aria-label="Booking trends"
          >
            {/* grid + y ticks */}
            {yTicks.map((t, idx) => {
              const y = yScale(t);
              return (
                <g key={idx}>
                  <line x1={padL} y1={y} x2={w - padR} y2={y} stroke="currentColor" opacity="0.08" />
                  <text x={padL - 8} y={y + 4} textAnchor="end" fontSize="12" fill="currentColor" opacity="0.6">
                    {t}
                  </text>
                </g>
              );
            })}

            {/* axes */}
            <line x1={padL} y1={padT} x2={padL} y2={h - padB} stroke="currentColor" opacity="0.25" />
            <line x1={padL} y1={h - padB} x2={w - padR} y2={h - padB} stroke="currentColor" opacity="0.25" />

            {/* pending line */}
            <path d={poly(pointsPending)} fill="none" stroke="currentColor" opacity="0.55" strokeWidth="3" />

            {/* confirmed line (dashed to distinguish without color assumption) */}
            <path
              d={poly(pointsConfirmed)}
              fill="none"
              stroke="currentColor"
              opacity="0.85"
              strokeWidth="3"
              strokeDasharray="6 5"
            />

            {/* x labels */}
            {labels.map((lbl, i) => {
              if (i % xLabelEvery !== 0 && i !== n - 1) return null;
              const x = xScale(i);
              const short = lbl ? lbl.slice(5) : ""; // MM-DD
              return (
                <text
                  key={i}
                  x={x}
                  y={h - 12}
                  textAnchor="middle"
                  fontSize="12"
                  fill="currentColor"
                  opacity="0.6"
                >
                  {short}
                </text>
              );
            })}
          </svg>
        )}
      </div>

      <div className="mt-2 text-xs text-muted-foreground">
        Çizgiler: <span className="font-medium">confirmed</span> (kesikli) / <span className="font-medium">pending</span> (düz)
      </div>
    </div>
  );
}
