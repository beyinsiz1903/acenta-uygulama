import React, { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Users, AlertCircle, Loader2, Search,
  ChevronDown, UserPlus, ShieldCheck, ShieldOff,
} from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { toast } from "sonner";

export default function AdminAllUsersPage() {
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [agencies, setAgencies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [agencyFilter, setAgencyFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [usersResp, agenciesResp] = await Promise.all([
        api.get("/admin/all-users"),
        api.get("/admin/agencies"),
      ]);
      setUsers(usersResp.data || []);
      setAgencies(agenciesResp.data || []);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  const filtered = useMemo(() => {
    let list = users;
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(
        (u) =>
          u.email?.toLowerCase().includes(q) ||
          u.name?.toLowerCase().includes(q) ||
          u.agency_name?.toLowerCase().includes(q)
      );
    }
    if (agencyFilter !== "all") {
      list = list.filter((u) => u.agency_id === agencyFilter);
    }
    if (statusFilter !== "all") {
      list = list.filter((u) => u.status === statusFilter);
    }
    return list;
  }, [users, search, agencyFilter, statusFilter]);

  async function handleStatusToggle(u) {
    if (!u.agency_id) return;
    const newStatus = u.status === "active" ? "disabled" : "active";
    try {
      await api.patch(`/admin/agencies/${u.agency_id}/users/${u.id}`, { status: newStatus });
      toast.success(`${u.email} durumu guncellendi`);
      await loadData();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  async function handleRoleChange(u, newRole) {
    if (!u.agency_id) return;
    try {
      await api.patch(`/admin/agencies/${u.agency_id}/users/${u.id}`, { role: newRole });
      toast.success(`${u.email} rolu guncellendi`);
      await loadData();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  const agencyRole = (roles) => {
    if (roles?.includes("agency_admin")) return "agency_admin";
    if (roles?.includes("agency_agent")) return "agency_agent";
    return "agency_agent";
  };

  if (loading) {
    return (
      <div className="space-y-6" data-testid="all-users-page">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Users className="h-6 w-6 text-primary" /> Kullanici Yonetimi
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Tum acenta kullanicilari yukleniyor...</p>
        </div>
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6" data-testid="all-users-page">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Users className="h-6 w-6 text-primary" /> Kullanici Yonetimi
          </h1>
        </div>
        <div className="rounded-2xl border border-destructive/50 bg-destructive/5 p-8 flex flex-col items-center gap-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button onClick={loadData}>Tekrar dene</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="all-users-page">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Users className="h-6 w-6 text-primary" /> Kullanici Yonetimi
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Tum acentalardaki kullanicilari goruntuleyip yonetin ({users.length} kullanici, {agencies.length} acenta)
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            data-testid="user-search"
            placeholder="Email, isim veya acenta ara..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="relative">
          <select
            data-testid="agency-filter"
            className="h-9 rounded-md border bg-background px-3 pr-8 text-sm appearance-none cursor-pointer"
            value={agencyFilter}
            onChange={(e) => setAgencyFilter(e.target.value)}
          >
            <option value="all">Tum Acentalar</option>
            {agencies.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        </div>
        <div className="relative">
          <select
            data-testid="status-filter"
            className="h-9 rounded-md border bg-background px-3 pr-8 text-sm appearance-none cursor-pointer"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">Tum Durumlar</option>
            <option value="active">Aktif</option>
            <option value="disabled">Pasif</option>
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="rounded-xl border bg-card p-4">
          <div className="text-xs text-muted-foreground">Toplam Kullanici</div>
          <div className="text-2xl font-bold text-foreground mt-1" data-testid="total-users-count">{users.length}</div>
        </div>
        <div className="rounded-xl border bg-card p-4">
          <div className="text-xs text-muted-foreground">Aktif</div>
          <div className="text-2xl font-bold text-emerald-600 mt-1" data-testid="active-users-count">
            {users.filter((u) => u.status === "active").length}
          </div>
        </div>
        <div className="rounded-xl border bg-card p-4">
          <div className="text-xs text-muted-foreground">Pasif</div>
          <div className="text-2xl font-bold text-red-500 mt-1" data-testid="disabled-users-count">
            {users.filter((u) => u.status === "disabled").length}
          </div>
        </div>
        <div className="rounded-xl border bg-card p-4">
          <div className="text-xs text-muted-foreground">Acenta Sayisi</div>
          <div className="text-2xl font-bold text-foreground mt-1" data-testid="agency-count">{agencies.length}</div>
        </div>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center gap-4">
          <Users className="h-10 w-10 text-muted-foreground/40" />
          <p className="font-medium text-foreground">
            {search || agencyFilter !== "all" || statusFilter !== "all"
              ? "Filtrelere uyan kullanici bulunamadi"
              : "Henuz kullanici yok"}
          </p>
        </div>
      ) : (
        <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="font-semibold">Email</TableHead>
                <TableHead className="font-semibold">Ad</TableHead>
                <TableHead className="font-semibold">Acenta</TableHead>
                <TableHead className="font-semibold">Rol</TableHead>
                <TableHead className="font-semibold">Durum</TableHead>
                <TableHead className="font-semibold">Olusturma</TableHead>
                <TableHead className="font-semibold">Aksiyonlar</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((u) => (
                <TableRow key={u.id} data-testid={`user-row-${u.id}`}>
                  <TableCell className="font-mono text-xs">{u.email}</TableCell>
                  <TableCell className="text-sm">{u.name || "-"}</TableCell>
                  <TableCell>
                    {u.agency_name ? (
                      <button
                        className="text-xs text-primary hover:underline"
                        onClick={() => navigate(`/app/admin/agencies/${u.agency_id}/users`)}
                        data-testid={`go-agency-${u.id}`}
                      >
                        {u.agency_name}
                      </button>
                    ) : (
                      <span className="text-xs text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <select
                      data-testid={`role-select-${u.id}`}
                      className="h-8 rounded-md border bg-background px-2 text-xs"
                      value={agencyRole(u.roles)}
                      onChange={(e) => handleRoleChange(u, e.target.value)}
                    >
                      <option value="agency_admin">Yonetici</option>
                      <option value="agency_agent">Satis/Operasyon</option>
                    </select>
                  </TableCell>
                  <TableCell>
                    {u.status === "active" ? (
                      <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
                        Aktif
                      </Badge>
                    ) : (
                      <Badge variant="secondary">Pasif</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {u.created_at ? new Date(u.created_at).toLocaleDateString("tr-TR") : "-"}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      data-testid={`toggle-status-${u.id}`}
                      onClick={() => handleStatusToggle(u)}
                      className="text-xs gap-1.5"
                    >
                      {u.status === "active" ? (
                        <><ShieldOff className="h-3.5 w-3.5" /> Pasiflestir</>
                      ) : (
                        <><ShieldCheck className="h-3.5 w-3.5" /> Aktiflestir</>
                      )}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
