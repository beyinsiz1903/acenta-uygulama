import React, { useEffect, useState } from "react";
import { Settings, UserPlus } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";

function UserForm({ open, onOpenChange, onSaved }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("pass123");
  const [roles, setRoles] = useState("sales");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setEmail("");
      setName("");
      setPassword("pass123");
      setRoles("sales");
      setError("");
    }
  }, [open]);

  async function save() {
    setLoading(true);
    setError("");
    try {
      await api.post("/settings/users", {
        email,
        name,
        password,
        roles: roles.split(",").map((s) => s.trim()).filter(Boolean),
        agency_id: null,
      });
      onSaved?.();
      onOpenChange(false);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Yeni Kullanıcı</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Email</Label>
            <Input value={email} onChange={(e) => setEmail(e.target.value)} data-testid="user-email" />
          </div>
          <div className="space-y-2">
            <Label>Ad</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} data-testid="user-name" />
          </div>
          <div className="space-y-2">
            <Label>Şifre</Label>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} data-testid="user-password" />
          </div>
          <div className="space-y-2">
            <Label>Roller (virgülle)</Label>
            <Input value={roles} onChange={(e) => setRoles(e.target.value)} data-testid="user-roles" />
            <div className="text-xs text-slate-500">Örn: admin,sales,ops,accounting</div>
          </div>

          {error ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="user-error">
              {error}
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Vazgeç
          </Button>
          <Button onClick={save} disabled={loading} data-testid="user-save">
            {loading ? "Kaydediliyor..." : "Kaydet"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function SettingsPage() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [openUser, setOpenUser] = useState(false);

  async function load() {
    setError("");
    try {
      const resp = await api.get("/settings/users");
      setUsers(resp.data || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Ayarlar</h2>
          <p className="text-sm text-slate-600">Kullanıcı ve rol yönetimi.</p>
        </div>
        <Button onClick={() => setOpenUser(true)} className="gap-2" data-testid="user-new">
          <UserPlus className="h-4 w-4" />
          Kullanıcı
        </Button>
      </div>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" data-testid="settings-error">
          {error}
        </div>
      ) : null}

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Settings className="h-4 w-4 text-slate-500" />
            Kullanıcılar
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="users-table">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="py-2">Email</th>
                  <th className="py-2">Ad</th>
                  <th className="py-2">Roller</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="py-6 text-slate-500">Kayıt yok.</td>
                  </tr>
                ) : (
                  users.map((u) => (
                    <tr key={u.id} className="border-t">
                      <td className="py-3 font-medium text-slate-900">{u.email}</td>
                      <td className="py-3 text-slate-700">{u.name || "-"}</td>
                      <td className="py-3 text-slate-600">{(u.roles || []).join(", ")}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <UserForm open={openUser} onOpenChange={setOpenUser} onSaved={load} />
    </div>
  );
}
