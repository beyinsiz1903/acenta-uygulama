import React, { useCallback, useEffect, useState } from "react";
import { Settings, UserPlus } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link } from "react-router-dom";

import { api, apiErrorMessage, getUser } from "../lib/api";
import { createUserSchema } from "../lib/validations";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import { Checkbox } from "../components/ui/checkbox";
import { SettingsSectionNav } from "../components/settings/SettingsSectionNav";

const AVAILABLE_ROLES = [
  { id: "super_admin", label: "Süper Admin" },
  { id: "admin", label: "Admin (legacy)" },
  { id: "sales", label: "Satış" },
  { id: "ops", label: "Operasyon" },
  { id: "accounting", label: "Muhasebe" },
  { id: "b2b_agent", label: "B2B Acenta Kullanıcısı" },
];

function UserForm({ open, onOpenChange, onSaved }) {
  const [serverError, setServerError] = useState("");

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(createUserSchema),
    defaultValues: { email: "", name: "", password: "pass123", roles: ["sales"] },
  });

  const selectedRoles = watch("roles") || [];

  useEffect(() => {
    if (open) {
      reset({ email: "", name: "", password: "pass123", roles: ["sales"] });
      setServerError("");
    }
  }, [open, reset]);

  async function onSubmit(data) {
    setServerError("");
    try {
      await api.post("/settings/users", {
        email: data.email,
        name: data.name,
        password: data.password,
        roles: data.roles,
        agency_id: null,
      });
      onSaved?.();
      onOpenChange(false);
    } catch (e) {
      setServerError(apiErrorMessage(e));
    }
  }

  function toggleRole(roleId, checked) {
    const current = new Set(selectedRoles);
    if (checked) current.add(roleId);
    else current.delete(roleId);
    setValue("roles", Array.from(current), { shouldValidate: true });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Yeni Kullanıcı</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label>Email</Label>
            <Input
              type="email"
              autoComplete="email"
              aria-invalid={!!errors.email}
              data-testid="user-email"
              {...register("email")}
            />
            {errors.email && (
              <p className="text-xs text-rose-600" role="alert">{errors.email.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label>Ad</Label>
            <Input
              aria-invalid={!!errors.name}
              data-testid="user-name"
              {...register("name")}
            />
            {errors.name && (
              <p className="text-xs text-rose-600" role="alert">{errors.name.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label>Şifre</Label>
            <Input
              type="password"
              autoComplete="new-password"
              aria-invalid={!!errors.password}
              data-testid="user-password"
              {...register("password")}
            />
            {errors.password && (
              <p className="text-xs text-rose-600" role="alert">{errors.password.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label>Roller</Label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1" data-testid="user-roles">
              {AVAILABLE_ROLES.map((role) => {
                const checked = selectedRoles.includes(role.id);
                return (
                  <label
                    key={role.id}
                    className="flex items-center gap-2 rounded-md border border-border/60 bg-muted/40 px-2 py-1.5 text-xs cursor-pointer hover:bg-muted/70"
                  >
                    <Checkbox
                      checked={checked}
                      onCheckedChange={(val) => toggleRole(role.id, val)}
                    />
                    <span>{role.label}</span>
                    <span className="ml-auto font-mono text-2xs text-muted-foreground">{role.id}</span>
                  </label>
                );
              })}
            </div>
            {errors.roles && (
              <p className="text-xs text-rose-600" role="alert">{errors.roles.message}</p>
            )}
            <div className="text-xs text-muted-foreground">
              En az bir rol seçilmeli. Sadece deneysel kullanıcılar için admin/sales/ops/accounting/b2b_agent.
            </div>
          </div>

          {serverError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="user-error">
              {serverError}
            </div>
          ) : null}

          <DialogFooter>
            <Button variant="outline" type="button" onClick={() => onOpenChange(false)}>
              Vazgeç
            </Button>
            <Button type="submit" disabled={isSubmitting} data-testid="user-save">
              {isSubmitting ? "Kaydediliyor..." : "Kaydet"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function SettingsPage() {
  const currentUser = getUser();
  const canManageUsers = (currentUser?.roles || []).some((role) => ["super_admin", "admin"].includes(role));
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [openUser, setOpenUser] = useState(false);

  const load = useCallback(async () => {
    if (!canManageUsers) {
      setUsers([]);
      setError("");
      return;
    }

    setError("");
    try {
      const resp = await api.get("/settings/users");
      setUsers(resp.data || []);
    } catch (e) {
      const msg = apiErrorMessage(e);
      // "Not Found" durumunda henüz kullanıcı yokmuş gibi davranıyoruz; kırmızı hata göstermiyoruz.
      if (msg === "Not Found") {
        setUsers([]);
      } else {
        setError(msg);
      }
    }
  }, [canManageUsers]);

  useEffect(() => {
    const t = setTimeout(() => {
      load();
    }, 0);
    return () => clearTimeout(t);
  }, [load]);

  if (!canManageUsers) {
    return (
      <div className="space-y-6" data-testid="settings-users-page">
        <div>
          <h2 className="text-4xl font-semibold text-foreground">Ayarlar</h2>
          <p className="mt-2 text-base text-muted-foreground">Güvenlik ve yönetim bölümleri.</p>
        </div>

        <SettingsSectionNav showUsersSection={false} />

        <Card className="rounded-3xl border-border/60" data-testid="settings-users-unauthorized-state">
          <CardContent className="space-y-3 p-6">
            <div>
              <h3 className="text-lg font-semibold text-foreground">Kullanıcı yönetimi yetkisi gerekiyor</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Bu bölüm yalnızca yönetici rolleri için açıktır. Güvenlik ayarlarından aktif oturumlarınızı yönetebilirsiniz.
              </p>
            </div>
            <Button asChild data-testid="settings-users-go-security-button">
              <Link to="/app/settings/security">Aktif Oturumlara Git</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="space-y-4">
        <div>
          <h2 className="text-4xl font-semibold text-foreground">Ayarlar</h2>
          <p className="mt-2 text-base text-muted-foreground">Kullanıcı, rol ve güvenlik bölümleri.</p>
        </div>

        <SettingsSectionNav showUsersSection />

        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-xl font-semibold text-foreground">Kullanıcılar</h3>
            <p className="text-sm text-muted-foreground">Kullanıcı ve rol yönetimi.</p>
          </div>
          <Button onClick={() => setOpenUser(true)} className="gap-2" data-testid="user-new">
            <UserPlus className="h-4 w-4" />
            Kullanıcı
          </Button>
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" data-testid="settings-error">
          {error}
        </div>
      ) : null}

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Settings className="h-4 w-4 text-muted-foreground" />
            Kullanıcılar
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table data-testid="users-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Ad</TableHead>
                  <TableHead>Roller</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={3} className="py-6 text-muted-foreground">
                      Kayıt yok.
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((u) => (
                    <TableRow key={u.id}>
                      <TableCell className="font-medium text-foreground">{u.email}</TableCell>
                      <TableCell className="text-foreground/80">{u.name || "-"}</TableCell>
                      <TableCell className="text-muted-foreground">{(u.roles || []).join(", ")}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <UserForm open={openUser} onOpenChange={setOpenUser} onSaved={load} />
    </div>
  );
}
