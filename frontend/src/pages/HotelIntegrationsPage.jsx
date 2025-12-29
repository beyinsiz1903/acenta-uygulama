// HotelIntegrationsPage.jsx
import React, { useEffect, useMemo, useState } from "react";

import { api, apiErrorMessage } from "../lib/api";
import { useToast } from "../hooks/use-toast";

import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "../components/ui/sheet";

/**
 * Minimal, production-friendly Channel Hub page that restores:
 * - Connectors list + details
 * - Mappings editor (room/rate) + raw JSON (advanced)
 * - ARI Fetch (Debug)
 * - ARI Apply (Dry Run / Write) + diff viewer
 * - Runs history (ari_apply / ari_read etc.)
 * - Internal ARI Simulator panel:
 *    - rules list + refresh
 *    - simulate dry-run / write
 *    - reuse same "ARI Apply Result" panel format
 */

function safeJsonStringify(x, space = 2) {
  try {
    return JSON.stringify(x ?? {}, null, space);
  } catch {
    return "{}";
  }
}

function isoToday() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function isoPlusDays(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function statusBadge(status) {
  const s = String(status || "").toLowerCase();
  if (s === "success") return <Badge className="bg-emerald-600">success</Badge>;
  if (s === "partial") return <Badge className="bg-amber-600">partial</Badge>;
  if (s === "failed") return <Badge className="bg-red-600">failed</Badge>;
  if (s === "running") return <Badge className="bg-sky-600">running</Badge>;
  return <Badge variant="secondary">{status || "-"}</Badge>;
}

export default function HotelIntegrationsPage() {
  const { toast } = useToast();

  // global UI
  const [error, setError] = useState("");
  const [pageLoading, setPageLoading] = useState(false);

  // connectors
  const [connectors, setConnectors] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const selectedConnector = useMemo(
    () => connectors.find((c) => String(c?.id || c?._id || c?.connector_id || "") === String(selectedId)),
    [connectors, selectedId],
  );

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    provider: "exely",
    display_name: "",
    credentials_json: "{}",
    settings_json: "{}",
    capabilities_csv: "ARI_read,ARI_write",
  });
  const [createLoading, setCreateLoading] = useState(false);

  // mappings
  const [mappingsLoading, setMappingsLoading] = useState(false);
  const [roomRows, setRoomRows] = useState([]);
  const [rateRows, setRateRows] = useState([]);
  const [mappingsRaw, setMappingsRaw] = useState(null);
  const [mappingsRawText, setMappingsRawText] = useState("");

  const [saveMappingsLoading, setSaveMappingsLoading] = useState(false);
  const [saveMappingsError, setSaveMappingsError] = useState("");

  // connector test
  const [testLoading, setTestLoading] = useState(false);
  const [testResult, setTestResult] = useState(null);

  // ARI Fetch
  const [ariFromDate, setAriFromDate] = useState(isoToday());
  const [ariToDate, setAriToDate] = useState(isoPlusDays(2));
  const [ariLoading, setAriLoading] = useState(false);
  const [ariResult, setAriResult] = useState(null);
  const [ariError, setAriError] = useState(null);

  // ARI Apply
  const [ariApplyLoading, setAriApplyLoading] = useState(false);
  const [ariApplyResult, setAriApplyResult] = useState(null); // {ok,status,run_id,summary,diff,error}
  const [ariApplyError, setAriApplyError] = useState(null);

  // runs
  const [runsLoading, setRunsLoading] = useState(false);
  const [runs, setRuns] = useState([]);
  const [runsSheetOpen, setRunsSheetOpen] = useState(false);
  const [selectedRun, setSelectedRun] = useState(null);

  // Internal ARI
  const [internalRulesLoading, setInternalRulesLoading] = useState(false);
  const [internalRules, setInternalRules] = useState([]);
  const [internalSimLoading, setInternalSimLoading] = useState(false);
  const [internalSimResult, setInternalSimResult] = useState(null); // AriApplyOut
  const [internalSimError, setInternalSimError] = useState(null);

  // ---------- API helpers ----------

  async function loadConnectors() {
    setError("");
    setPageLoading(true);
    try {
      const resp = await api.get("/channels/connectors");
      const items = resp?.data?.items || resp?.data || [];
      setConnectors(Array.isArray(items) ? items : []);
      // auto select first
      const first = Array.isArray(items) && items.length ? items[0] : null;
      const firstId = String(first?.id || first?._id || first?.connector_id || "");
      if (!selectedId && firstId) setSelectedId(firstId);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setPageLoading(false);
    }
  }

  async function loadMappings(connectorId) {
    if (!connectorId) return;
    setSaveMappingsError("");
    setMappingsLoading(true);
    try {
      const resp = await api.get(`/channels/connectors/${connectorId}/mappings`);
      const doc = resp?.data || {};
      setMappingsRaw(doc);
      setMappingsRawText(safeJsonStringify(doc, 2));

      const room = doc?.room_type_mappings || doc?.roomTypeMappings || [];
      const rate = doc?.rate_plan_mappings || doc?.ratePlanMappings || [];

      setRoomRows(Array.isArray(room) ? room : []);
      setRateRows(Array.isArray(rate) ? rate : []);
    } catch (e) {
      setSaveMappingsError(apiErrorMessage(e));
      setMappingsRaw(null);
      setMappingsRawText("{}");
      setRoomRows([]);
      setRateRows([]);
    } finally {
      setMappingsLoading(false);
    }
  }

  async function saveMappings() {
    if (!selectedId) return;
    setSaveMappingsError("");
    setSaveMappingsLoading(true);
    setError("");
    try {
      const payload = {
        room_type_mappings: roomRows,
        rate_plan_mappings: rateRows,
      };
      await api.put(`/channels/connectors/${selectedId}/mappings`, payload);
      toast({ title: "Mappings kaydedildi", description: "Eşlemeler başarıyla güncellendi." });
      await loadMappings(selectedId);
    } catch (e) {
      const msg = apiErrorMessage(e);
      setSaveMappingsError(msg);
      toast({ title: "Mappings kaydedilemedi", description: msg, variant: "destructive" });
    } finally {
      setSaveMappingsLoading(false);
    }
  }

  async function handleTestConnection() {
    if (!selectedId) return;
    setError("");
    setTestResult(null);
    setTestLoading(true);
    try {
      const resp = await api.post(`/channels/connectors/${selectedId}/test`, {});
      setTestResult(resp?.data || {});
      toast({ title: "Test tamamlandı", description: resp?.data?.message || "Bağlantı test sonucu alındı." });
    } catch (e) {
      const msg = apiErrorMessage(e);
      toast({ title: "Test başarısız", description: msg, variant: "destructive" });
      setTestResult({ ok: false, message: msg, error: e?.response?.data || null });
    } finally {
      setTestLoading(false);
    }
  }

  async function loadRuns(connectorId) {
    if (!connectorId) return;
    setRunsLoading(true);
    try {
      // NOTE: Eğer sende farklıysa sadece burayı değiştiririz.
      const resp = await api.get(`/channels/connectors/${connectorId}/runs`, {
        params: { limit: 50 },
      });
      const items = resp?.data?.items || resp?.data || [];
      setRuns(Array.isArray(items) ? items : []);
    } catch (e) {
      // runs yoksa sayfayı kırmayalım
      setRuns([]);
    } finally {
      setRunsLoading(false);
    }
  }

  async function handleAriFetch() {
    if (!selectedId) return;
    setError("");
    setAriError(null);
    setAriResult(null);
    setAriLoading(true);
    try {
      const resp = await api.get(`/channels/connectors/${selectedId}/ari`, {
        params: { from_date: ariFromDate, to_date: ariToDate },
      });
      const payload = resp?.data || {};
      setAriResult(payload);
      toast({ title: "ARI Fetch tamamlandı", description: "ARI debug çıktısı alındı." });
    } catch (e) {
      setAriError(e);
      const status = e?.response?.status;
      const detail = e?.response?.data?.detail;
      const code = typeof detail === "object" && detail?.code ? String(detail.code) : "";
      let msg =
        (typeof detail === "object" && detail?.message) ||
        (typeof detail === "string" ? detail : apiErrorMessage(e));

      if (code === "CONFIG_ERROR") {
        msg =
          "Exely konfigürasyonu eksik: base_url tanımlı değil. (credentials.base_url veya settings.base_url)";
      }
      if (code === "PROVIDER_UNAVAILABLE") {
        msg = "Sağlayıcıya erişilemiyor veya geçici bir sorun var. Lütfen daha sonra tekrar deneyin.";
      }
      if (code === "TIMEOUT") {
        msg = "Sağlayıcıya yapılan ARI isteği zaman aşımına uğradı.";
      }
      if (status === 403 && code === "FEATURE_NOT_AVAILABLE") {
        msg = "Bu özellik paketinizde aktif değil. Paket yükseltmek için iletişime geçin.";
      }
      if (status === 403 && (code === "INSUFFICIENT_ROLE" || code === "NO_HOTEL_CONTEXT")) {
        msg = "Bu işlem için geçerli bir otel bağlamı ve yetki gerekiyor.";
      }

      setError(msg);
      toast({ title: "ARI Fetch başarısız", description: msg, variant: "destructive" });
    } finally {
      setAriLoading(false);
    }
  }

  async function handleAriApply(dryRun) {
    if (!selectedId) return;
    setError("");
    setAriApplyError(null);
    setAriApplyResult(null);
    setAriApplyLoading(true);
    try {
      const body = {
        from_date: ariFromDate, // "YYYY-MM-DD"
        to_date: ariToDate,
        mode: "rates_and_availability",
      };
      const resp = await api.post(`/channels/connectors/${selectedId}/ari/apply`, body, {
        params: { dry_run: dryRun ? 1 : 0 },
      });

      const payload = resp?.data || {};
      setAriApplyResult(payload);

      toast({
        title: dryRun ? "ARI Apply (Dry Run) çalıştırıldı" : "ARI Apply (Write) tamamlandı",
        description: payload?.status || payload?.summary?.status || "İşlem sonucu alındı.",
      });

      await loadRuns(selectedId);
    } catch (e) {
      setAriApplyError(e);
      const status = e?.response?.status;
      const detail = e?.response?.data?.detail;
      const code = typeof detail === "object" && detail?.code ? String(detail.code) : "";
      let msg =
        (typeof detail === "object" && detail?.message) ||
        (typeof detail === "string" ? detail : apiErrorMessage(e));

      if (code === "CONFIG_ERROR") {
        msg =
          "Exely konfigürasyonu eksik: base_url tanımlı değil. (credentials.base_url veya settings.base_url)";
      }
      if (code === "PROVIDER_UNAVAILABLE") {
        msg = "Sağlayıcıya erişilemiyor veya geçici bir sorun var. Lütfen daha sonra tekrar deneyin.";
      }
      if (code === "TIMEOUT") {
        msg = "Sağlayıcıya yapılan ARI isteği zaman aşımına uğradı.";
      }
      if (status === 403 && code === "FEATURE_NOT_AVAILABLE") {
        msg = "Bu özellik paketinizde aktif değil. Paket yükseltmek için iletişime geçin.";
      }
      if (status === 403 && (code === "INSUFFICIENT_ROLE" || code === "NO_HOTEL_CONTEXT")) {
        msg = "Bu işlem için geçerli bir otel bağlamı ve hotel_admin yetkisi gerekiyor.";
      }

      setError(msg);
      toast({ title: "ARI Apply başarısız", description: msg, variant: "destructive" });
    } finally {
      setAriApplyLoading(false);
    }
  }

  async function loadInternalRules() {
    setInternalRulesLoading(true);
    setError("");
    try {
      const resp = await api.get("/internal-ari/rules");
      const items = resp?.data?.items || resp?.data || [];
      setInternalRules(Array.isArray(items) ? items : []);
      toast({ title: "Internal ARI kuralları yüklendi", description: `${Array.isArray(items) ? items.length : 0} kural` });
    } catch (e) {
      const msg = apiErrorMessage(e);
      setError(msg);
      toast({ title: "Kurallar yüklenemedi", description: msg, variant: "destructive" });
      setInternalRules([]);
    } finally {
      setInternalRulesLoading(false);
    }
  }

  async function handleInternalSimulate(dryRun) {
    setInternalSimError(null);
    setInternalSimResult(null);
    setError("");
    setInternalSimLoading(true);
    try {
      const body = { from_date: ariFromDate, to_date: ariToDate };
      const resp = await api.post("/internal-ari/simulate", body, { params: { dry_run: dryRun ? 1 : 0 } });
      const payload = resp?.data || {};
      setInternalSimResult(payload);

      // Internal sim sonucu AriApplyOut formatında; ana ARI Apply panelini reuse etmek için de kullanabilirsin.
      setAriApplyResult(payload);

      toast({
        title: dryRun ? "Internal Simulate (Dry Run)" : "Internal Simulate (Write)",
        description: payload?.status || "Simülasyon sonucu alındı.",
      });

      // runs listesi internal_ari için connector runs endpoint'ine bağlı olabilir;
      // en azından selected connector runs'ı refresh edelim.
      if (selectedId) await loadRuns(selectedId);
    } catch (e) {
      setInternalSimError(e);
      const msg = apiErrorMessage(e);
      setError(msg);
      toast({ title: "Internal simulate başarısız", description: msg, variant: "destructive" });
    } finally {
      setInternalSimLoading(false);
    }
  }

  async function handleCreateConnector() {
    setCreateLoading(true);
    setError("");
    try {
      const credentials = JSON.parse(createForm.credentials_json || "{}");
      const settings = JSON.parse(createForm.settings_json || "{}");
      const capabilities = (createForm.capabilities_csv || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      const body = {
        provider: createForm.provider,
        display_name: createForm.display_name || `${createForm.provider} connector`,
        credentials,
        settings,
        capabilities,
      };

      const resp = await api.post("/channels/connectors", body);
      const created = resp?.data || null;

      toast({ title: "Connector oluşturuldu", description: created?.display_name || "Yeni connector eklendi." });
      setCreateOpen(false);
      setCreateForm({
        provider: "exely",
        display_name: "",
        credentials_json: "{}",
        settings_json: "{}",
        capabilities_csv: "ARI_read,ARI_write",
      });

      await loadConnectors();
    } catch (e) {
      const msg = apiErrorMessage(e);
      setError(msg);
      toast({ title: "Connector oluşturulamadı", description: msg, variant: "destructive" });
    } finally {
      setCreateLoading(false);
    }
  }

  // ---------- effects ----------

  useEffect(() => {
    loadConnectors();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    loadMappings(selectedId);
    loadRuns(selectedId);
    setTestResult(null);
    setAriResult(null);
    setAriError(null);
    setAriApplyResult(null);
    setAriApplyError(null);
  }, [selectedId]);

  // ---------- mapping row helpers ----------

  function addRoomRow() {
    setRoomRows((prev) => [
      ...prev,
      {
        pms_room_type_id: "",
        channel_room_type_id: "",
        channel_room_name: "",
        active: true,
      },
    ]);
  }

  function addRateRow() {
    setRateRows((prev) => [
      ...prev,
      {
        pms_rate_plan_id: "",
        channel_rate_plan_id: "",
        channel_rate_name: "",
        active: true,
      },
    ]);
  }

  function updateRow(setter, idx, key, value) {
    setter((prev) => {
      const copy = [...prev];
      copy[idx] = { ...(copy[idx] || {}), [key]: value };
      return copy;
    });
  }

  function removeRow(setter, idx) {
    setter((prev) => prev.filter((_, i) => i !== idx));
  }

  const activeInternalRules = useMemo(
    () => (internalRules || []).filter((r) => r?.active),
    [internalRules],
  );

  // ---------- UI ----------

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xl font-semibold">Channel Hub • Entegrasyonlar</div>
          <div className="text-sm text-muted-foreground">
            Connector yönetimi, mapping, ARI debug/apply ve Internal ARI Simulator.
          </div>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" onClick={loadConnectors} disabled={pageLoading}>
            {pageLoading ? "Yükleniyor..." : "Yenile"}
          </Button>

          <Button onClick={() => setCreateOpen(true)}>Yeni Connector</Button>

          <Button
            variant="outline"
            onClick={() => setRunsSheetOpen(true)}
            disabled={!selectedId}
          >
            Runs
          </Button>
        </div>
      </div>

      {error ? (
        <div className="border border-red-200 bg-red-50 text-red-700 rounded-md p-3 text-sm">
          {error}
        </div>
      ) : null}

      {/* Main layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: connectors list */}
        <div className="border rounded-md p-3 bg-background">
          <div className="flex items-center justify-between">
            <div className="font-medium">Connectors</div>
            <div className="text-xs text-muted-foreground">{connectors.length} adet</div>
          </div>

          <div className="mt-2 space-y-2">
            {connectors.length === 0 ? (
              <div className="text-sm text-muted-foreground">
                Henüz connector yok. &quot;Yeni Connector&quot; ile ekleyebilirsin.
              </div>
            ) : (
              connectors.map((c) => {
                const id = String(c?.id || c?._id || c?.connector_id || "");
                const name = c?.display_name || c?.name || c?.provider || id;
                const provider = c?.provider || "-";
                const caps = Array.isArray(c?.capabilities) ? c.capabilities : [];
                const isSelected = String(selectedId) === String(id);

                return (
                  <button
                    key={id}
                    type="button"
                    className={[
                      "w-full text-left rounded-md border p-2 transition",
                      isSelected ? "border-primary bg-muted/50" : "hover:bg-muted/40",
                    ].join(" ")}
                    onClick={() => setSelectedId(id)}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="font-medium text-sm">{name}</div>
                      <Badge variant="secondary" className="text-[10px]">
                        {provider}
                      </Badge>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {caps.slice(0, 4).map((x) => (
                        <Badge key={x} variant="outline" className="text-[10px]">
                          {x}
                        </Badge>
                      ))}
                      {caps.length > 4 ? (
                        <span className="text-[10px] text-muted-foreground">+{caps.length - 4}</span>
                      ) : null}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right: details + mappings + ARI */}
        <div className="lg:col-span-2 space-y-4">
          {/* Connector details */}
          <div className="border rounded-md p-3 bg-background">
            <div className="flex items-center justify-between gap-2">
              <div className="font-medium">Connector Detayı</div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleTestConnection}
                  disabled={!selectedId || testLoading}
                >
                  {testLoading ? "Test..." : "Bağlantıyı Test Et"}
                </Button>
              </div>
            </div>

            {!selectedId ? (
              <div className="mt-2 text-sm text-muted-foreground">Bir connector seç.</div>
            ) : (
              <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="text-sm space-y-1">
                  <div>
                    <span className="font-semibold">ID:</span>{" "}
                    <span className="font-mono text-xs">{selectedId}</span>
                  </div>
                  <div>
                    <span className="font-semibold">Provider:</span> {selectedConnector?.provider || "-"}
                  </div>
                  <div>
                    <span className="font-semibold">Display:</span> {selectedConnector?.display_name || "-"}
                  </div>
                  <div>
                    <span className="font-semibold">Capabilities:</span>{" "}
                    {(selectedConnector?.capabilities || []).join(", ") || "-"}
                  </div>
                </div>

                <div className="text-sm">
                  <div className="font-semibold mb-1">Test Sonucu</div>
                  <div className="border rounded-md p-2 bg-muted/30 text-xs">
                    <pre className="whitespace-pre-wrap break-words">
                      {testResult ? safeJsonStringify(testResult, 2) : "Henüz test çalıştırılmadı."}
                    </pre>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Mappings */}
          <div className="border rounded-md p-3 bg-background">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="font-medium">Mappings</div>
                <div className="text-xs text-muted-foreground">
                  Channel ID → PMS ID eşlemeleri. Kaydedince backend&apos;de aktif olur.
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => selectedId && loadMappings(selectedId)}
                  disabled={!selectedId || mappingsLoading}
                >
                  {mappingsLoading ? "Yükleniyor..." : "Yenile"}
                </Button>
                <Button
                  size="sm"
                  onClick={saveMappings}
                  disabled={!selectedId || saveMappingsLoading}
                >
                  {saveMappingsLoading ? "Kaydediliyor..." : "Kaydet"}
                </Button>
              </div>
            </div>

            {saveMappingsError ? (
              <div className="mt-2 text-xs text-red-600">{saveMappingsError}</div>
            ) : null}

            <div className="mt-3 grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Rooms mapping table */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-sm">Room Type Mappings</div>
                  <Button variant="outline" size="sm" onClick={addRoomRow} disabled={!selectedId}>
                    + Ekle
                  </Button>
                </div>

                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[140px]">PMS Room ID</TableHead>
                      <TableHead className="w-[140px]">Channel Room ID</TableHead>
                      <TableHead>Ad</TableHead>
                      <TableHead className="w-[70px]">Aktif</TableHead>
                      <TableHead className="w-[60px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {roomRows.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="text-xs text-muted-foreground">
                          Henüz room mapping yok.
                        </TableCell>
                      </TableRow>
                    ) : (
                      roomRows.map((r, idx) => (
                        <TableRow key={`room-${idx}`}>
                          <TableCell>
                            <Input
                              value={r?.pms_room_type_id || ""}
                              onChange={(e) => updateRow(setRoomRows, idx, "pms_room_type_id", e.target.value)}
                              placeholder="rt_1"
                            />
                          </TableCell>
                          <TableCell>
                            <Input
                              value={r?.channel_room_type_id || ""}
                              onChange={(e) => updateRow(setRoomRows, idx, "channel_room_type_id", e.target.value)}
                              placeholder="ch_rt_1"
                            />
                          </TableCell>
                          <TableCell>
                            <Input
                              value={r?.channel_room_name || ""}
                              onChange={(e) => updateRow(setRoomRows, idx, "channel_room_name", e.target.value)}
                              placeholder="STD"
                            />
                          </TableCell>
                          <TableCell>
                            <Input
                              type="checkbox"
                              className="h-4 w-4"
                              checked={Boolean(r?.active ?? true)}
                              onChange={(e) => updateRow(setRoomRows, idx, "active", e.target.checked)}
                            />
                          </TableCell>
                          <TableCell>
                            <Button variant="outline" size="sm" onClick={() => removeRow(setRoomRows, idx)}>
                              Sil
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Rates mapping table */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-sm">Rate Plan Mappings</div>
                  <Button variant="outline" size="sm" onClick={addRateRow} disabled={!selectedId}>
                    + Ekle
                  </Button>
                </div>

                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[140px]">PMS Rate ID</TableHead>
                      <TableHead className="w-[140px]">Channel Rate ID</TableHead>
                      <TableHead>Ad</TableHead>
                      <TableHead className="w-[70px]">Aktif</TableHead>
                      <TableHead className="w-[60px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rateRows.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="text-xs text-muted-foreground">
                          Henüz rate mapping yok.
                        </TableCell>
                      </TableRow>
                    ) : (
                      rateRows.map((r, idx) => (
                        <TableRow key={`rate-${idx}`}>
                          <TableCell>
                            <Input
                              value={r?.pms_rate_plan_id || ""}
                              onChange={(e) => updateRow(setRateRows, idx, "pms_rate_plan_id", e.target.value)}
                              placeholder="rp_1"
                            />
                          </TableCell>
                          <TableCell>
                            <Input
                              value={r?.channel_rate_plan_id || ""}
                              onChange={(e) => updateRow(setRateRows, idx, "channel_rate_plan_id", e.target.value)}
                              placeholder="ch_rp_1"
                            />
                          </TableCell>
                          <TableCell>
                            <Input
                              value={r?.channel_rate_name || ""}
                              onChange={(e) => updateRow(setRateRows, idx, "channel_rate_name", e.target.value)}
                              placeholder="BAR"
                            />
                          </TableCell>
                          <TableCell>
                            <Input
                              type="checkbox"
                              className="h-4 w-4"
                              checked={Boolean(r?.active ?? true)}
                              onChange={(e) => updateRow(setRateRows, idx, "active", e.target.checked)}
                            />
                          </TableCell>
                          <TableCell>
                            <Button variant="outline" size="sm" onClick={() => removeRow(setRateRows, idx)}>
                              Sil
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>

            {/* Advanced raw */}
            <div className="mt-3">
              <details>
                <summary className="cursor-pointer select-none text-sm">
                  Advanced (raw mappings JSON)
                </summary>
                <Textarea
                  className="mt-2"
                  rows={10}
                  value={mappingsRawText}
                  onChange={(e) => setMappingsRawText(e.target.value)}
                />
                <div className="mt-2 flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      try {
                        const doc = JSON.parse(mappingsRawText || "{}");
                        setMappingsRaw(doc);
                        setRoomRows(Array.isArray(doc?.room_type_mappings) ? doc.room_type_mappings : []);
                        setRateRows(Array.isArray(doc?.rate_plan_mappings) ? doc.rate_plan_mappings : []);
                        toast({ title: "Raw JSON parse OK", description: "Grid state güncellendi." });
                      } catch (e) {
                        toast({ title: "JSON parse hatası", description: String(e?.message || e), variant: "destructive" });
                      }
                    }}
                  >
                    JSON → Grid
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const doc = {
                        room_type_mappings: roomRows,
                        rate_plan_mappings: rateRows,
                      };
                      setMappingsRaw(doc);
                      setMappingsRawText(safeJsonStringify(doc, 2));
                      toast({ title: "Grid → JSON", description: "Raw JSON güncellendi." });
                    }}
                  >
                    Grid → JSON
                  </Button>
                </div>
              </details>
            </div>
          </div>

          {/* ARI Controls */}
          <div className="border rounded-md p-3 bg-background">
            <div className="font-medium">ARI</div>
            <div className="text-xs text-muted-foreground">
              Debug fetch + apply (dry-run / write). Tarih aralığını seçip çalıştır.
            </div>

            <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <Label>From</Label>
                <Input value={ariFromDate} onChange={(e) => setAriFromDate(e.target.value)} placeholder="YYYY-MM-DD" />
              </div>
              <div>
                <Label>To</Label>
                <Input value={ariToDate} onChange={(e) => setAriToDate(e.target.value)} placeholder="YYYY-MM-DD" />
              </div>
              <div className="flex items-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  type="button"
                  onClick={handleAriFetch}
                  disabled={!selectedId || ariLoading || ariApplyLoading}
                >
                  {ariLoading ? "Çekiliyor..." : "ARI Fetch (Debug)"}
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  type="button"
                  onClick={() => handleAriApply(true)}
                  disabled={!selectedId || ariApplyLoading}
                >
                  {ariApplyLoading ? "Apply..." : "ARI Apply (Dry Run)"}
                </Button>

                <Button
                  variant="destructive"
                  size="sm"
                  type="button"
                  onClick={() => {
                    if (!selectedId || ariApplyLoading) return;
                    if (
                      window.confirm(
                        "ARI Apply (Write) PMS verilerini günceller ve geri alınamaz olabilir. Emin misiniz?",
                      )
                    ) {
                      handleAriApply(false);
                    }
                  }}
                  disabled={!selectedId || ariApplyLoading}
                >
                  ARI Apply (Write)
                </Button>
              </div>
            </div>

            {ariApplyResult ? (
              <div className="mt-2 text-[11px] text-muted-foreground">
                Son Apply Run: <span className="font-mono">{ariApplyResult.run_id}</span>{" "}
                (
                <span
                  className={
                    ariApplyResult.status === "success"
                      ? "text-emerald-600"
                      : ariApplyResult.status === "partial"
                      ? "text-amber-600"
                      : "text-red-600"
                  }
                >
                  {ariApplyResult.status}
                </span>
                )
              </div>
            ) : null}

            {/* ARI Fetch result */}
            <div className="mt-3">
              <details open={false}>
                <summary className="cursor-pointer select-none text-sm">Son ARI Sonucu (Debug JSON)</summary>
                <div className="mt-2 border rounded-md bg-muted/30 p-2 text-xs">
                  <pre className="whitespace-pre-wrap break-words">
                    {ariResult ? safeJsonStringify(ariResult, 2) : ariError ? "ARI Fetch hata aldı." : "Henüz fetch yok."}
                  </pre>
                </div>
              </details>
            </div>

            {/* ARI Apply result panel */}
            {ariApplyResult ? (
              <div className="mt-3 space-y-1 text-xs border rounded-md p-2 bg-muted/40">
                <div className="font-medium">Son ARI Apply Sonucu</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <div>
                    <div>
                      <span className="font-semibold">Status:</span> {ariApplyResult.status}
                    </div>
                    <div>
                      <span className="font-semibold">Run ID:</span> {ariApplyResult.run_id}
                    </div>
                    <div>
                      <span className="font-semibold">OK:</span> {String(ariApplyResult.ok)}
                    </div>
                    {ariApplyResult.error ? (
                      <div className="mt-1 text-red-600">
                        <span className="font-semibold">Hata:</span>{" "}
                        {ariApplyResult.error.code} — {ariApplyResult.error.message}
                      </div>
                    ) : null}

                    <div className="mt-1 grid grid-cols-2 gap-1">
                      <div>
                        <span className="font-semibold">changed_prices:</span>{" "}
                        {ariApplyResult.summary?.changed_prices ?? 0}
                      </div>
                      <div>
                        <span className="font-semibold">changed_avail:</span>{" "}
                        {ariApplyResult.summary?.changed_availability ?? 0}
                      </div>
                      <div>
                        <span className="font-semibold">unmapped_rooms:</span>{" "}
                        {ariApplyResult.summary?.unmapped_rooms ?? 0}
                      </div>
                      <div>
                        <span className="font-semibold">unmapped_rates:</span>{" "}
                        {ariApplyResult.summary?.unmapped_rates ?? 0}
                      </div>
                    </div>

                    <details className="mt-2">
                      <summary className="cursor-pointer select-none">Advanced Summary</summary>
                      <div className="mt-1 border rounded-md p-2 bg-background">
                        <pre className="whitespace-pre-wrap break-words">
                          {safeJsonStringify(ariApplyResult.summary || {}, 2)}
                        </pre>
                      </div>
                    </details>
                  </div>

                  <div>
                    <details className="mt-1">
                      <summary className="cursor-pointer select-none">Advanced (diff)</summary>
                      <Textarea
                        className="mt-1"
                        rows={10}
                        value={safeJsonStringify(ariApplyResult.diff ?? {}, 2)}
                        readOnly
                      />
                    </details>
                  </div>
                </div>
              </div>
            ) : ariApplyError ? (
              <div className="mt-2 text-xs text-red-600">ARI Apply sırasında bir hata oluştu.</div>
            ) : null}
          </div>

          {/* Internal ARI Simulator panel */}
          <div className="border rounded-md p-3 bg-background">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="font-medium">Internal ARI Simulator</div>
                <div className="text-xs text-muted-foreground">
                  Acentesiz ortamda rule&apos;larla ARI üretip (dry-run / write) apply pipeline&apos;ını test et.
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={loadInternalRules}
                  disabled={internalRulesLoading}
                >
                  {internalRulesLoading ? "Yükleniyor..." : "Kuralları Yenile"}
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleInternalSimulate(true)}
                  disabled={internalSimLoading}
                >
                  {internalSimLoading ? "Sim..." : "Simulate (Dry Run)"}
                </Button>

                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    if (internalSimLoading) return;
                    if (
                      window.confirm(
                        "Internal Simulate (Write) PMS snapshot'ını günceller. Emin misiniz?",
                      )
                    ) {
                      handleInternalSimulate(false);
                    }
                  }}
                  disabled={internalSimLoading}
                >
                  Simulate (Write)
                </Button>
              </div>
            </div>

            <div className="mt-2 text-xs text-muted-foreground">
              Aktif kural: <span className="font-semibold">{activeInternalRules.length}</span> /{" "}
              {internalRules.length}
            </div>

            <div className="mt-2">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ad</TableHead>
                    <TableHead className="w-[90px]">Scope</TableHead>
                    <TableHead className="w-[80px]">Aktif</TableHead>
                    <TableHead className="w-[220px]">Date Rule</TableHead>
                    <TableHead className="w-[220px]">Rate / Avail</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {internalRules.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-xs text-muted-foreground">
                        Kural yok veya henüz yüklenmedi. &quot;Kuralları Yenile&quot; ile çek.
                      </TableCell>
                    </TableRow>
                  ) : (
                    internalRules.slice(0, 10).map((r) => (
                      <TableRow key={String(r?.id || r?._id || Math.random())}>
                        <TableCell className="text-sm">
                          <div className="font-medium">{r?.name || "-"}</div>
                          <div className="text-xs text-muted-foreground">
                            {String(r?.updated_at || r?.created_at || "")}
                          </div>
                        </TableCell>
                        <TableCell className="text-xs">{r?.scope || "-"}</TableCell>
                        <TableCell className="text-xs">
                          {r?.active ? <Badge className="bg-emerald-600">active</Badge> : <Badge variant="secondary">off</Badge>}
                        </TableCell>
                        <TableCell className="text-xs">
                          {r?.date_rule
                            ? `${r.date_rule.type || "-"} ${r.date_rule.from_date ? `(${r.date_rule.from_date}..${r.date_rule.to_date || ""})` : ""}`
                            : "-"}
                        </TableCell>
                        <TableCell className="text-xs">
                          <div>
                            <span className="font-semibold">rate:</span>{" "}
                            {r?.rate_rule ? `${r.rate_rule.type}:${r.rate_rule.value}` : "-"}
                          </div>
                          <div>
                            <span className="font-semibold">avail:</span>{" "}
                            {r?.availability_rule ? `${r.availability_rule.type}:${r.availability_rule.value}` : "-"}
                          </div>
                          <div>
                            <span className="font-semibold">stop_sell:</span>{" "}
                            {typeof r?.stop_sell === "boolean" ? String(r.stop_sell) : "-"}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>

              {internalSimResult ? (
                <div className="mt-3 text-xs border rounded-md p-2 bg-muted/40">
                  <div className="font-medium">Son Internal Simulate Sonucu</div>
                  <div className="mt-1">
                    <span className="font-semibold">Status:</span>{" "}
                    <span className="font-mono">{internalSimResult.status}</span>{" "}
                    {statusBadge(internalSimResult.status)}
                  </div>
                  <div className="mt-1">
                    <span className="font-semibold">Run ID:</span>{" "}
                    <span className="font-mono">{internalSimResult.run_id}</span>
                  </div>

                  <details className="mt-2">
                    <summary className="cursor-pointer select-none">Advanced (summary + diff)</summary>
                    <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2">
                      <div className="border rounded-md p-2 bg-background">
                        <div className="font-semibold mb-1">summary</div>
                        <pre className="whitespace-pre-wrap break-words">
                          {safeJsonStringify(internalSimResult.summary || {}, 2)}
                        </pre>
                      </div>
                      <div className="border rounded-md p-2 bg-background">
                        <div className="font-semibold mb-1">diff</div>
                        <pre className="whitespace-pre-wrap break-words">
                          {safeJsonStringify(internalSimResult.diff || {}, 2)}
                        </pre>
                      </div>
                    </div>
                  </details>
                </div>
              ) : internalSimError ? (
                <div className="mt-2 text-xs text-red-600">Internal simulate sırasında hata oluştu.</div>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      {/* Create connector dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Yeni Connector</DialogTitle>
            <DialogDescription>
              Provider + credentials/settings JSON ile connector oluştur.
            </DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <Label>Provider</Label>
              <Input
                value={createForm.provider}
                onChange={(e) => setCreateForm((p) => ({ ...p, provider: e.target.value }))}
                placeholder="exely | mock_ari | internal_ari ..."
              />
            </div>
            <div>
              <Label>Display Name</Label>
              <Input
                value={createForm.display_name}
                onChange={(e) => setCreateForm((p) => ({ ...p, display_name: e.target.value }))}
                placeholder="Exely - Canyon"
              />
            </div>

            <div className="md:col-span-2">
              <Label>Capabilities (CSV)</Label>
              <Input
                value={createForm.capabilities_csv}
                onChange={(e) => setCreateForm((p) => ({ ...p, capabilities_csv: e.target.value }))}
                placeholder="ARI_read,ARI_write"
              />
            </div>

            <div className="md:col-span-2">
              <Label>Credentials (JSON)</Label>
              <Textarea
                rows={6}
                value={createForm.credentials_json}
                onChange={(e) => setCreateForm((p) => ({ ...p, credentials_json: e.target.value }))}
              />
            </div>

            <div className="md:col-span-2">
              <Label>Settings (JSON)</Label>
              <Textarea
                rows={6}
                value={createForm.settings_json}
                onChange={(e) => setCreateForm((p) => ({ ...p, settings_json: e.target.value }))}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              İptal
            </Button>
            <Button onClick={handleCreateConnector} disabled={createLoading}>
              {createLoading ? "Oluşturuluyor..." : "Oluştur"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Runs sheet */}
      <Sheet open={runsSheetOpen} onOpenChange={setRunsSheetOpen}>
        <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Runs</SheetTitle>
            <SheetDescription>
              Son run kayıtları. (Connector seçiliyse o connector&apos;a ait)
            </SheetDescription>
          </SheetHeader>

          <div className="mt-3 flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => selectedId && loadRuns(selectedId)}
              disabled={!selectedId || runsLoading}
            >
              {runsLoading ? "Yükleniyor..." : "Yenile"}
            </Button>
          </div>

          <div className="mt-3">
            {runs.length === 0 ? (
              <div className="text-sm text-muted-foreground">Run kaydı yok veya endpoint farklı.</div>
            ) : (
              <div className="space-y-2">
                {runs.map((r) => {
                  const rid = String(r?.id || r?._id || "");
                  return (
                    <button
                      key={rid}
                      type="button"
                      className="w-full text-left border rounded-md p-2 hover:bg-muted/40"
                      onClick={() => setSelectedRun(r)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="font-mono text-xs">{rid}</div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-[10px]">
                            {r?.type || "-"}
                          </Badge>
                          {statusBadge(r?.status)}
                        </div>
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {String(r?.started_at || "")} • {String(r?.duration_ms ?? "")}ms
                      </div>
                      <div className="mt-1 text-xs">
                        connector_id: <span className="font-mono">{String(r?.connector_id || "")}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {selectedRun ? (
            <div className="mt-4 border rounded-md p-2 bg-muted/30">
              <div className="font-medium text-sm">Run Detayı</div>
              <div className="mt-2 text-xs">
                <div>
                  <span className="font-semibold">Status:</span> {String(selectedRun?.status || "-")}
                </div>
                <div>
                  <span className="font-semibold">Type:</span> {String(selectedRun?.type || "-")}
                </div>
                <div className="mt-2">
                  <details>
                    <summary className="cursor-pointer select-none">summary</summary>
                    <pre className="mt-2 whitespace-pre-wrap break-words">
                      {safeJsonStringify(selectedRun?.summary || {}, 2)}
                    </pre>
                  </details>
                </div>
                <div className="mt-2">
                  <details>
                    <summary className="cursor-pointer select-none">diff</summary>
                    <pre className="mt-2 whitespace-pre-wrap break-words">
                      {safeJsonStringify(selectedRun?.diff || {}, 2)}
                    </pre>
                  </details>
                </div>
              </div>
            </div>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}