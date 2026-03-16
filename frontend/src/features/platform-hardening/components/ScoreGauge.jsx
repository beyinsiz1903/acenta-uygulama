import React from "react";

export function ScoreGauge({ score, max, label, size = "lg" }) {
  const pct = (score / max) * 100;
  const color = score >= 8 ? "text-emerald-400" : score >= 5 ? "text-amber-400" : "text-red-400";
  const dim = size === "lg" ? "w-32 h-32" : "w-20 h-20";
  const textSize = size === "lg" ? "text-2xl" : "text-lg";
  const subSize = size === "lg" ? "text-xs" : "text-[10px]";
  return (
    <div data-testid={`gauge-${label?.replace(/\s/g, "-").toLowerCase()}`} className="flex flex-col items-center gap-1.5">
      <div className={`relative ${dim}`}>
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r="42" fill="none" stroke="currentColor" className="text-zinc-800" strokeWidth="8" />
          <circle cx="50" cy="50" r="42" fill="none" stroke="currentColor" className={color} strokeWidth="8" strokeDasharray={`${pct * 2.64} 264`} strokeLinecap="round" />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`${textSize} font-bold ${color}`}>{score}</span>
          <span className={`${subSize} text-zinc-500`}>/{max}</span>
        </div>
      </div>
      {label && <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider text-center leading-tight">{label}</span>}
    </div>
  );
}
