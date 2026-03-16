import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import { useState } from "react";
import {
  ArrowLeft,
  Package,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Hotel,
  CreditCard,
  Truck,
  MapPin,
  User,
  Calendar,
  DollarSign,
  Activity,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../../components/ui/dialog";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import {
  fetchOrderDetail,
  fetchOrderTimeline,
  confirmOrder,
  requestCancelOrder,
  cancelOrder,
  closeOrder,
} from "./lib/ordersApi";
import { toast } from "sonner";

const fmt = (v, currency = "EUR") =>
  new Intl.NumberFormat("tr-TR", { style: "currency", currency }).format(v || 0);

const STATUS_CONFIG = {
  draft: { label: "Taslak", className: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300", icon: FileText },
  pending_confirmation: { label: "Onay Bekliyor", className: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300", icon: Clock },
  confirmed: { label: "Onaylandı", className: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300", icon: CheckCircle2 },
  cancel_requested: { label: "İptal Talebi", className: "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300", icon: AlertTriangle },
  cancelled: { label: "İptal Edildi", className: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300", icon: XCircle },
  closed: { label: "Kapatıldı", className: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300", icon: CheckCircle2 },
};

const SUPPLIER_STATUS_CONFIG = {
  not_started: { label: "Başlamadı", className: "bg-zinc-100 text-zinc-600" },
  pending: { label: "Beklemede", className: "bg-amber-100 text-amber-700" },
  confirmed: { label: "Onaylandı", className: "bg-emerald-100 text-emerald-700" },
  failed: { label: "Başarısız", className: "bg-red-100 text-red-700" },
  cancel_requested: { label: "İptal Talebi", className: "bg-orange-100 text-orange-700" },
  cancelled: { label: "İptal", className: "bg-red-100 text-red-700" },
};

const SETTLEMENT_STATUS_CONFIG = {
  not_settled: { label: "Ödenmedi", className: "bg-zinc-100 text-zinc-600" },
  partially_settled: { label: "Kısmi Ödendi", className: "bg-amber-100 text-amber-700" },
  settled: { label: "Ödendi", className: "bg-emerald-100 text-emerald-700" },
  reversed: { label: "İade Edildi", className: "bg-red-100 text-red-700" },
};

const StatusBadge = ({ status, config = STATUS_CONFIG }) => {
  const cfg = config[status] || { label: status, className: "bg-zinc-100 text-zinc-600" };
  const Icon = cfg.icon;
  return (
    <Badge className={`${cfg.className} gap-1 font-medium`}>
      {Icon && <Icon className="h-3 w-3" />}
      {cfg.label}
    </Badge>
  );
};

// Allowed actions per status
const ALLOWED_ACTIONS = {
  draft: ["confirm"],
  pending_confirmation: ["confirm", "request-cancel", "cancel"],
  confirmed: ["request-cancel", "cancel", "close"],
  cancel_requested: ["cancel"],
  cancelled: ["close"],
  closed: [],
};

const ACTION_LABELS = {
  confirm: { label: "Onayla", variant: "default", icon: CheckCircle2 },
  "request-cancel": { label: "İptal Talebi", variant: "outline", icon: AlertTriangle },
  cancel: { label: "İptal Et", variant: "destructive", icon: XCircle },
  close: { label: "Kapat", variant: "secondary", icon: FileText },
};

export default function OrderDetailPage() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [actionDialog, setActionDialog] = useState(null);
  const [reason, setReason] = useState("");
  const [processing, setProcessing] = useState(false);
  const [timelineOpen, setTimelineOpen] = useState(true);

  const { data: order, isLoading } = useQuery({
    queryKey: ["order-detail", orderId],
    queryFn: () => fetchOrderDetail(orderId),
    enabled: !!orderId,
  });

  const { data: timeline } = useQuery({
    queryKey: ["order-timeline", orderId],
    queryFn: () => fetchOrderTimeline(orderId),
    enabled: !!orderId,
  });

  const handleAction = async () => {
    setProcessing(true);
    try {
      const actionMap = { confirm: confirmOrder, "request-cancel": requestCancelOrder, cancel: cancelOrder, close: closeOrder };
      const fn = actionMap[actionDialog];
      await fn(orderId, "admin", reason);
      toast.success(`Sipariş durumu güncellendi`);
      setActionDialog(null);
      setReason("");
      queryClient.invalidateQueries({ queryKey: ["order-detail", orderId] });
      queryClient.invalidateQueries({ queryKey: ["order-timeline", orderId] });
    } catch (err) {
      toast.error(err.message || "İşlem başarısız");
    } finally {
      setProcessing(false);
    }
  };

  if (isLoading || !order) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
      </div>
    );
  }

  const actions = ALLOWED_ACTIONS[order.status] || [];
  const items = order.items || [];
  const fin = order.financial_summary || {};
  const timelineEvents = timeline || [];

  return (
    <div data-testid="order-detail-page" className="space-y-6 p-6">
      {/* Back + Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate("/app/admin/orders")} data-testid="back-to-orders">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight font-mono">{order.order_number}</h1>
            <StatusBadge status={order.status} />
            <StatusBadge status={order.settlement_status || "not_settled"} config={SETTLEMENT_STATUS_CONFIG} />
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            {order.channel} &middot; {order.customer_id || "—"} &middot; {order.agency_id || "—"}
            {order.pricing_trace_id && <span className="ml-2 font-mono text-xs opacity-60">{order.pricing_trace_id}</span>}
          </p>
        </div>
        {/* Action Buttons */}
        <div className="flex gap-2">
          {actions.map((action) => {
            const cfg = ACTION_LABELS[action];
            const Icon = cfg.icon;
            return (
              <Button
                key={action}
                data-testid={`action-${action}`}
                variant={cfg.variant}
                size="sm"
                onClick={() => setActionDialog(action)}
              >
                <Icon className="h-4 w-4 mr-1" /> {cfg.label}
              </Button>
            );
          })}
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Items + Financial */}
        <div className="lg:col-span-2 space-y-6">
          {/* Order Items */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Hotel className="h-4 w-4" /> Sipariş Kalemleri ({items.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {items.length === 0 ? (
                <p className="text-muted-foreground text-sm text-center py-6">Henüz kalem eklenmemiş</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Tip</TableHead>
                      <TableHead>Ürün</TableHead>
                      <TableHead>Supplier</TableHead>
                      <TableHead>Supplier Booking</TableHead>
                      <TableHead>Tarihler</TableHead>
                      <TableHead className="text-right">Satış</TableHead>
                      <TableHead className="text-right">Maliyet</TableHead>
                      <TableHead className="text-right">Marj</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {items.map((item) => (
                      <TableRow key={item.item_id} data-testid={`item-row-${item.item_id}`}>
                        <TableCell>
                          <Badge variant="outline" className="text-xs capitalize">{item.item_type}</Badge>
                        </TableCell>
                        <TableCell className="font-medium text-sm">{item.product_name || item.product_reference}</TableCell>
                        <TableCell className="text-sm">{item.supplier_code}</TableCell>
                        <TableCell>
                          <div className="flex flex-col gap-1">
                            <span className="font-mono text-xs">{item.supplier_booking_id || "—"}</span>
                            <StatusBadge status={item.supplier_booking_status || "not_started"} config={SUPPLIER_STATUS_CONFIG} />
                          </div>
                        </TableCell>
                        <TableCell className="text-xs">
                          {item.check_in && item.check_out ? (
                            <span>{item.check_in} &rarr; {item.check_out}</span>
                          ) : "—"}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">{fmt(item.sell_amount, item.currency)}</TableCell>
                        <TableCell className="text-right font-mono text-sm">{fmt(item.supplier_amount, item.currency)}</TableCell>
                        <TableCell className="text-right font-mono text-sm font-medium text-emerald-600">
                          {fmt(item.margin_amount, item.currency)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Financial Summary */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <DollarSign className="h-4 w-4" /> Finansal Özet
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-3 rounded-lg bg-muted/50">
                  <p className="text-xs text-muted-foreground">Toplam Satış</p>
                  <p data-testid="fin-sell-total" className="text-lg font-bold font-mono">{fmt(fin.sell_total, fin.currency)}</p>
                </div>
                <div className="text-center p-3 rounded-lg bg-muted/50">
                  <p className="text-xs text-muted-foreground">Toplam Maliyet</p>
                  <p data-testid="fin-supplier-total" className="text-lg font-bold font-mono">{fmt(fin.supplier_total, fin.currency)}</p>
                </div>
                <div className="text-center p-3 rounded-lg bg-emerald-50 dark:bg-emerald-900/20">
                  <p className="text-xs text-muted-foreground">Toplam Marj</p>
                  <p data-testid="fin-margin-total" className="text-lg font-bold font-mono text-emerald-600">{fmt(fin.margin_total, fin.currency)}</p>
                </div>
                <div className="text-center p-3 rounded-lg bg-muted/50">
                  <p className="text-xs text-muted-foreground">Ödeme Durumu</p>
                  <div className="mt-1">
                    <StatusBadge status={fin.settlement_status || "not_settled"} config={SETTLEMENT_STATUS_CONFIG} />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right: Timeline */}
        <div className="space-y-6">
          {/* Order Info Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Package className="h-4 w-4" /> Sipariş Bilgileri
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Sipariş No</span>
                <span className="font-mono font-medium">{order.order_number}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Kanal</span>
                <Badge variant="outline">{order.channel}</Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Para Birimi</span>
                <span>{order.currency}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Kaynak</span>
                <span>{order.source}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Oluşturan</span>
                <span>{order.created_by}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Oluşturulma</span>
                <span className="text-xs">{order.created_at ? new Date(order.created_at).toLocaleString("tr-TR") : "—"}</span>
              </div>
              {order.pricing_trace_id && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Pricing Trace</span>
                  <span className="font-mono text-xs">{order.pricing_trace_id}</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Timeline */}
          <Card>
            <CardHeader className="pb-2 cursor-pointer" onClick={() => setTimelineOpen(!timelineOpen)}>
              <CardTitle className="text-base flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Olay Zaman Çizelgesi ({timelineEvents.length})
                {timelineOpen ? <ChevronUp className="h-4 w-4 ml-auto" /> : <ChevronDown className="h-4 w-4 ml-auto" />}
              </CardTitle>
            </CardHeader>
            {timelineOpen && (
              <CardContent>
                {timelineEvents.length === 0 ? (
                  <p className="text-muted-foreground text-sm text-center py-4">Henüz olay yok</p>
                ) : (
                  <div className="relative space-y-0">
                    {timelineEvents.map((ev, idx) => (
                      <div key={ev.event_id} data-testid={`timeline-event-${ev.event_id}`} className="flex gap-3 pb-4 last:pb-0">
                        {/* Line */}
                        <div className="flex flex-col items-center">
                          <div className="h-2.5 w-2.5 rounded-full bg-primary mt-1.5 shrink-0" />
                          {idx < timelineEvents.length - 1 && <div className="w-px flex-1 bg-border mt-1" />}
                        </div>
                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">
                              {ev.event_type.replace(/_/g, " ")}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {ev.actor_name} &middot; {ev.occurred_at ? new Date(ev.occurred_at).toLocaleString("tr-TR") : ""}
                          </p>
                          {ev.after_state?.status && (
                            <div className="mt-1">
                              {ev.before_state?.status && (
                                <span className="text-xs text-muted-foreground">
                                  {ev.before_state.status} &rarr;{" "}
                                </span>
                              )}
                              <StatusBadge status={ev.after_state.status} />
                            </div>
                          )}
                          {ev.payload?.reason && (
                            <p className="text-xs text-muted-foreground mt-1 italic">
                              "{ev.payload.reason}"
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            )}
          </Card>
        </div>
      </div>

      {/* Action Confirmation Dialog */}
      <Dialog open={!!actionDialog} onOpenChange={() => { setActionDialog(null); setReason(""); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {actionDialog && ACTION_LABELS[actionDialog]?.label} — {order.order_number}
            </DialogTitle>
          </DialogHeader>
          <div className="py-2">
            <Label>Açıklama (opsiyonel)</Label>
            <Textarea
              data-testid="action-reason-input"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Bu işlem için bir açıklama girebilirsiniz..."
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setActionDialog(null); setReason(""); }}>Vazgeç</Button>
            <Button
              data-testid="confirm-action-btn"
              variant={actionDialog === "cancel" ? "destructive" : "default"}
              onClick={handleAction}
              disabled={processing}
            >
              {processing ? "İşleniyor..." : "Onayla"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
