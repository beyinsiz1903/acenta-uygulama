// frontend/src/pages/crm/CrmDuplicateCustomersPage.jsx
import React, { useEffect, useState } from "react";
import { listCustomerDuplicates, mergeCustomers } from "../../lib/crm";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

function formatDate(val) {
  if (!val) return "";
  try {
    return new Date(val).toLocaleString("tr-TR");
  } catch {
    return String(val);
  }
}

export default function CrmDuplicateCustomersPage() {
  const navigate = useNavigate();
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errMsg, setErrMsg] = useState("");
  const [previewByKey, setPreviewByKey] = useState({});
  const [loadingKey, setLoadingKey] = useState("");
  const [mergingKey, setMergingKey] = useState("");

  function contactKey(c) {
    if (!c) return "";
    return `${c.type || ""}:${c.value || ""}`;
  }

  async function loadClusters() {
    setLoading(true);
    setErrMsg("");
    try {
      const res = await listCustomerDuplicates();
      setClusters(res || []);
      // Clear previews for clusters that no longer exist
      const keys = new Set((res || []).map((g) => contactKey(g.contact)));
      setPreviewByKey((prev) => {
        const next = {};
        Object.keys(prev || {}).forEach((k) => {
          if (keys.has(k)) next[k] = prev[k];
        });
        return next;
      });
    } catch (e) {
      setErrMsg(e.message || "Duplicate m\u00fc\u015fteriler y\u00fcklenemedi.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadClusters();
  }, []);

  async function handleDryRun(cluster) {
    const key = contactKey(cluster.contact);
    if (!cluster.primary || !cluster.duplicates?.length) return;
    setLoadingKey(key);
    try {
      const res = await mergeCustomers({
        primaryId: cluster.primary.id,
        duplicateIds: cluster.duplicates.map((d) => d.id),
        dryRun: true,
      });
      setPreviewByKey((prev) => ({ ...prev, [key]: res }));

      const rw = (res && res.rewired) || {};
      const b = (rw.bookings && rw.bookings.matched) || 0;
      const d = (rw.deals && rw.deals.matched) || 0;
      const t = (rw.tasks && rw.tasks.matched) || 0;
      const a = (rw.activities && rw.activities.matched) || 0;
      const msg = `Dry-run tamamland\u0131: ${b} rezervasyon, ${d} f\u0131rsat, ${t} g\u00f6rev, ${a} aktivite etkilenecek.`;
      toast.success(msg);
    } catch (e) {
      toast.error(e.message || "Dry-run ba\u015far\u0131s\u0131z oldu.");
    } finally {
      setLoadingKey("");
    }
  }

  async function handleMerge(cluster) {
    const key = contactKey(cluster.contact);
    if (!cluster.primary || !cluster.duplicates?.length) return;
    setMergingKey(key);
    try {
      const res = await mergeCustomers({
        primaryId: cluster.primary.id,
        duplicateIds: cluster.duplicates.map((d) => d.id),
        dryRun: false,
      });

      const rw = (res && res.rewired) || {};
      const b = (rw.bookings && rw.bookings.modified) || 0;
      const d = (rw.deals && rw.deals.modified) || 0;
      const t = (rw.tasks && rw.tasks.modified) || 0;
      const a = (rw.activities && rw.activities.modified) || 0;
      const msg = `Merge tamamland\u0131: ${b} rezervasyon, ${d} f\u0131rsat, ${t} g\u00f6rev, ${a} aktivite g\u00fcncellendi.`;
      toast.success(msg);

      // Optimistic remove: hide this cluster immediately
      setClusters((prev) => prev.filter((c) => contactKey(c.contact) !== key));

      // Reload clusters; merged cluster should zaten kaybolmu5f olacak
      await loadClusters();
      setPreviewByKey((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    } catch (e) {
      const msg =
        e.message ||
        (e.raw && e.raw.response && e.raw.response.data && e.raw.response.data.detail) ||
        "Merge i\u015flemi ba\u015far\u0131s\u0131z oldu.";
      if (msg === "customer_merge_conflict") {
        toast.error(
          "Bu kay\u0131t ba\u015fka bir primary'ye merge edilmi\u015f. \u00d6nce duplicate raporunu yenileyin."
        );
      } else {
        toast.error(msg);
      }
    } finally {
      setMergingKey("");
    }
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <button
          onClick={() => navigate(-1)}
          className="px-2.5 py-2 rounded-lg border border-border bg-card cursor-pointer text-sm font-medium text-foreground hover:bg-muted transition-colors"
        >
          ← Geri
        </button>
        <h1 className="m-0 text-xl font-bold text-foreground">CRM Duplicate Müşteriler</h1>
      </div>

      {errMsg ? (
        <div className="mt-3 p-3 rounded-xl border border-destructive/30 bg-destructive/5 text-destructive text-sm">
          {errMsg}
        </div>
      ) : null}

      <div className="mt-3 text-sm text-muted-foreground">
        {loading
          ? "Yükleniyor..."
          : clusters.length
          ? `${clusters.length} contact anahtarı için duplicate bulundu.`
          : "Duplicate müşteri bulunamadı."}
      </div>

      <div className="mt-3 flex flex-col gap-3">
        {!loading && clusters.length === 0 ? (
          <div className="p-6 rounded-2xl border border-border bg-muted text-center max-w-md mx-auto mt-6">
            <div className="text-3xl mb-2">👥</div>
            <div className="text-sm font-semibold mb-1 text-foreground">Duplicate müşteri bulunamadı.</div>
            <div className="text-xs text-muted-foreground">
              CRM verinizde aynı iletişim anahtarına sahip birden fazla müşteri kaydı tespit edilmedi.
            </div>
          </div>
        ) : (
          clusters.map((cluster) => {
          const key = contactKey(cluster.contact);
          const preview = previewByKey[key];
          const isLoading = loadingKey === key;
          const isMerging = mergingKey === key;
          return (
            <div key={key} className="border border-border rounded-xl p-3 bg-muted/50">
              <div className="flex justify-between gap-3 flex-wrap">
                <div>
                  <div className="text-xs text-muted-foreground">Contact</div>
                  <div className="text-sm font-semibold text-foreground">
                    {cluster.contact?.type}: {cluster.contact?.value}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleDryRun(cluster)}
                    disabled={isLoading || isMerging}
                    className="px-2.5 py-1.5 rounded-full border border-foreground bg-card text-xs disabled:cursor-not-allowed cursor-pointer hover:bg-muted transition-colors"
                  >
                    {isLoading ? "Dry-run..." : "Dry-run"}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleMerge(cluster)}
                    disabled={isMerging || !cluster.duplicates?.length}
                    className="px-2.5 py-1.5 rounded-full border border-foreground bg-foreground text-primary-foreground text-xs disabled:cursor-not-allowed cursor-pointer hover:opacity-90 transition-opacity"
                  >
                    {isMerging ? "Merge yapılıyor..." : "Merge et"}
                  </button>
                </div>
              </div>

              <div className="mt-2.5 grid grid-cols-[1fr_2fr] gap-2.5">
                <div className="border border-border rounded-lg p-2 bg-card">
                  <div className="text-xs text-muted-foreground">Primary</div>
                  <div className="text-sm font-semibold text-foreground">{cluster.primary?.name || cluster.primary?.id}</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    ID: <code>{cluster.primary?.id}</code>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {formatDate(cluster.primary?.updated_at)}
                  </div>
                </div>

                <div className="border border-border rounded-lg p-2 bg-card">
                  <div className="text-xs text-muted-foreground">Duplicates</div>
                  {cluster.duplicates?.length ? (
                    <ul className="m-0 pl-4 mt-1">
                      {cluster.duplicates.map((d) => (
                        <li key={d.id} className="mb-1">
                          <div className="text-sm font-medium text-foreground">{d.name || d.id}</div>
                          <div className="text-xs text-muted-foreground">
                            ID: <code>{d.id}</code>
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {formatDate(d.updated_at)}
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="mt-1 text-xs text-muted-foreground">Duplicate kayıt yok.</div>
                  )}
                </div>
              </div>

              {preview ? (
                <div className="mt-2.5 p-2 rounded-lg border border-dashed border-border bg-muted text-xs text-foreground">
                  <div className="font-semibold mb-1">Etki özeti (dry-run)</div>
                  <div>Bookings: {preview.rewired?.bookings?.matched || 0} hedef, {preview.rewired?.bookings?.modified || 0} değişiklik</div>
                  <div>Deals: {preview.rewired?.deals?.matched || 0} hedef, {preview.rewired?.deals?.modified || 0} değişiklik</div>
                  <div>Tasks: {preview.rewired?.tasks?.matched || 0} hedef, {preview.rewired?.tasks?.modified || 0} değişiklik</div>
                  <div>Activities: {preview.rewired?.activities?.matched || 0} hedef, {preview.rewired?.activities?.modified || 0} değişiklik</div>
                </div>
              ) : null}
            </div>
          );
        })
        )}
      </div>
    </div>
  );
}
