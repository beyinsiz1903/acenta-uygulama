import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import {
  Package,
  Plus,
  RefreshCw,
  Filter,
  ChevronRight,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  ArrowUpRight,
  Calendar,
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../../components/ui/dialog";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { fetchOrders, createOrder, seedDemoOrders, searchOrders } from "./lib/ordersApi";
import { toast } from "sonner";

const fmt = (v) =>
  new Intl.NumberFormat("tr-TR", { style: "currency", currency: "EUR" }).format(v || 0);

const STATUS_CONFIG = {
  draft: { label: "Taslak", className: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300", icon: FileText },
  pending_confirmation: { label: "Onay Bekliyor", className: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300", icon: Clock },
  confirmed: { label: "Onaylandı", className: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300", icon: CheckCircle2 },
  cancel_requested: { label: "İptal Talebi", className: "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300", icon: AlertTriangle },
  cancelled: { label: "İptal Edildi", className: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300", icon: XCircle },
  closed: { label: "Kapatıldı", className: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300", icon: CheckCircle2 },
};

const StatusBadge = ({ status }) => {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
  const Icon = cfg.icon;
  return (
    <Badge data-testid={`order-status-${status}`} className={`${cfg.className} gap-1 font-medium`}>
      <Icon className="h-3 w-3" />
      {cfg.label}
    </Badge>
  );
};

export default function OrdersPage() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [settlementFilter, setSettlementFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newOrder, setNewOrder] = useState({
    customer_id: "",
    agency_id: "",
    channel: "B2B",
    currency: "EUR",
    product_name: "",
    supplier_code: "ratehawk",
    check_in: "",
    check_out: "",
    sell_amount: "",
    supplier_amount: "",
  });

  const hasAdvancedFilters = searchQuery || dateFrom || dateTo || settlementFilter;

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["orders", statusFilter, channelFilter, searchQuery, dateFrom, dateTo, settlementFilter],
    queryFn: () =>
      hasAdvancedFilters
        ? searchOrders({
            status: statusFilter || undefined,
            channel: channelFilter || undefined,
            q: searchQuery || undefined,
            date_from: dateFrom || undefined,
            date_to: dateTo || undefined,
            settlement_status: settlementFilter || undefined,
          })
        : fetchOrders({ status: statusFilter || undefined, channel: channelFilter || undefined }),
  });

  const handleSeed = async () => {
    try {
      const result = await seedDemoOrders();
      toast.success(result.message || "Demo siparişler oluşturuldu");
      refetch();
    } catch {
      toast.error("Seed hatası");
    }
  };

  const handleCreate = async () => {
    setCreating(true);
    try {
      const sell = parseFloat(newOrder.sell_amount) || 0;
      const sup = parseFloat(newOrder.supplier_amount) || 0;
      const result = await createOrder({
        customer_id: newOrder.customer_id,
        agency_id: newOrder.agency_id,
        channel: newOrder.channel,
        currency: newOrder.currency,
        items: newOrder.product_name ? [{
          item_type: "hotel",
          supplier_code: newOrder.supplier_code,
          product_name: newOrder.product_name,
          check_in: newOrder.check_in,
          check_out: newOrder.check_out,
          sell_amount: sell,
          supplier_amount: sup,
          margin_amount: sell - sup,
        }] : [],
      });
      toast.success(`Sipariş oluşturuldu: ${result.order_number}`);
      setShowCreate(false);
      setNewOrder({ customer_id: "", agency_id: "", channel: "B2B", currency: "EUR", product_name: "", supplier_code: "ratehawk", check_in: "", check_out: "", sell_amount: "", supplier_amount: "" });
      refetch();
    } catch {
      toast.error("Sipariş oluşturulamadı");
    } finally {
      setCreating(false);
    }
  };

  const orders = data?.orders || [];
  const total = data?.total || 0;

  // Stats
  const stats = {
    total: total,
    draft: orders.filter((o) => o.status === "draft").length,
    confirmed: orders.filter((o) => o.status === "confirmed").length,
    cancelled: orders.filter((o) => o.status === "cancelled" || o.status === "cancel_requested").length,
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div data-testid="orders-page" className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Order Management</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Sipariş yaşam döngüsü yönetimi — OMS Faz 1
          </p>
        </div>
        <div className="flex gap-2">
          <Button data-testid="seed-orders-btn" variant="outline" size="sm" onClick={handleSeed}>
            <RefreshCw className="h-4 w-4 mr-1" /> Demo Seed
          </Button>
          <Button data-testid="create-order-btn" size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4 mr-1" /> Yeni Sipariş
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Package className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Toplam Sipariş</p>
                <p data-testid="stat-total-orders" className="text-xl font-bold">{stats.total}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center">
                <FileText className="h-5 w-5 text-zinc-600" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Taslak</p>
                <p data-testid="stat-draft-orders" className="text-xl font-bold">{stats.draft}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Onaylanmış</p>
                <p data-testid="stat-confirmed-orders" className="text-xl font-bold">{stats.confirmed}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                <XCircle className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">İptal</p>
                <p data-testid="stat-cancelled-orders" className="text-xl font-bold">{stats.cancelled}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="space-y-3">
        <div className="flex gap-3 items-center flex-wrap">
          <Filter className="h-4 w-4 text-muted-foreground shrink-0" />
          <Input
            data-testid="search-orders-input"
            placeholder="Sipariş no, müşteri, acenta ara..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-[240px]"
          />
          <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v === "all" ? "" : v)}>
            <SelectTrigger data-testid="filter-status" className="w-[180px]">
              <SelectValue placeholder="Status Filtre" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tümü</SelectItem>
              <SelectItem value="draft">Taslak</SelectItem>
              <SelectItem value="pending_confirmation">Onay Bekliyor</SelectItem>
              <SelectItem value="confirmed">Onaylanmış</SelectItem>
              <SelectItem value="cancel_requested">İptal Talebi</SelectItem>
              <SelectItem value="cancelled">İptal Edildi</SelectItem>
              <SelectItem value="closed">Kapatıldı</SelectItem>
            </SelectContent>
          </Select>
          <Select value={channelFilter} onValueChange={(v) => setChannelFilter(v === "all" ? "" : v)}>
            <SelectTrigger data-testid="filter-channel" className="w-[160px]">
              <SelectValue placeholder="Kanal Filtre" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tümü</SelectItem>
              <SelectItem value="B2B">B2B</SelectItem>
              <SelectItem value="B2C">B2C</SelectItem>
              <SelectItem value="Corporate">Corporate</SelectItem>
            </SelectContent>
          </Select>
          <Select value={settlementFilter} onValueChange={(v) => setSettlementFilter(v === "all" ? "" : v)}>
            <SelectTrigger data-testid="filter-settlement" className="w-[180px]">
              <SelectValue placeholder="Ödeme Durumu" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tümü</SelectItem>
              <SelectItem value="not_settled">Ödenmedi</SelectItem>
              <SelectItem value="partially_settled">Kısmi Ödendi</SelectItem>
              <SelectItem value="settled">Ödendi</SelectItem>
              <SelectItem value="reversed">İade</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="ghost" size="sm" onClick={refetch}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex gap-3 items-center">
          <Calendar className="h-4 w-4 text-muted-foreground shrink-0" />
          <Input
            data-testid="filter-date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="w-[160px]"
            placeholder="Başlangıç"
          />
          <span className="text-muted-foreground text-sm">—</span>
          <Input
            data-testid="filter-date-to"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="w-[160px]"
            placeholder="Bitiş"
          />
          {(searchQuery || dateFrom || dateTo || settlementFilter) && (
            <Button
              variant="ghost"
              size="sm"
              data-testid="clear-filters-btn"
              onClick={() => {
                setSearchQuery("");
                setDateFrom("");
                setDateTo("");
                setSettlementFilter("");
                setStatusFilter("");
                setChannelFilter("");
              }}
            >
              Filtreleri Temizle
            </Button>
          )}
        </div>
      </div>

      {/* Orders Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Siparişler ({total})</CardTitle>
        </CardHeader>
        <CardContent>
          {orders.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Package className="h-12 w-12 mx-auto mb-3 opacity-40" />
              <p>Henüz sipariş bulunmuyor.</p>
              <Button variant="outline" size="sm" className="mt-3" onClick={handleSeed}>
                Demo Veri Oluştur
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Sipariş No</TableHead>
                  <TableHead>Müşteri</TableHead>
                  <TableHead>Acenta</TableHead>
                  <TableHead>Kanal</TableHead>
                  <TableHead>Durum</TableHead>
                  <TableHead className="text-right">Satış</TableHead>
                  <TableHead className="text-right">Maliyet</TableHead>
                  <TableHead className="text-right">Marj</TableHead>
                  <TableHead>Tarih</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((o) => (
                  <TableRow
                    key={o.order_id}
                    data-testid={`order-row-${o.order_id}`}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => navigate(`/app/admin/orders/${o.order_id}`)}
                  >
                    <TableCell className="font-mono font-semibold text-sm">
                      {o.order_number}
                    </TableCell>
                    <TableCell className="text-sm">{o.customer_id || "—"}</TableCell>
                    <TableCell className="text-sm">{o.agency_id || "—"}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">{o.channel}</Badge>
                    </TableCell>
                    <TableCell><StatusBadge status={o.status} /></TableCell>
                    <TableCell className="text-right font-mono text-sm">{fmt(o.total_sell_amount)}</TableCell>
                    <TableCell className="text-right font-mono text-sm">{fmt(o.total_supplier_amount)}</TableCell>
                    <TableCell className="text-right font-mono text-sm font-medium text-emerald-600">
                      {fmt(o.total_margin_amount)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {o.created_at ? new Date(o.created_at).toLocaleDateString("tr-TR") : "—"}
                    </TableCell>
                    <TableCell>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Order Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Yeni Sipariş Oluştur</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Müşteri ID</Label>
                <Input data-testid="input-customer-id" value={newOrder.customer_id} onChange={(e) => setNewOrder({ ...newOrder, customer_id: e.target.value })} placeholder="cust_..." />
              </div>
              <div>
                <Label>Acenta ID</Label>
                <Input data-testid="input-agency-id" value={newOrder.agency_id} onChange={(e) => setNewOrder({ ...newOrder, agency_id: e.target.value })} placeholder="agency_..." />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Kanal</Label>
                <Select value={newOrder.channel} onValueChange={(v) => setNewOrder({ ...newOrder, channel: v })}>
                  <SelectTrigger data-testid="input-channel"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="B2B">B2B</SelectItem>
                    <SelectItem value="B2C">B2C</SelectItem>
                    <SelectItem value="Corporate">Corporate</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Para Birimi</Label>
                <Select value={newOrder.currency} onValueChange={(v) => setNewOrder({ ...newOrder, currency: v })}>
                  <SelectTrigger data-testid="input-currency"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EUR">EUR</SelectItem>
                    <SelectItem value="USD">USD</SelectItem>
                    <SelectItem value="TRY">TRY</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <hr className="my-1" />
            <p className="text-sm font-medium text-muted-foreground">Otel Bilgisi (Opsiyonel)</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Otel Adı</Label>
                <Input data-testid="input-hotel-name" value={newOrder.product_name} onChange={(e) => setNewOrder({ ...newOrder, product_name: e.target.value })} />
              </div>
              <div>
                <Label>Supplier</Label>
                <Select value={newOrder.supplier_code} onValueChange={(v) => setNewOrder({ ...newOrder, supplier_code: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ratehawk">RateHawk</SelectItem>
                    <SelectItem value="paximum">Paximum</SelectItem>
                    <SelectItem value="hotelbeds">Hotelbeds</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Check-in</Label>
                <Input data-testid="input-checkin" type="date" value={newOrder.check_in} onChange={(e) => setNewOrder({ ...newOrder, check_in: e.target.value })} />
              </div>
              <div>
                <Label>Check-out</Label>
                <Input data-testid="input-checkout" type="date" value={newOrder.check_out} onChange={(e) => setNewOrder({ ...newOrder, check_out: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Satış Fiyatı</Label>
                <Input data-testid="input-sell-amount" type="number" value={newOrder.sell_amount} onChange={(e) => setNewOrder({ ...newOrder, sell_amount: e.target.value })} />
              </div>
              <div>
                <Label>Maliyet</Label>
                <Input data-testid="input-supplier-amount" type="number" value={newOrder.supplier_amount} onChange={(e) => setNewOrder({ ...newOrder, supplier_amount: e.target.value })} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreate(false)}>İptal</Button>
            <Button data-testid="submit-create-order" onClick={handleCreate} disabled={creating}>
              {creating ? "Oluşturuluyor..." : "Sipariş Oluştur"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
