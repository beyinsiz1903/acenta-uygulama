import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Phone, MessageCircle, Mail, ArrowRight, RefreshCw, Search } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "../components/ui/sheet";
import { Textarea } from "../components/ui/textarea";
import { Switch } from "../components/ui/switch";
import { useToast } from "../hooks/use-toast";

const IDLE_PRESETS = [
  { key: "all", label: "Tümü" },
  { key: "3", label: ">= 3g" },
  { key: "7", label: ">= 7g" },
  { key: "14", label: ">= 14g" },
  { key: "30", label: ">= 30g" },
];

const FILTER_PRESETS = [
  { key: "all", label: "Hepsi" },
  { key: "callback", label: "Callback" },
  { key: "overdue", label: "Overdue" },
  { key: "due_today", label: "Bugün" },
  { key: "idle", label: "Idle" },
];

function normalizePhone(raw) {
  const digits = String(raw || "").replace(/[^0-9+]/g, "");
  if (!digits) return "";
  if (digits.startsWith("+")) return digits;
  // 10 haneli TR numara ise +90 ekle
  const onlyDigits = digits.replace(/[^0-9]/g, "");
  if (onlyDigits.length === 10) return "+90" + onlyDigits;
  return digits;
}

function formatDateTr(iso) {
  if (!iso) return "-";
  try {
    const d = new Date(iso);
    const day = String(d.getUTCDate()).padStart(2, "0");
    const month = String(d.getUTCMonth() + 1).padStart(2, "0");
    const year = d.getUTCFullYear();
    return `${day}.${month}.${year}`;
  } catch {
    return iso;
  }
}

export default function AgencyCrmFollowupsPage() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [idlePreset, setIdlePreset] = useState("7");
  const [filterPreset, setFilterPreset] = useState("all");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  const [cursor, setCursor] = useState(null);
  const [items, setItems] = useState([]);
  const [meta, setMeta] = useState({ days_idle: 7, due_until: null, count: 0, next_cursor: null });
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  const [actionableOnly, setActionableOnly] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [activeTab, setActiveTab] = useState("note");

  const [noteSubject, setNoteSubject] = useState("");
  const [noteBody, setNoteBody] = useState("");

  const [callOutcome, setCallOutcome] = useState("callback");
  const [callSubject, setCallSubject] = useState("Arama");
  const [callBody, setCallBody] = useState("");

  const [taskTitle, setTaskTitle] = useState("");
  const [taskDueDate, setTaskDueDate] = useState("");
  const [taskAssignee, setTaskAssignee] = useState("");

  const [saving, setSaving] = useState(false);

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedSearch(search.trim());
    }, 350);
    return () => clearTimeout(t);
  }, [search]);

  async function fetchFollowups({ append = false, nextCursor = null } = {}) {
    const isLoadMore = append && nextCursor;
    if (isLoadMore) {
      setLoadingMore(true);
    } else {
      setLoading(true);
    }
    setError("");

    try {
      const params = {
        scope: "agency",
        limit: 25,
      };
      if (nextCursor) params.cursor = nextCursor;
      if (debouncedSearch) params.q = debouncedSearch;

      const res = await api.get("/crm/follow-ups", { params });
      const data = res.data || {};
      const newItems = Array.isArray(data.items) ? data.items : [];
      const merged = append ? [...items, ...newItems] : newItems;

      setItems(merged);
      setMeta({
        days_idle: data.meta?.days_idle ?? 7,
        due_until: data.meta?.due_until ?? null,
        count: Array.isArray(newItems) ? newItems.length : 0,
        next_cursor: data.next_cursor ?? null,
      });
      setCursor(data.next_cursor ?? null);
    } catch (err) {
      const msg = apiErrorMessage(err);
      setError(msg);
      toast({
        title: "CRM Follow-ups",
        description: msg,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }

  useEffect(() => {
    // İlk yük + search değiştiğinde full reload
    fetchFollowups({ append: false, nextCursor: null });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch]);

  const idleThreshold = useMemo(() => {
    if (idlePreset === "all") return null;
    const n = parseInt(idlePreset, 10);
    return Number.isFinite(n) ? n : null;
  }, [idlePreset]);

  const filteredItems = useMemo(() => {
    return (items || []).filter((it) => {
      const s = it.signals || {};
      const idle = typeof s.idle_days === "number" ? s.idle_days : null;
      const overdue = Number(s.overdue || 0);
      const dueToday = Number(s.due_today || 0);
      const reason = it.suggested_action?.reason;

      // Idle filter
      if (idleThreshold != null) {
        if (idle == null || idle < idleThreshold) {
          return false;
        }
      }

      // Status filter
      switch (filterPreset) {
        case "callback":
          return reason === "callback";
        case "overdue":
          return overdue > 0;
        case "due_today":
          return dueToday > 0;
        case "idle":
          return idle != null && idle >= 7 && !["callback", "overdue", "due_today"].includes(reason || "");
        default:
          return true;
      }
    });
  }, [items, filterPreset, idleThreshold]);

  function handleRefresh() {
    setCursor(null);
    fetchFollowups({ append: false, nextCursor: null });
  }

  function handleLoadMore() {
    if (!cursor) return;
    fetchFollowups({ append: true, nextCursor: cursor });
  }

  return (
    <div className="space-y-4" data-testid="crm-followups-page">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">CRM Takip Masası</h2>
          <p className="text-sm text-muted-foreground">
            Callback, overdue ve idle otelleri tek ekranda yönetin.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={loading}
            className="gap-2"
            data-testid="followups-refresh"
          >
            {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Yenile
          </Button>
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive" data-testid="followups-error">
          {error}
        </div>
      ) : null}

      <Card className="rounded-2xl shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Filtreler</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-1 flex-col gap-2 sm:flex-row sm:items-center">
              <div className="relative w-full sm:w-64">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  data-testid="followups-search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Otel adı / şehir / telefon ara"
                  className="pl-8 h-9 text-sm"
                />
              </div>

              <div className="flex gap-2">
                <Select value={idlePreset} onValueChange={setIdlePreset}>
                  <SelectTrigger className="h-9 w-28 text-xs" data-testid="followups-idle-select">
                    <SelectValue placeholder="Idle süresi" />
                  </SelectTrigger>
                  <SelectContent>
                    {IDLE_PRESETS.map((opt) => (
                      <SelectItem key={opt.key} value={opt.key} className="text-xs">
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={filterPreset} onValueChange={setFilterPreset}>
                  <SelectTrigger className="h-9 w-28 text-xs" data-testid="followups-filter-select">
                    <SelectValue placeholder="Durum" />
                  </SelectTrigger>
                  <SelectContent>
                    {FILTER_PRESETS.map((opt) => (
                      <SelectItem key={opt.key} value={opt.key} className="text-xs">
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="text-xs text-muted-foreground">
              {meta?.count ?? 0} kayıt (sayfa)  b7 Due until: {meta?.due_until || "-"}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-2">
        {filteredItems.length === 0 && !loading ? (
          <Card className="rounded-2xl border-dashed bg-muted/40">
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              Aktif follow-up sinyali bulunamadı. Filtreleri gevşetin veya daha sonra tekrar deneyin.
            </CardContent>
          </Card>
        ) : null}

        {filteredItems.map((it) => {
          const s = it.signals || {};
          const primary = it.primary_contact || {};
          const idle = s.idle_days;
          const badgeReason = it.suggested_action?.reason || "review";

          let badgeLabel = "REVIEW";
          let badgeTone = "bg-slate-500/10 text-slate-200 border-slate-500/30";
          if (badgeReason === "callback") {
            badgeLabel = "CALL BACK";
            badgeTone = "bg-emerald-500/10 text-emerald-300 border-emerald-500/30";
          } else if (badgeReason === "overdue") {
            badgeLabel = "OVERDUE";
            badgeTone = "bg-rose-500/10 text-rose-300 border-rose-500/30";
          } else if (badgeReason === "due_today") {
            badgeLabel = "DUE TODAY";
            badgeTone = "bg-amber-500/10 text-amber-200 border-amber-500/30";
          } else if (badgeReason === "idle") {
            badgeLabel = "IDLE";
            badgeTone = "bg-sky-500/10 text-sky-200 border-sky-500/30";
          }

          const phoneNorm = normalizePhone(primary.phone || it.phone);
          const waNorm = normalizePhone(primary.whatsapp || primary.phone || it.phone);
          const mail = primary.email || it.email;

          return (
            <Card key={it.hotel_id} className="rounded-2xl border bg-card/80" data-testid="followup-row">
              <CardContent className="py-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div className="space-y-2 min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <div className="truncate text-sm font-semibold text-foreground">
                        {it.hotel_name || it.hotel_id}
                      </div>
                      {it.city ? (
                        <span className="rounded-full bg-accent px-2 py-0.5 text-[11px] text-muted-foreground">
                          {it.city}
                        </span>
                      ) : null}
                      <Badge
                        className={`ml-1 border text-[10px] font-semibold ${badgeTone}`}
                        variant="outline"
                      >
                        {badgeLabel}
                      </Badge>
                    </div>

                    {primary?.name || phoneNorm || mail ? (
                      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        {primary?.name ? <span className="font-medium text-foreground">{primary.name}</span> : null}
                        {phoneNorm ? <span>{phoneNorm}</span> : null}
                        {mail ? <span className="truncate max-w-[180px]">{mail}</span> : null}
                      </div>
                    ) : null}

                    <div className="mt-1 flex flex-wrap gap-3 text-[11px] text-muted-foreground">
                      <span>
                        Idle: {idle != null ? `${idle}g` : "-"}
                      </span>
                      <span>Open: {s.open_tasks ?? 0}</span>
                      <span>Today: {s.due_today ?? 0}</span>
                      <span>Overdue: {s.overdue ?? 0}</span>
                      <span>Next due: {formatDateTr(s.next_due_date)}</span>
                    </div>

                    {s.last_touch_summary || s.last_touch_at ? (
                      <div className="mt-1 text-xs text-muted-foreground">
                        <span className="font-medium">Son dokunuş:</span>{" "}
                        {s.last_touch_summary || "-"} {" "}
                        {s.last_touch_at ? `(${formatDateTr(s.last_touch_at)})` : ""}
                      </div>
                    ) : null}
                  </div>

                  <div className="flex flex-col items-end gap-2">
                    <div className="flex flex-wrap justify-end gap-1">
                      <Button
                        variant="outline"
                        size="xs"
                        asChild
                        disabled={!phoneNorm}
                        data-testid="followup-action-call"
                      >
                        <a href={phoneNorm ? `tel:${phoneNorm}` : undefined}>
                          <Phone className="mr-1 h-3 w-3" /> Ara
                        </a>
                      </Button>

                      <Button
                        variant="outline"
                        size="xs"
                        disabled={!waNorm}
                        data-testid="followup-action-whatsapp"
                        onClick={() => {
                          if (!waNorm) return;
                          const summary = encodeURIComponent(`Otel: ${it.hotel_name || it.hotel_id}`);
                          window.open(`https://wa.me/${waNorm.replace(/[^0-9+]/g, "")}?text=${summary}`, "_blank");
                        }}
                      >
                        <MessageCircle className="mr-1 h-3 w-3" /> WhatsApp
                      </Button>

                      <Button
                        variant="outline"
                        size="xs"
                        asChild
                        disabled={!mail}
                        data-testid="followup-action-email"
                      >
                        <a href={mail ? `mailto:${mail}` : undefined}>
                          <Mail className="mr-1 h-3 w-3" /> Mail
                        </a>
                      </Button>

                      <Button
                        variant="ghost"
                        size="xs"
                        className="gap-1"
                        data-testid="followup-action-detail"
                        onClick={() => navigate(`/app/agency/hotels/${it.hotel_id}`)}
                      >
                        Detay
                        <ArrowRight className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}

        {cursor ? (
          <div className="flex justify-center pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleLoadMore}
              disabled={loadingMore}
              className="gap-2"
              data-testid="followups-load-more"
            >
              {loadingMore ? <RefreshCw className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              Daha fazla yükle
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
