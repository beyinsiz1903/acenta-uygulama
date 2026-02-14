import React, { useState, useEffect } from "react";
import { getTrialStatus, createUpgradeRequest, getPlans } from "../lib/gtm";
import { X, Zap } from "lucide-react";

export default function TrialBanner() {
  const [trial, setTrial] = useState(null);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    getTrialStatus().then(setTrial).catch(() => {});
  }, []);

  if (!trial || dismissed) return null;
  const daysLeft = trial.trial_days_remaining ?? trial.days_remaining ?? null;
  if (daysLeft === null || daysLeft < 0) return null;
  const urgent = daysLeft <= 3;

  return (
    <>
      <div className={`flex items-center justify-between px-4 py-2 text-sm ${urgent ? "bg-red-50 text-red-700 border-b border-red-200" : "bg-amber-50 text-amber-700 border-b border-amber-200"}`} data-testid="trial-banner">
        <div className="flex items-center gap-2">
          <Zap size={16} className={urgent ? "text-red-500" : "text-amber-500"} />
          <span>Deneme sureniz: <strong>{daysLeft} gun</strong> kaldi</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowUpgrade(true)} className={`px-3 py-1 rounded-full text-xs font-semibold ${urgent ? "bg-red-600 text-white hover:bg-red-700" : "bg-amber-600 text-white hover:bg-amber-700"} transition-colors`} data-testid="upgrade-cta">Plani yukselt</button>
          <button onClick={() => setDismissed(true)} className="p-0.5 hover:bg-black/5 rounded"><X size={14} /></button>
        </div>
      </div>
      {showUpgrade && <UpgradeModal onClose={() => setShowUpgrade(false)} />}
    </>
  );
}

function UpgradeModal({ onClose }) {
  const [plans, setPlans] = useState([]);
  const [sel, setSel] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getPlans().then(r => setPlans(r.plans || r || [])).catch(() => setPlans([{id:"growth",name:"Growth"},{id:"enterprise",name:"Enterprise"}]));
  }, []);

  async function handleSubmit() {
    if (!sel) return;
    setSubmitting(true); setError("");
    try {
      await createUpgradeRequest({ requested_plan: sel });
      setSuccess(true);
    } catch (e) { setError(e?.message || "Talep gonderilemedi"); }
    finally { setSubmitting(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6" onClick={e => e.stopPropagation()} data-testid="upgrade-modal">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Plan Yukseltme</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded"><X size={18} /></button>
        </div>
        {success ? (
          <div className="text-center py-6">
            <Zap className="mx-auto text-green-600 mb-2" size={32} />
            <h3 className="text-lg font-semibold text-green-700 mb-1">Talep Gonderildi!</h3>
            <p className="text-sm text-muted-foreground">Yoneticiniz talebinizi inceleyecek.</p>
            <button onClick={onClose} className="mt-4 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm">Kapat</button>
          </div>
        ) : (
          <>
            <div className="space-y-3 mb-4">
              {(Array.isArray(plans) ? plans : []).map(p => (
                <label key={p.id||p.plan_id||p.name} className={`block p-4 border rounded-lg cursor-pointer transition-colors ${sel===(p.id||p.plan_id||p.name) ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:border-gray-300"}`}>
                  <input type="radio" name="plan" value={p.id||p.plan_id||p.name} checked={sel===(p.id||p.plan_id||p.name)} onChange={e=>setSel(e.target.value)} className="hidden" />
                  <div className="font-semibold text-sm">{p.name||p.display_name||p.id}</div>
                  {p.price && <div className="text-xs text-muted-foreground mt-1">{p.price}</div>}
                </label>
              ))}
            </div>
            {error && <p className="text-sm text-red-600 mb-3">{error}</p>}
            <div className="flex gap-2 justify-end">
              <button onClick={onClose} className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50">Iptal</button>
              <button onClick={handleSubmit} disabled={!sel||submitting} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {submitting ? "Gonderiliyor..." : "Talep Gonder"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
