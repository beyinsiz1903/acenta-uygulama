import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Clock,
  Filter,
  History,
  User,
  FileText,
  Settings,
  CreditCard,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../../components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../../components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "../../components/ui/dialog";
import { fetchTimeline, fetchTimelineStats } from "./lib/timelineApi";

const ACTION_ICONS = {
  created: <FileText className="h-4 w-4 text-emerald-500" />,
  updated: <Settings className="h-4 w-4 text-blue-500" />,
  deleted: <AlertTriangle className="h-4 w-4 text-red-500" />,
  submitted: <ChevronRight className="h-4 w-4 text-amber-500" />,
  approved: <CreditCard className="h-4 w-4 text-emerald-600" />,
  rejected: <AlertTriangle className="h-4 w-4 text-red-600" />,
  paid: <CreditCard className="h-4 w-4 text-emerald-700" />,
  resolved: <Settings className="h-4 w-4 text-teal-500" />,
  dismissed: <AlertTriangle className="h-4 w-4 text-zinc-400" />,
};

const ACTION_LABELS = {
  created: "Olusturuldu",
  updated: "Guncellendi",
  deleted: "Silindi",
  submitted: "Onaya Gonderildi",
  approved: "Onaylandi",
  rejected: "Reddedildi",
  paid: "Odendi",
  resolved: "Cozuldu",
  dismissed: "Kapatildi",
};

const ENTITY_LABELS = {
  distribution_rule: "Dagitim Kurali",
  channel_config: "Kanal Yapilandirmasi",
  guardrail: "Koruma Siniri",
  promotion: "Promosyon",
  settlement_run: "Uzlasma Islemi",
  finance_exception: "Finans Istisnasi",
};

const ENTITY_TYPES = [
  { value: "all", label: "Tum Tipler" },
  { value: "distribution_rule", label: "Dagitim Kurali" },
  { value: "channel_config", label: "Kanal Yap." },
  { value: "guardrail", label: "Koruma Siniri" },
  { value: "promotion", label: "Promosyon" },
  { value: "settlement_run", label: "Uzlasma" },
  { value: "finance_exception", label: "Finans Istisna" },
];

const ACTION_TYPES = [
  { value: "all", label: "Tum Aksiyonlar" },
  { value: "created", label: "Olusturuldu" },
  { value: "updated", label: "Guncellendi" },
  { value: "deleted", label: "Silindi" },
  { value: "approved", label: "Onaylandi" },
  { value: "rejected", label: "Reddedildi" },
  { value: "paid", label: "Odendi" },
];

function formatTs(ts) {
  if (!ts) return "-";
  const d = new Date(ts);
  return d.toLocaleString("tr-TR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function ActivityTimelinePage() {
  const [entityFilter, setEntityFilter] = useState("all");
  const [actionFilter, setActionFilter] = useState("all");
  const [page, setPage] = useState(0);
  const [detailEvent, setDetailEvent] = useState(null);
  const PAGE_SIZE = 30;

  const { data: stats } = useQuery({
    queryKey: ["timeline-stats"],
    queryFn: fetchTimelineStats,
    staleTime: 30_000,
  });

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["timeline", entityFilter, actionFilter, page],
    queryFn: () =>
      fetchTimeline({
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
        entity_type: entityFilter !== "all" ? entityFilter : undefined,
        action: actionFilter !== "all" ? actionFilter : undefined,
      }),
    staleTime: 10_000,
  });

  const events = data?.events || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-6" data-testid="activity-timeline-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" data-testid="timeline-title">
            Aktivite Zaman Cizgisi
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Tum sistem aksiyonlarinin denetim izi
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} data-testid="timeline-refresh-btn">
          <RefreshCw className="h-4 w-4 mr-1" /> Yenile
        </Button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="timeline-stats-cards">
          <Card>
            <CardContent className="p-4">
              <div className="text-sm text-muted-foreground">Toplam Olay</div>
              <div className="text-2xl font-bold" data-testid="stat-total-events">{stats.total_events}</div>
            </CardContent>
          </Card>
          {Object.entries(stats.by_entity_type || {}).slice(0, 3).map(([key, val]) => (
            <Card key={key}>
              <CardContent className="p-4">
                <div className="text-sm text-muted-foreground">{ENTITY_LABELS[key] || key}</div>
                <div className="text-2xl font-bold">{val}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4" />
            <CardTitle className="text-base">Filtreler</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <Select value={entityFilter} onValueChange={(v) => { setEntityFilter(v); setPage(0); }}>
              <SelectTrigger className="w-48" data-testid="filter-entity-type">
                <SelectValue placeholder="Tip" />
              </SelectTrigger>
              <SelectContent>
                {ENTITY_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={actionFilter} onValueChange={(v) => { setActionFilter(v); setPage(0); }}>
              <SelectTrigger className="w-48" data-testid="filter-action">
                <SelectValue placeholder="Aksiyon" />
              </SelectTrigger>
              <SelectContent>
                {ACTION_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Events Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <History className="h-4 w-4" />
            Olaylar ({total})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">Yukleniyor...</div>
          ) : events.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground" data-testid="timeline-empty">
              Henuz olay kaydedilmemis
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-40">Tarih</TableHead>
                    <TableHead className="w-36">Aksiyon</TableHead>
                    <TableHead>Varlik</TableHead>
                    <TableHead className="w-48">Kullanici</TableHead>
                    <TableHead className="w-20 text-right">Detay</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {events.map((evt) => (
                    <TableRow key={evt.event_id} data-testid={`timeline-event-${evt.event_id}`}>
                      <TableCell className="text-xs text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                          <Clock className="h-3 w-3" />
                          {formatTs(evt.timestamp)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          {ACTION_ICONS[evt.action] || <ChevronRight className="h-4 w-4" />}
                          <Badge variant="secondary" className="text-xs">
                            {ACTION_LABELS[evt.action] || evt.action}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="font-medium text-sm">
                          {ENTITY_LABELS[evt.entity_type] || evt.entity_type}
                        </div>
                        <div className="text-xs text-muted-foreground font-mono">
                          {evt.entity_id}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5 text-sm">
                          <User className="h-3 w-3 text-muted-foreground" />
                          {evt.actor}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDetailEvent(evt)}
                          data-testid={`timeline-detail-btn-${evt.event_id}`}
                        >
                          <ChevronDown className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4" data-testid="timeline-pagination">
                  <div className="text-sm text-muted-foreground">
                    Sayfa {page + 1} / {totalPages}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>
                      Onceki
                    </Button>
                    <Button variant="outline" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>
                      Sonraki
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Event Detail Dialog */}
      <Dialog open={!!detailEvent} onOpenChange={() => setDetailEvent(null)}>
        <DialogContent className="max-w-lg" data-testid="event-detail-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {detailEvent && (ACTION_ICONS[detailEvent.action] || <ChevronRight className="h-4 w-4" />)}
              Olay Detayi
            </DialogTitle>
          </DialogHeader>
          {detailEvent && (
            <div className="space-y-3 text-sm">
              <Row label="Olay ID" value={detailEvent.event_id} />
              <Row label="Tarih" value={formatTs(detailEvent.timestamp)} />
              <Row label="Kullanici" value={detailEvent.actor} />
              <Row label="Aksiyon" value={ACTION_LABELS[detailEvent.action] || detailEvent.action} />
              <Row label="Varlik Tipi" value={ENTITY_LABELS[detailEvent.entity_type] || detailEvent.entity_type} />
              <Row label="Varlik ID" value={detailEvent.entity_id} mono />
              {detailEvent.trace_id && <Row label="Trace ID" value={detailEvent.trace_id} mono />}

              {detailEvent.metadata && Object.keys(detailEvent.metadata).length > 0 && (
                <div>
                  <div className="font-medium text-muted-foreground mb-1">Metadata</div>
                  <pre className="bg-muted rounded p-2 text-xs overflow-auto max-h-32">
                    {JSON.stringify(detailEvent.metadata, null, 2)}
                  </pre>
                </div>
              )}

              {detailEvent.before_summary && (
                <div>
                  <div className="font-medium text-muted-foreground mb-1">Onceki Durum</div>
                  <pre className="bg-red-50 dark:bg-red-950/20 rounded p-2 text-xs overflow-auto max-h-32">
                    {JSON.stringify(detailEvent.before_summary, null, 2)}
                  </pre>
                </div>
              )}

              {detailEvent.after_summary && (
                <div>
                  <div className="font-medium text-muted-foreground mb-1">Yeni Durum</div>
                  <pre className="bg-emerald-50 dark:bg-emerald-950/20 rounded p-2 text-xs overflow-auto max-h-32">
                    {JSON.stringify(detailEvent.after_summary, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Row({ label, value, mono }) {
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className={mono ? "font-mono text-xs" : ""}>{value}</span>
    </div>
  );
}
