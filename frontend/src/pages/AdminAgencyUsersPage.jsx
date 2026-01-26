import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Users, AlertCircle, Loader2, Copy, ExternalLink } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../components/ui/dialog";
import { toast } from "sonner";

export default function AdminAgencyUsersPage() {
  const { agencyId } = useParams();
  const navigate = useNavigate();

  const [agency, setAgency] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteForm, setInviteForm] = useState({ email: "", name: "", role: "agency_agent" });
  const [inviteError, setInviteError] = useState("");
  const [inviteLoading, setInviteLoading] = useState(false);

  const [resetUser, setResetUser] = useState(null);
  const [resetLoading, setResetLoading] = useState(false);
  const [resetLink, setResetLink] = useState("");
  const [resetError, setResetError] = useState("");

  useEffect(() => {
    if (!agencyId) return;
    loadData();
  }, [agencyId]);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [agencyResp, usersResp] = await Promise.all([
        api.get(`/admin/agencies/`),
        api.get(`/admin/agencies/${agencyId}/users`),
      ]);

      const agencies = agencyResp.data || [];
      const current = agencies.find((a) => a.id === agencyId);
      setAgency(current || null);
      setUsers(usersResp.data || []);
    } catch (err) {
      console.error("[AdminAgencyUsers] load error", err);
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleInvite(e) {
    e.preventDefault();
    setInviteError("");

    const email = inviteForm.email.trim();
    if (!email) {
      setInviteError("Email zorunlu");
      return;
    }

    setInviteLoading(true);
    try {
      await api.post(`/admin/agencies/${agencyId}/users/invite`, {
        email,
        name: inviteForm.name || undefined,
        role: inviteForm.role,
      });
      toast.success("Kullanıcı davet edildi / acenteye bağlandı");
      setInviteForm({ email: "", name: "", role: "agency_agent" });
      setInviteOpen(false);
      await loadData();
    } catch (err) {
      const msg = apiErrorMessage(err);
      setInviteError(msg);
    } finally {
      setInviteLoading(false);
    }
  }

  async function handleRoleChange(u, newRole) {
    try {
      await api.patch(`/admin/agencies/${agencyId}/users/${u.id}`, {
        role: newRole,
      });
      toast.success("Rol güncellendi");
      await loadData();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  async function handleStatusToggle(u) {
    const newStatus = u.status === "active" ? "disabled" : "active";
    try {
      await api.patch(`/admin/agencies/${agencyId}/users/${u.id}`, {
        status: newStatus,
      });
      toast.success("Durum güncellendi");
      await loadData();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  async function handleResetPassword(u) {
    setResetUser(u);
    setResetError("");
    setResetLink("");
    setResetLoading(true);
    try {
      const resp = await api.post(`/admin/agencies/${agencyId}/users/${u.id}/reset-password`);
      setResetLink(resp.data?.reset_link || "");
    } catch (err) {
      setResetError(apiErrorMessage(err));
    } finally {
      setResetLoading(false);
    }
  }

  function copyResetLink() {
    if (!resetLink) return;
    navigator.clipboard
      .writeText(resetLink)
      .then(() => toast.success("Link kopyalandı"))
      .catch(() => toast.error("Kopyalama başarısız"));
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Acenta Kullanıcıları</h1>
          <p className="text-sm text-muted-foreground mt-1">Kullanıcılar yükleniyor...</p>
        </div>
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Veriler yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Acenta Kullanıcıları</h1>
            <p className="text-sm text-muted-foreground mt-1">Acenta kullanıcı yönetimi</p>
          </div>
          <Button variant="outline" onClick={() => navigate(-1)}>
            Geri
          </Button>
        </div>
        <div className="rounded-2xl border border-destructive/50 bg-destructive/5 p-8 flex flex-col items-center justify-center gap-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <div className="text-center">
            <p className="font-semibold text-foreground">Kullanıcılar yüklenemedi</p>
            <p className="text-sm text-muted-foreground mt-1">{error}</p>
          </div>
          <Button onClick={loadData}>Tekrar dene</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Acenta Kullanıcıları</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {agency ? `${agency.name} (${agency.id})` : "Seçili acenta"}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate(-1)}>
            Geri
          </Button>
          <Button className="gap-2" onClick={() => setInviteOpen(true)}>
            <Users className="h-4 w-4" />
            Yeni Kullanıcı / Davet
          </Button>
        </div>
      </div>

      {users.length === 0 ? (
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
            <Users className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="text-center max-w-md">
            <p className="font-semibold text-foreground">Henüz kullanıcı yok</p>
            <p className="text-sm text-muted-foreground mt-2">
              Bu acenta için yeni kullanıcı oluşturabilir veya mevcut kullanıcıları davet edebilirsiniz.
            </p>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="font-semibold">Email</TableHead>
                <TableHead className="font-semibold">Ad</TableHead>
                <TableHead className="font-semibold">Rol</TableHead>
                <TableHead className="font-semibold">Durum</TableHead>
                <TableHead className="font-semibold">Oluşturma</TableHead>
                <TableHead className="font-semibold">Aksiyonlar</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((u) => {
                const agencyRole = (u.roles || []).find((r) => r === "agency_admin" || r === "agency_agent");
                return (
                  <TableRow key={u.id}>
                    <TableCell className="font-mono text-xs">{u.email}</TableCell>
                    <TableCell>{u.name || "-"}</TableCell>
                    <TableCell>
                      <select
                        className="h-8 rounded-md border bg-background px-2 text-xs"
                        value={agencyRole || "agency_agent"}
                        onChange={(e) => handleRoleChange(u, e.target.value)}
                      >
                        <option value="agency_admin">Yönetici</option>
                        <option value="agency_agent">Satış/Operasyon</option>
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
                    <TableCell className="text-xs text-muted-foreground">{u.created_at || "-"}</TableCell>
                    <TableCell className="text-xs">
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant="outline"
                          size="xs"
                          onClick={() => handleStatusToggle(u)}
                          className="text-xs"
                        >
                          {u.status === "active" ? "Pasifleştir" : "Aktifleştir"}
                        </Button>
                        <Button
                          variant="outline"
                          size="xs"
                          onClick={() => handleResetPassword(u)}
                          className="text-xs"
                        >
                          Şifre Sıfırla
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Invite dialog */}
      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Yeni Kullanıcı / Davet</DialogTitle>
            <DialogDescription>
              Bu acenteye yeni bir kullanıcı ekleyebilir veya mevcut bir kullanıcıyı email adresi ile
              bağlayabilirsiniz.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleInvite} className="space-y-4 mt-2">
            <div className="space-y-2">
              <Label htmlFor="invite-email">Email *</Label>
              <Input
                id="invite-email"
                type="email"
                value={inviteForm.email}
                onChange={(e) => setInviteForm((prev) => ({ ...prev, email: e.target.value }))}
                placeholder="kullanici@example.com"
                disabled={inviteLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite-name">Ad (opsiyonel)</Label>
              <Input
                id="invite-name"
                value={inviteForm.name}
                onChange={(e) => setInviteForm((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="İsim soyisim"
                disabled={inviteLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite-role">Rol</Label>
              <select
                id="invite-role"
                className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                value={inviteForm.role}
                onChange={(e) => setInviteForm((prev) => ({ ...prev, role: e.target.value }))}
                disabled={inviteLoading}
              >
                <option value="agency_admin">Yönetici</option>
                <option value="agency_agent">Satış/Operasyon</option>
              </select>
            </div>

            {inviteError && <p className="text-xs text-red-600">{inviteError}</p>}

            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setInviteOpen(false)}
                disabled={inviteLoading}
              >
                İptal
              </Button>
              <Button type="submit" size="sm" disabled={inviteLoading} className="gap-2">
                {inviteLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                {inviteLoading ? "Gönderiliyor..." : "Kaydet"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Reset password dialog */}
      <Dialog open={!!resetUser} onOpenChange={(open) => !open && setResetUser(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Şifre Sıfırlama Linki</DialogTitle>
            <DialogDescription>
              Bu link sadece bu kullanıcı için üretilmiştir. Linki kopyalayıp güvenli bir kanaldan iletebilirsiniz.
            </DialogDescription>
          </DialogHeader>

          {resetLoading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : resetError ? (
            <p className="text-sm text-red-600">{resetError}</p>
          ) : resetLink ? (
            <div className="space-y-3">
              <div className="text-xs text-muted-foreground break-all border rounded-md bg-muted/40 px-3 py-2">
                {resetLink}
              </div>
              <div className="flex gap-2">
                <Button type="button" size="sm" className="gap-2" onClick={copyResetLink}>
                  <Copy className="h-4 w-4" />
                  Kopyala
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="gap-2"
                  onClick={() => {
                    if (resetLink) {
                      const url = resetLink.startsWith("http")
                        ? resetLink
                        : `${window.location.origin}${resetLink}`;
                      window.open(url, "_blank");
                    }
                  }}
                >
                  <ExternalLink className="h-4 w-4" />
                  Yeni sekmede aç
                </Button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Link üretilemedi.</p>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
