import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Calendar, Users } from "lucide-react";

import { formatMoney } from "../lib/format";
import { formatDateTime } from "../utils/formatters";
import { Button } from "../components/ui/button";
import { BookingDetailDrawer } from "../components/BookingDetailDrawer";
import { PageShell, DataTable, SortableHeader, FilterBar, StatusBadge } from "../design-system";
import { useAgencyBookings } from "../features/bookings/hooks";

const STATUS_OPTIONS = [
  { value: "confirmed", label: "Onaylı" },
  { value: "cancelled", label: "İptal" },
  { value: "draft", label: "Taslak" },
];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export default function AgencyBookingsListPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedId, setSelectedId] = useState(null);

  const { data: rawBookings = [], isLoading, isError, error, refetch } = useAgencyBookings();

  const bookings = useMemo(() =>
    [...rawBookings].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)),
    [rawBookings]
  );

  const today = todayIso();
  const todayArrivals = useMemo(
    () => bookings.filter((b) => (b.stay || {}).check_in === today).length,
    [bookings, today]
  );

  const filtered = useMemo(() => {
    let list = bookings;
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter((b) => {
        const guest = b.guest || {};
        return `${b.id} ${b.hotel_name || ""} ${guest.full_name || ""}`.toLowerCase().includes(q);
      });
    }
    if (statusFilter) {
      list = list.filter((b) => b.status === statusFilter);
    }
    return list;
  }, [bookings, search, statusFilter]);

  const columns = useMemo(() => [
    {
      accessorKey: "id",
      header: ({ column }) => <SortableHeader column={column}>Booking ID</SortableHeader>,
      cell: ({ row }) => <span className="font-mono text-sm" data-testid={`agency-bookings-row-${row.original.id}`}>{row.original.id}</span>,
    },
    {
      accessorKey: "hotel_name",
      header: ({ column }) => <SortableHeader column={column}>Otel</SortableHeader>,
      cell: ({ row }) => <span className="text-sm font-medium">{row.original.hotel_name || "-"}</span>,
    },
    {
      id: "dates",
      header: "Tarihler",
      cell: ({ row }) => {
        const stay = row.original.stay || {};
        return (
          <div>
            <div className="flex items-center gap-1 text-sm">
              <Calendar className="h-3 w-3 text-muted-foreground" />
              {stay.check_in} - {stay.check_out}
            </div>
            <div className="text-xs text-muted-foreground">{stay.nights} gece</div>
          </div>
        );
      },
    },
    {
      id: "guest",
      header: "Misafir",
      cell: ({ row }) => {
        const guest = row.original.guest || {};
        return (
          <div className="flex items-center gap-1 text-sm">
            <Users className="h-3 w-3 text-muted-foreground" />
            {guest.full_name || "-"}
          </div>
        );
      },
    },
    {
      id: "amount",
      header: ({ column }) => <SortableHeader column={column}>Tutar</SortableHeader>,
      accessorFn: (row) => (row.rate_snapshot?.price?.total || 0),
      cell: ({ row }) => {
        const price = row.original.rate_snapshot?.price || {};
        return <span className="text-sm font-semibold">{formatMoney(price.total || 0, price.currency || "TRY")}</span>;
      },
    },
    {
      accessorKey: "status",
      header: "Durum",
      cell: ({ row }) => {
        const status = row.original.status;
        const statusMap = {
          confirmed: "confirmed",
          guaranteed: "confirmed",
          checked_in: "confirmed",
          cancelled: "cancelled",
          draft: "draft",
        };
        return <StatusBadge status={statusMap[status] || status} />;
      },
    },
    {
      accessorKey: "created_at",
      header: ({ column }) => <SortableHeader column={column}>Oluşturma</SortableHeader>,
      cell: ({ row }) => <span className="text-sm text-muted-foreground">{formatDateTime(row.original.created_at)}</span>,
    },
  ], []);

  return (
    <PageShell
      title="Rezervasyonlarım"
      description={`${bookings.length} rezervasyon — Bugün giriş: ${todayArrivals}`}
      actions={
        <Button onClick={() => navigate("/app/agency/hotels")} size="sm" className="gap-1.5 text-xs font-medium h-9" data-testid="agency-bookings-new-search-button">
          <Search className="h-3.5 w-3.5" />
          Yeni Arama
        </Button>
      }
    >
      <div className="space-y-3" data-testid="agency-bookings-page">
        <FilterBar
          search={{ placeholder: "Misafir, otel veya Booking ID ara...", value: search, onChange: setSearch }}
          filters={[
            { key: "status", label: "Durum", value: statusFilter, onChange: setStatusFilter, options: STATUS_OPTIONS },
          ]}
          onReset={() => { setSearch(""); setStatusFilter(""); }}
        />

        {isError && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-600" data-testid="agency-bookings-error">
            {error?.message || "Veriler yüklenemedi"}
            <Button variant="ghost" size="sm" className="ml-2 h-6 text-xs" onClick={() => refetch()}>Tekrar Dene</Button>
          </div>
        )}

        <DataTable
          data={filtered}
          columns={columns}
          loading={isLoading}
          pageSize={20}
          onRowClick={(row) => { setSelectedId(row.id); setDrawerOpen(true); }}
          emptyState={
            <div className="flex flex-col items-center gap-3 py-8">
              <p className="text-sm font-medium text-muted-foreground">Henüz rezervasyon yok</p>
              <p className="text-xs text-muted-foreground/70">Hızlı Rezervasyon ekranından arama yapıp rezervasyon oluşturabilirsiniz.</p>
              <Button onClick={() => navigate("/app/agency/hotels")} size="sm" className="text-xs" data-testid="agency-bookings-empty-search-hotels-button">
                <Search className="h-3.5 w-3.5 mr-1" /> Otel Ara
              </Button>
            </div>
          }
        />
      </div>

      <BookingDetailDrawer
        bookingId={selectedId}
        mode="agency"
        open={drawerOpen}
        onOpenChange={(next) => {
          setDrawerOpen(next);
          if (!next) refetch();
        }}
        onBookingChanged={() => refetch()}
      />
    </PageShell>
  );
}
