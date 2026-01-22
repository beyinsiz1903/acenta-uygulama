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
    <div style={{ padding: 16 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            padding: "8px 10px",
            borderRadius: 10,
            border: "1px solid #ddd",
            background: "#fff",
            cursor: "pointer",
          }}
        >
          ← Geri
        </button>
        <h1 style={{ margin: 0, fontSize: 22 }}>CRM Duplicate Müşteriler</h1>
      </div>

      {errMsg ? (
        <div
          style={{
            marginTop: 12,
            padding: 12,
            borderRadius: 12,
            border: "1px solid #f2caca",
            background: "#fff5f5",
            color: "#8a1f1f",
            fontSize: 13,
          }}
        >
          {errMsg}
        </div>
      ) : null}

      <div style={{ marginTop: 12, fontSize: 13, color: "#666" }}>
        {loading
          ? "Y\u00fckleniyor..."
          : clusters.length
          ? `${clusters.length} contact anahtar\u0131 i\u00e7in duplicate bulundu.`
          : "Duplicate m\u00fc\u015fteri bulunamad\u0131."}
      </div>

      <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 12 }}>
        {!loading && clusters.length === 0 ? (
          <div
            style={{
              padding: 24,
              borderRadius: 16,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              textAlign: "center",
              maxWidth: 420,
              margin: "24px auto 0",
            }}
          >
            <div style={{ fontSize: 32, marginBottom: 8 }}>👥</div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>Duplicate müşteri bulunamadı.</div>
            <div style={{ fontSize: 12, color: "#6b7280" }}>
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
            <div
              key={key}
              style={{
                border: "1px solid #eee",
                borderRadius: 12,
                padding: 12,
                background: "#fafafa",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontSize: 12, color: "#666" }}>Contact</div>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>
                    {cluster.contact?.type}: {cluster.contact?.value}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    type="button"
                    onClick={() => handleDryRun(cluster)}
                    disabled={isLoading || isMerging}
                    style={{
                      padding: "6px 10px",
                      borderRadius: 999,
                      border: "1px solid #111",
                      background: "#fff",
                      cursor: isLoading || isMerging ? "not-allowed" : "pointer",
                      fontSize: 12,
                    }}
                  >
                    {isLoading ? "Dry-run..." : "Dry-run"}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleMerge(cluster)}
                    disabled={isMerging || !cluster.duplicates?.length}
                    style={{
                      padding: "6px 10px",
                      borderRadius: 999,
                      border: "1px solid #111",
                      background: "#111",
                      color: "#fff",
                      cursor: isMerging || !cluster.duplicates?.length ? "not-allowed" : "pointer",
                      fontSize: 12,
                    }}
                  >
                    {isMerging ? "Merge yap\u0131l\u0131yor..." : "Merge et"}
                  </button>
                </div>
              </div>

              {/* Primary + duplicates list */}
              <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 2fr", gap: 10 }}>
                <div
                  style={{
                    border: "1px solid #e5e5e5",
                    borderRadius: 10,
                    padding: 8,
                    background: "#fff",
                  }}
                >
                  <div style={{ fontSize: 12, color: "#666" }}>Primary</div>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{cluster.primary?.name || cluster.primary?.id}</div>
                  <div style={{ marginTop: 4, fontSize: 11, color: "#666" }}>
                    ID: <code>{cluster.primary?.id}</code>
                  </div>
                  <div style={{ marginTop: 4, fontSize: 11, color: "#666" }}>
                    {formatDate(cluster.primary?.updated_at)}
                  </div>
                </div>

                <div
                  style={{
                    border: "1px solid #e5e5e5",
                    borderRadius: 10,
                    padding: 8,
                    background: "#fff",
                  }}
                >
                  <div style={{ fontSize: 12, color: "#666" }}>Duplicates</div>
                  {cluster.duplicates?.length ? (
                    <ul style={{ margin: 0, paddingLeft: 16, marginTop: 4 }}>
                      {cluster.duplicates.map((d) => (
                        <li key={d.id} style={{ marginBottom: 4 }}>
                          <div style={{ fontSize: 13, fontWeight: 500 }}>{d.name || d.id}</div>
                          <div style={{ fontSize: 11, color: "#666" }}>
                            ID: <code>{d.id}</code>
                          </div>
                          <div style={{ fontSize: 11, color: "#666" }}>
                            {formatDate(d.updated_at)}
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div style={{ marginTop: 4, fontSize: 12, color: "#666" }}>Duplicate kay\u0131t yok.</div>
                  )}
                </div>
              </div>

              {/* Dry-run preview per cluster */}
              {preview ? (
                <div
                  style={{
                    marginTop: 10,
                    padding: 8,
                    borderRadius: 10,
                    border: "1px dashed #e5e7eb",
                    background: "#f9fafb",
                    fontSize: 12,
                    color: "#444",
                  }}
                >
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>Etki \u00f6zeti (dry-run)</div>
                  <div>Bookings: {preview.rewired?.bookings?.matched || 0} hedef, {preview.rewired?.bookings?.modified || 0} de\u011fi\u015fiklik</div>
                  <div>Deals: {preview.rewired?.deals?.matched || 0} hedef, {preview.rewired?.deals?.modified || 0} de\u011fi\u015fiklik</div>
                  <div>Tasks: {preview.rewired?.tasks?.matched || 0} hedef, {preview.rewired?.tasks?.modified || 0} de\u011fi\u015fiklik</div>
                  <div>Activities: {preview.rewired?.activities?.matched || 0} hedef, {preview.rewired?.activities?.modified || 0} de\u011fi\u015fiklik</div>
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
