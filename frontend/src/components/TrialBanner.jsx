import React, { useState, useEffect } from "react";
import { getTrialStatus, createUpgradeRequest, getPlans } from "../lib/gtm";

export default function TrialBanner() {
  const [trial, setTrial] = useState(null);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => { loadTrial(); }, []);
  async function loadTrial() { try { setTrial(await getTrialStatus()); } catch {} }

  if (!trial || dismissed) return null;
  const daysLeft = trial.trial_days_remaining ?? trial.days_remaining ?? null;
  if (daysLeft === null || daysLeft < 0) return null;
  const urgent = daysLeft <= 3;

  return (
    <>
      <div className={`flex items-center justify-between px-4 py-2 text-sm ${urgent ? "bg-red-50 text-red-700 border-b border-red-200" : "bg-amber-50 text-amber-700 border-b border-amber-200"}`} data-testid="trial-banner">
        <span>Deneme sureniz: <strong>{daysLeft} gun</strong> kaldi</span>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowUpgrade(true)} className={`px-3 py-1 rounded-full text-xs font-semibold ${urgent ? "bg-red-600 text-white" : "bg-amber-600 text-white"}`} data-testid="upgrade-cta">Plani yukselt</button>
          <button onClick={() => setDismissed(true)} className="text-xs">\u2715</button>
        </div>
      </div>
      {showUpgrade && <UpgradeModal onClose={() => setShowUpgrade(false)} />}
    </>
  );
}

function UpgradeModal({ onClose }) {
  const [plans, setPlans] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { loadPlans(); }, []);
  async function loadPlans() {
    try { const res = await getPlans(); setPlans(res.plans || res || []); }
    catch { setPlans([{ id: "growth", name: "Growth" }, { id: "enterprise", name: "Enterprise" }]); }
  }

  async function handleSubmit() {
    if (!selectedPlan) return;
    setSubmitting(true); setError("");
    try { await createUpgradeRequest({ requested_plan: selectedPlan }); setSuccess(true); }
    catch (e) { setError(e?.message || "Talep gonderilemedi"); }
    finally { setSubmitting(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6" onClick={e => e.stopPropagation()} data-testid="upgrade-modal">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Plan Yukseltme</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">\u2715</button>
        </div>
        {success ? (
          <div className="text-center py-6">
            <p className="text-green-700 font-semibold text-lg mb-2">Talep Gonderildi!</p>
            <p className="text-sm text-gray-600">Yoneticiniz talebinizi inceleyecek.</p>
            <button onClick={onClose} className="mt-4 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm">Kapat</button>
          </div>
        ) : (
          <>
            <div className="space-y-3 mb-4">
              {(Array.isArray(plans) ? plans : []).map(plan => (
                <label key={plan.id || plan.plan_id || plan.name} className={`block p-4 border rounded-lg cursor-pointer ${selectedPlan === (plan.id || plan.plan_id || plan.name) ? "border-blue-500 bg-blue-50" : "border-gray-200"}`}>
                  <input type="radio" name="plan" value={plan.id || plan.plan_id || plan.name} checked={selectedPlan === (plan.id || plan.plan_id || plan.name)} onChange={e => setSelectedPlan(e.target.value)} className="hidden" />
                  <div className="font-semibold text-sm">{plan.name || plan.display_name || plan.id}</div>
                  {plan.price && <div className="text-xs text-gray-500 mt-1">{plan.price}</div>}
                </label>
              ))}
            </div>
            {error && <p className="text-sm text-red-600 mb-3">{error}</p>}
            <div className="flex gap-2 justify-end">
              <button onClick={onClose} className="px-4 py-2 text-sm border rounded-lg">Iptal</button>
              <button onClick={handleSubmit} disabled={!selectedPlan || submitting} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg disabled:opacity-50">{submitting ? "Gonderiliyor..." : "Talep Gonder"}</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
