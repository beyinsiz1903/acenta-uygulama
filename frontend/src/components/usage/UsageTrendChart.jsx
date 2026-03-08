import React from "react";
import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend } from "recharts";

function UsageTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-xl border bg-card px-3 py-2 shadow-lg">
      <p className="text-xs text-muted-foreground">{label}</p>
      {payload.map((item) => (
        <p key={item.dataKey} className="text-sm font-medium" style={{ color: item.color }}>
          {item.name}: {Number(item.value || 0).toLocaleString("tr-TR")}
        </p>
      ))}
    </div>
  );
}

export const UsageTrendChart = ({ data = [], testId = "usage-trend-chart", title = "Last 30 days" }) => {
  const hasData = data.some((item) => item.reservationCreated || item.reportGenerated || item.exportGenerated);

  return (
    <div className="rounded-3xl border bg-card/85 p-5" data-testid={testId}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-foreground" data-testid={`${testId}-title`}>{title}</h2>
          <p className="text-sm text-muted-foreground" data-testid={`${testId}-subtitle`}>Reservations, reports ve exports trendini son 30 gün için izleyin.</p>
        </div>
      </div>

      {!hasData ? (
        <div className="flex min-h-[280px] items-center justify-center rounded-2xl border border-dashed text-sm text-muted-foreground" data-testid={`${testId}-empty`}>
          Son 30 günde gösterilecek usage hareketi bulunmuyor.
        </div>
      ) : (
        <div className="h-[300px] w-full" data-testid={`${testId}-canvas`}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.18} />
              <XAxis dataKey="date" tickFormatter={(value) => value.slice(5)} tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip content={<UsageTooltip />} />
              <Legend />
              <Line type="monotone" dataKey="reservationCreated" name="Reservations" stroke="#0f766e" strokeWidth={3} dot={false} />
              <Line type="monotone" dataKey="reportGenerated" name="Reports" stroke="#2563eb" strokeWidth={3} dot={false} />
              <Line type="monotone" dataKey="exportGenerated" name="Exports" stroke="#ea580c" strokeWidth={3} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};