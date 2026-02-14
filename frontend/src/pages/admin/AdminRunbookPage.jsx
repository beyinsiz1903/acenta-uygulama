import React, { useEffect, useState, useCallback } from "react";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { BookOpen, RefreshCw, ChevronDown, ChevronRight, ExternalLink, Terminal } from "lucide-react";

const SEVERITY_STYLE = {
  P0: "bg-red-100 text-red-700",
  P1: "bg-orange-100 text-orange-700",
  P2: "bg-amber-100 text-amber-700",
  Scheduled: "bg-blue-100 text-blue-700",
};

export default function AdminRunbookPage() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState({});

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get("/admin/system/runbook");
      setEntries(res.data?.entries || []);
      // Auto-expand all
      const exp = {};
      (res.data?.entries || []).forEach((e) => { exp[e.id] = true; });
      setExpanded(exp);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggle = (id) => setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));

  return (
    <div className="space-y-6" data-testid="runbook-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BookOpen className="h-6 w-6 text-orange-600" />
          <h1 className="text-2xl font-bold text-foreground">Ops Runbook</h1>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
          Yenile
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground/60" />
        </div>
      ) : entries.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <BookOpen className="h-12 w-12 mx-auto mb-3 text-muted-foreground/40" />
          <p>Runbook girdisi bulunamadı</p>
        </div>
      ) : (
        <div className="space-y-4" data-testid="runbook-entries">
          {entries.map((entry) => {
            const isOpen = expanded[entry.id];
            const svStyle = SEVERITY_STYLE[entry.severity] || "bg-gray-100 text-muted-foreground";
            return (
              <div key={entry.id} className="bg-white border rounded-lg overflow-hidden shadow-sm">
                {/* Header */}
                <button
                  className="w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 transition-colors"
                  onClick={() => toggle(entry.id)}
                >
                  {isOpen ? <ChevronDown className="h-4 w-4 text-muted-foreground/60" /> : <ChevronRight className="h-4 w-4 text-muted-foreground/60" />}
                  <Badge className={svStyle}>{entry.severity}</Badge>
                  <span className="font-semibold text-foreground flex-1 text-left">{entry.title}</span>
                  <span className="text-xs text-muted-foreground/60">Hedef: {entry.target_time}</span>
                </button>

                {/* Steps */}
                {isOpen && (
                  <div className="border-t px-4 py-3">
                    <ol className="space-y-3">
                      {entry.steps.map((step) => (
                        <li key={step.order} className="flex items-start gap-3">
                          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 text-xs flex items-center justify-center font-bold">
                            {step.order}
                          </span>
                          <div className="flex-1">
                            <p className="text-sm font-medium text-foreground">{step.action}</p>
                            <p className="text-xs text-muted-foreground mt-0.5">{step.detail}</p>
                            <div className="flex gap-2 mt-1">
                              {step.api && (
                                <span className="inline-flex items-center gap-1 text-xs bg-gray-100 text-muted-foreground px-2 py-0.5 rounded font-mono">
                                  <Terminal className="h-3 w-3" /> {step.api}
                                </span>
                              )}
                              {step.page && (
                                <a
                                  href={step.page}
                                  className="inline-flex items-center gap-1 text-xs bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded hover:bg-indigo-100 transition-colors"
                                >
                                  <ExternalLink className="h-3 w-3" /> Sayfayı Aç
                                </a>
                              )}
                            </div>
                          </div>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
