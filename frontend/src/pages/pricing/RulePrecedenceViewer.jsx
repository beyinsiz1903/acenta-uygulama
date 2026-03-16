import React, { useState } from "react";
import { Eye, ChevronDown, ChevronUp, Trophy, XCircle, CheckCircle2 } from "lucide-react";
import { Badge } from "../../components/ui/badge";

export function RulePrecedenceViewer({ evaluatedRules }) {
  const [expanded, setExpanded] = useState(false);
  if (!evaluatedRules?.length) return null;

  const winners = evaluatedRules.filter(r => r.won);
  const losers = evaluatedRules.filter(r => !r.won);

  return (
    <div className="border rounded-lg overflow-hidden" data-testid="evaluated-rules-panel">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 bg-slate-50 hover:bg-slate-100 transition-colors duration-150"
        data-testid="toggle-evaluated-rules"
      >
        <div className="flex items-center gap-2">
          <Eye className="w-4 h-4 text-slate-500" />
          <span className="text-sm font-medium">Kural Precedence ({evaluatedRules.length} kural degerlendirildi)</span>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>
      {expanded && (
        <div className="p-3 space-y-3">
          {winners.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-emerald-700 mb-1.5 flex items-center gap-1"><Trophy className="w-3 h-3" /> Kazanan Kurallar</p>
              <div className="space-y-1.5">
                {winners.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 p-2 rounded-md bg-emerald-50 border border-emerald-200">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-emerald-800 truncate">{r.name || r.rule_id}</p>
                      <p className="text-[10px] text-emerald-600">{r.category} | Skor: {r.match_score} | Oncelik: {r.priority} | Deger: %{r.value}</p>
                    </div>
                    <Badge variant="outline" className="text-[9px] border-emerald-300 text-emerald-700 shrink-0">KAZANDI</Badge>
                  </div>
                ))}
              </div>
            </div>
          )}
          {losers.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-500 mb-1.5 flex items-center gap-1"><XCircle className="w-3 h-3" /> Diger Kurallar</p>
              <div className="space-y-1">
                {losers.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 p-2 rounded-md bg-slate-50 border border-slate-200">
                    <XCircle className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-slate-600 truncate">{r.name || r.rule_id}</p>
                      <p className="text-[10px] text-slate-400">{r.category} | Skor: {r.match_score} | Deger: %{r.value}</p>
                    </div>
                    {r.reject_reason && <Badge variant="secondary" className="text-[9px] shrink-0">{r.reject_reason}</Badge>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
