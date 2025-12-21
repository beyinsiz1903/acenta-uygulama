import React from "react";

// Minimal StepBar: 3 adım (Otel → Fiyat → Misafir)
// current: 1 | 2 | 3
export default function StepBar({ current = 1, className = "" }) {
  const steps = [
    { key: 1, label: "Otel" },
    { key: 2, label: "Fiyat" },
    { key: 3, label: "Misafir" },
  ];

  return (
    <div className={`w-full ${className}`}>
      <div className="flex items-center gap-3 flex-wrap">
        {steps.map((s, idx) => {
          const isActive = s.key === current;
          const isDone = s.key < current;

          return (
            <React.Fragment key={s.key}>
              <div className="flex items-center gap-2">
                <div
                  className={[
                    "h-7 w-7 rounded-full flex items-center justify-center text-xs font-semibold border",
                    isActive
                      ? "bg-foreground text-background border-foreground"
                      : isDone
                      ? "bg-muted text-foreground border-muted-foreground/30"
                      : "bg-background text-muted-foreground border-muted-foreground/30",
                  ].join(" ")}
                  aria-label={`${s.key}/3`}
                >
                  {s.key}
                </div>

                <div className="leading-tight">
                  <div
                    className={[
                      "text-xs font-medium",
                      isActive ? "text-foreground" : "text-muted-foreground",
                    ].join(" ")}
                  >
                    {s.key}/3
                  </div>
                  <div
                    className={[
                      "text-sm font-semibold",
                      isActive ? "text-foreground" : "text-muted-foreground",
                    ].join(" ")}
                  >
                    {s.label}
                  </div>
                </div>
              </div>

              {idx < steps.length - 1 && (
                <div
                  className={[
                    "flex-1 h-px min-w-[24px]",
                    s.key < current ? "bg-foreground/30" : "bg-muted-foreground/20",
                  ].join(" ")}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
