import React, { useState } from "react";
import { seedDemoData } from "../lib/gtm";

export default function DemoSeedButton() {
  const [showModal, setShowModal] = useState(false);
  const [mode, setMode] = useState("light");
  const [withFinance, setWithFinance] = useState(true);
  const [withCrm, setWithCrm] = useState(true);
  const [force, setForce] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function handleSeed() {
    setLoading(true); setError(""); setResult(null);
    try { setResult(await seedDemoData({ mode, with_finance: withFinance, with_crm: withCrm, force })); }
    catch (e) { setError(e?.message || "Demo verisi olusturulamadi"); }
    finally { setLoading(false); }
  }

  return (
    <>
      <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm font-medium" data-testid="demo-seed-btn">Demo verisi olustur</button>
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => !loading && setShowModal(false)}>
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6" onClick={e => e.stopPropagation()} data-testid="demo-seed-modal">
            <h2 className="text-lg font-bold mb-4">Demo Verisi Olustur</h2>
            {result ? (
              <div className="text-center py-4">
                {result.already_seeded ? (
                  <div><p className="text-amber-700 font-medium">Zaten demo verisi mevcut</p><p className="text-sm text-gray-500 mt-1">Yeniden olusturmak icin "Zorla" secenegini aktiflestin.</p></div>
                ) : (
                  <div><p className="text-green-700 font-medium">Demo verisi olusturuldu!</p>
                    <div className="mt-3 text-sm text-gray-600 space-y-1">{Object.entries(result.counts || {}).map(([k, v]) => <div key={k}>{k}: <strong>{v}</strong></div>)}</div>
                    <a href="/app" className="inline-block mt-4 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm">Dashboard'a don</a>
                  </div>
                )}
                <button onClick={() => { setResult(null); setShowModal(false); }} className="mt-3 text-sm text-gray-500">Kapat</button>
              </div>
            ) : (
              <>
                <div className="space-y-4">
                  <div><label className="block text-sm font-medium text-gray-700 mb-1">Mod</label>
                    <div className="flex gap-2">{["light", "full"].map(m => <button key={m} onClick={() => setMode(m)} className={`px-4 py-2 rounded-lg text-sm border ${mode === m ? "bg-purple-600 text-white border-purple-600" : "bg-white border-gray-300"}`}>{m === "light" ? "Hafif" : "Tam"}</button>)}</div>
                  </div>
                  <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={withFinance} onChange={e => setWithFinance(e.target.checked)} className="rounded" /><span className="text-sm">Finans verileri dahil</span></label>
                  <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={withCrm} onChange={e => setWithCrm(e.target.checked)} className="rounded" /><span className="text-sm">CRM verileri dahil</span></label>
                  <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={force} onChange={e => setForce(e.target.checked)} className="rounded" /><span className="text-sm">Zorla (mevcut demo verileri sil)</span></label>
                </div>
                {error && <p className="text-sm text-red-600 mt-3">{error}</p>}
                <div className="flex gap-2 justify-end mt-6">
                  <button onClick={() => setShowModal(false)} className="px-4 py-2 text-sm border rounded-lg">Iptal</button>
                  <button onClick={handleSeed} disabled={loading} className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm disabled:opacity-50" data-testid="demo-seed-confirm">{loading ? "Olusturuluyor..." : "Olustur"}</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
