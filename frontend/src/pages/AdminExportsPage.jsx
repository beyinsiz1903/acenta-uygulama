import React, { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Switch } from "../components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { Loader2, AlertCircle } from "lucide-react";

export default function AdminExportsPage() {
  const [tab, setTab] = useState("policies");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [policies, setPolicies] = useState([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [form, setForm] = useState({
    key: "",
    enabled: true,
    schedule_hint: "",
    cooldown_hours: 24,
    params: {
      days: 30,
      min_matches: 5,
      only_high_risk: false,
    },
    recipients: "",
  });

  const [saving, setSaving] = useState(false);
  const [runDryResult, setRunDryResult] = useState(null);
  const [runLoading, setRunLoading] = useState(false);

  const [runs, setRuns] = useState([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [runsPolicyKey, setRunsPolicyKey] = useState("");
  const [runsDeeplinkTemplate, setRunsDeeplinkTemplate] = useState("");

  const loadPolicies = async () => {
    try {
      setLoading(true);
      setError("");
      const resp = await api.get("/admin/exports/policies");
      const items = resp.data?.items || [];
      setPolicies(items);
      if (!selectedKey && items.length > 0) {
        const firstKey = items[0].key;
        setSelectedKey(firstKey);
        setRunsPolicyKey(firstKey);
        applyPolicyToForm(items[0]);
      }
    } catch (e) {
      console.error("Exports policies fetch failed", e);
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const applyPolicyToForm = (p) => {
    setForm({
      key: p.key,
      enabled: p.enabled,
      schedule_hint: p.schedule_hint || "",
      cooldown_hours: p.cooldown_hours ?? 24,
      params: {
        days: p.params?.days ?? 30,
        min_matches: p.params?.min_matches ?? 5,
        only_high_risk: p.params?.only_high_risk ?? false,
      },
      recipients: (p.recipients || []).join(", "),
    });
  };

  useEffect(() => {
    loadPolicies();
  }, []);

  const loadRuns = async (key) => {
    if (!key) {
      setRuns([]);
      return;
    }
    try {
      setRunsLoading(true);
      const resp = await api.get("/admin/exports/runs", {
        params: { key, limit: 50 },
      });
      setRuns(resp.data?.items || []);
      setRunsDeeplinkTemplate(resp.data?.admin_deeplink_template || "");
    } catch (e) {
      console.error("Exports runs fetch failed", e);
    } finally {
      setRunsLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      if (!form.key) {
        alert("Policy anahtarı (key) zorunludur");
        return;
      }
      setSaving(true);
      setError("");
      const recipients = form.recipients
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const payload = {
        key: form.key,
        enabled: form.enabled,
        type: "match_risk_summary",
        format: "csv",
        schedule_hint: form.schedule_hint || null,
        recipients,
        cooldown_hours: form.cooldown_hours,
        params: {
          days: form.params.days,
          min_matches: form.params.min_matches,
          only_high_risk: form.params.only_high_risk,
        },
      };
      await api.put(`/admin/exports/policies/${form.key}`, payload);
      await loadPolicies();
      alert("Policy kaydedildi");
    } catch (e) {
      console.error("Exports policy save failed", e);
      setError(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const handleRun = async (dry) => {
    if (!form.key) {
      alert("f6nce policy kaydet");
      return;
    }
    try {
      setRunLoading(true);
      setError("");
      setRunDryResult(null);
      const resp = await api.post("/admin/exports/run", null, {
        params: {
          key: form.key,
          dry_run: dry ? 1 : 0,
        },
      });
      const data = resp.data;
      if (dry) {
        setRunDryResult(data);
      } else {
        alert(
          `Run now tamamlandı. run_id=${data.run_id || "-"}${
            data.emailed ? ` (emailed to: ${(data.emailed_to || []).join(", ")})` : ""
          }`
        );
        setRunsPolicyKey(form.key);
        await loadRuns(form.key);
      }
    } catch (e) {
      console.error("Exports run failed", e);
      const msg = apiErrorMessage(e);
      setError(msg);
      if (!dry && msg.includes("EXPORT_COOLDOWN_ACTIVE")) {
        alert("Cooldown aktif; bu policy için bir süre tekrar çalıştırılamaz.");
      }
    } finally {
      setRunLoading(false);
    }
  };

  const handleDownload = async (runId) => {
    try {
      const resp = await api.get(`/admin/exports/runs/${runId}/download`, {
        responseType: "blob",
      });
      const blob = resp.data;
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      const disposition = resp.headers["content-disposition"] || "";
      const match = /filename=([^;]+)/.exec(disposition);
      const filename = match ? match[1] : "export.csv";
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Exports download failed", e);
      alert(apiErrorMessage(e));
    }
  };

  if (loading) {
    return (
      <div
        className="flex items-center justify-center h-96"
        data-testid="admin-exports-page"
      >
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-exports-page">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dışa Aktarımlar</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Match risk eşleşmeleriniz için planlı CSV export politikalarını yönetin ve geçmiş export arşivini buradan görüntüleyin.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-destructive text-sm">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="policies">Policies</TabsTrigger>
          <TabsTrigger value="archive">Archive</TabsTrigger>
        </TabsList>

        <TabsContent value="policies" className="mt-4">
          <div className="grid md:grid-cols-3 gap-6">
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle className="text-sm font-medium">Policies</CardTitle>
              </CardHeader>
              <CardContent>
                {policies.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    Henüz policy bulunamadı. Sağda yeni bir export policy oluşturabilirsiniz.
                  </p>
                ) : (
                  <div
                    className="overflow-x-auto"
                    data-testid="exports-policies-table"
                  >
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-xs text-muted-foreground">
                          <th className="py-1 pr-2 text-left">Key</th>
                          <th className="py-1 pr-2 text-left">Enabled</th>
                          <th className="py-1 pr-2 text-left">Schedule</th>
                          <th className="py-1 pr-2 text-left">Cooldown</th>
                        </tr>
                      </thead>
                      <tbody>
                        {policies.map((p) => (
                          <tr
                            key={p.key}
                            className={`border-b last:border-0 cursor-pointer ${
                              selectedKey === p.key ? "bg-muted" : "hover:bg-muted/60"
                            }`}
                            onClick={() => {
                              setSelectedKey(p.key);
                              applyPolicyToForm(p);
                            }}
                          >
                            <td className="py-1 pr-2 font-mono text-xs">{p.key}</td>
                            <td className="py-1 pr-2 text-xs">{p.enabled ? "Aktif" : "Kapalı"}</td>
                            <td className="py-1 pr-2 text-xs">{p.schedule_hint || "-"}</td>
                            <td className="py-1 pr-2 text-xs">{p.cooldown_hours}h</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Policy Formu</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-1">
                  <label className="text-sm font-medium" htmlFor="policy-key">
                    Key
                  </label>
                  <Input
                    id="policy-key"
                    value={form.key}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, key: e.target.value }))
                    }
                    disabled={!!selectedKey}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Aktif</span>
                  <Switch
                    checked={form.enabled}
                    onCheckedChange={(val) =>
                      setForm((prev) => ({ ...prev, enabled: Boolean(val) }))
                    }
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium" htmlFor="schedule-hint">
                    Schedule hint
                  </label>
                  <Input
                    id="schedule-hint"
                    placeholder="daily 09:00"
                    value={form.schedule_hint}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, schedule_hint: e.target.value }))
                    }
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium" htmlFor="cooldown-hours">
                    Cooldown (hours)
                  </label>
                  <Input
                    id="cooldown-hours"
                    type="number"
                    min="1"
                    max="168"
                    value={form.cooldown_hours}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        cooldown_hours: parseInt(e.target.value || "24", 10),
                      }))
                    }
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium" htmlFor="days">
                    Days
                  </label>
                  <Input
                    id="days"
                    type="number"
                    min="1"
                    max="365"
                    value={form.params.days}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        params: {
                          ...prev.params,
                          days: parseInt(e.target.value || "30", 10),
                        },
                      }))
                    }
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium" htmlFor="min-matches">
                    Min matches
                  </label>
                  <Input
                    id="min-matches"
                    type="number"
                    min="1"
                    value={form.params.min_matches}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        params: {
                          ...prev.params,
                          min_matches: parseInt(e.target.value || "1", 10),
                        },
                      }))
                    }
                  />
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Only high risk</span>
                  <Switch
                    checked={form.params.only_high_risk}
                    onCheckedChange={(val) =>
                      setForm((prev) => ({
                        ...prev,
                        params: {
                          ...prev.params,
                          only_high_risk: Boolean(val),
                        },
                      }))
                    }
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium" htmlFor="recipients">
                    Recipients (optional)
                  </label>
                  <Input
                    id="recipients"
                    placeholder="alerts@acenta.test, ops@acenta.test"
                    value={form.recipients}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, recipients: e.target.value }))
                    }
                  />
                </div>

                <div className="flex flex-wrap items-center gap-3 mt-2">
                  <Button
                    type="button"
                    onClick={handleSave}
                    disabled={saving}
                    data-testid="exports-policy-save"
                  >
                    {saving ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Kaydediliyor...
                      </>
                    ) : (
                      "Kaydet"
                    )}
                  </Button>

                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => handleRun(true)}
                    disabled={runLoading}
                    data-testid="exports-policy-run-dry"
                  >
                    Dry run
                  </Button>

                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      if (!window.confirm("Ger016ek export 0181al01310140131nacak ve archive'a yaz0131lacak. Devam?")
                      )
                        return;
                      handleRun(false);
                    }}
                    disabled={runLoading}
                    data-testid="exports-policy-run-now"
                  >
                    Run now
                  </Button>
                </div>

                {runDryResult && (
                  <div className="mt-3 text-xs text-muted-foreground">
                    <div>Rows: {runDryResult.rows}</div>
                    <div>Estimated size: {runDryResult.estimated_size_bytes} bytes</div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="archive" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Archive</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap items-end gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium" htmlFor="runs-policy-key">
                    Policy
                  </label>
                  <select
                    id="runs-policy-key"
                    className="border rounded px-2 py-1 text-sm bg-background"
                    value={runsPolicyKey}
                    onChange={(e) => {
                      const k = e.target.value;
                      setRunsPolicyKey(k);
                      loadRuns(k);
                    }}
                  >
                    <option value="">Se01a policy se0131n</option>
                    {policies.map((p) => (
                      <option key={p.key} value={p.key}>
                        {p.key}
                      </option>
                    ))}
                  </select>
                </div>

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => loadRuns(runsPolicyKey)}
                >
                  Yenile
                </Button>
              </div>

              {runsLoading ? (
                <p className="text-sm text-muted-foreground">Y01kleniyor...</p>
              ) : !runsPolicyKey ? (
                <p className="text-sm text-muted-foreground">
                  01nce bir policy se0131n.
                </p>
              ) : runs.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Hen0169 run bulunamad01.
                </p>
              ) : (
                <div
                  className="overflow-x-auto"
                  data-testid="exports-runs-table"
                >
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-xs text-muted-foreground">
                        <th className="py-1 pr-2 text-left">Generated at</th>
                        <th className="py-1 pr-2 text-left">Status</th>
                        <th className="py-1 pr-2 text-right">Rows (est)</th>
                        <th className="py-1 pr-2 text-right">Size</th>
                        <th className="py-1 pr-2 text-left">Filename</th>
                        <th className="py-1 pr-2 text-left">SHA</th>
                        <th className="py-1 pr-2 text-left">Emailed</th>
                        <th className="py-1 pr-2 text-left">Deeplink</th>
                        <th className="py-1 pr-2"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {runs.map((r) => {
                        const dateStr = r.generated_at
                          ? new Date(r.generated_at).toLocaleString()
                          : "";
                        const shaShort = r.sha256
                          ? r.sha256.slice(0, 10) + "..."
                          : "";
                        return (
                          <tr key={r.id} className="border-b last:border-0">
                            <td className="py-1 pr-2 text-xs">{dateStr}</td>
                            <td className="py-1 pr-2 text-xs">
                              <span
                                className={
                                  r.status === "ready"
                                    ? "text-emerald-600"
                                    : "text-red-600"
                                }
                              >
                                {r.status}
                              </span>
                            </td>
                            <td className="py-1 pr-2 text-right text-xs">
                              {/* rows sayısı backend'de yok; estimated size ile yetinelim */}
                              -
                            </td>
                            <td className="py-1 pr-2 text-right text-xs">
                              {r.size_bytes} B
                            </td>
                            <td className="py-1 pr-2 text-xs">{r.filename}</td>
                            <td className="py-1 pr-2 text-xs font-mono">{shaShort}</td>
                            <td className="py-1 pr-2 text-xs">
                              {r.emailed ? "Queued" : "—"}
                            </td>
                            <td className="py-1 pr-2 text-xs">
                              {r.type === "match_risk_summary" && runsDeeplinkTemplate ? (
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="outline"
                                  onClick={() => {
                                    const tpl = runsDeeplinkTemplate;
                                    const text = tpl.replace("{match_id}", "<match_id>");
                                    if (navigator.clipboard && navigator.clipboard.writeText) {
                                      navigator.clipboard.writeText(text);
                                    } else {
                                      const ta = document.createElement("textarea");
                                      ta.value = text;
                                      document.body.appendChild(ta);
                                      ta.select();
                                      document.execCommand("copy");
                                      document.body.removeChild(ta);
                                    }
                                    alert(`Template copied to clipboard: ${text}`);
                                  }}
                                  data-testid="exports-run-copy-deeplink-template"
                                >
                                  Copy deep link template
                                </Button>
                              ) : (
                                <span className="text-xs text-muted-foreground">-</span>
                              )}
                            </td>
                            <td className="py-1 pr-2 text-right">
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                onClick={() => handleDownload(r.id)}
                                data-testid="exports-run-download"
                              >
                                Download
                              </Button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
