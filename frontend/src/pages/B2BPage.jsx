import React, { useCallback, useEffect, useState } from "react";
import { Building2, Plus, UserPlus } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
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

function AgencyForm({ open, onOpenChange, onSaved }) {
  const [name, setName] = useState("");
  const [discount, setDiscount] = useState(5);
  const [commission, setCommission] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setName("");
      setDiscount(5);
      setCommission(10);
      setError("");
    }
  }, [open]);

  async function save() {
    setLoading(true);
    setError("");
    try {
      await api.post("/b2b/agencies", {
        name,
        discount_percent: Number(discount || 0),
        commission_percent: Number(commission || 0),
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
          <DialogTitle>Yeni Acente</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Acente Adı</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} data-testid="agency-name" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>İndirim (%)</Label>
              <Input type="number" value={discount} onChange={(e) => setDiscount(e.target.value)} data-testid="agency-discount" />
            </div>
            <div className="space-y-2">
              <Label>Komisyon (%)</Label>
              <Input type="number" value={commission} onChange={(e) => setCommission(e.target.value)} data-testid="agency-commission" />
            </div>
          </div>

          {error ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="agency-error">
              {error}
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Vazgeç
          </Button>
          <Button onClick={save} disabled={loading} data-testid="agency-save">
            {loading ? "Kaydediliyor..." : "Kaydet"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AgentForm({ open, onOpenChange, agencies, onSaved }) {
  const [agencyId, setAgencyId] = useState("");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("agent123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setAgencyId(agencies[0]?.id || "");
      setEmail("");
      setName("");
      setPassword("agent123");
      setError("");
    }
  }, [open, agencies]);

  async function save() {
    setLoading(true);
    setError("");
    try {
      await api.post("/b2b/agents", {
        agency_id: agencyId,
        email,
        name,
        password,
        roles: ["b2b_agent"],
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
          <DialogTitle>Alt Acente Kullanıcısı Oluştur</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Acente</Label>
            <select
              className="w-full rounded-xl border bg-white px-3 py-2 text-sm"
              value={agencyId}
              onChange={(e) => setAgencyId(e.target.value)}
              data-testid="agent-agency"
            >
              {agencies.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>Email</Label>
              <Input value={email} onChange={(e) => setEmail(e.target.value)} data-testid="agent-email" />
            </div>
            <div className="space-y-2">
              <Label>Ad</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} data-testid="agent-name" />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Şifre</Label>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} data-testid="agent-password" />
          </div>

          {error ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="agent-error">
              {error}
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Vazgeç
          </Button>
          <Button onClick={save} disabled={loading} data-testid="agent-save">
            {loading ? "Kaydediliyor..." : "Kaydet"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function B2BPage() {
  const [agencies, setAgencies] = useState([]);
  const [error, setError] = useState("");
  const [openAgency, setOpenAgency] = useState(false);
  const [openAgent, setOpenAgent] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const resp = await api.get("/b2b/agencies");
      setAgencies(resp.data || []);
    } catch (e) {
      const msg = apiErrorMessage(e);
      // 404 / "Not Found" durumunda, liste boşmuş gibi davran; kırmızı hata göstermeyelim.
      if (e?.response?.status === 404 || (typeof msg === "string" && msg.toLowerCase().includes("not found"))) {
        setAgencies([]);
      } else {
        setError(msg);
      }
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      load();
    }, 0);
    return () => clearTimeout(t);
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">B2B / Acenteler</h2>
          <p className="text-sm text-muted-foreground">Alt acenteleri ve b2b_agent kullanıcılarını yönet.</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setOpenAgency(true)} className="gap-2" data-testid="b2b-new-agency">
            <Plus className="h-4 w-4" />
            Acente
          </Button>
          <Button variant="outline" onClick={() => setOpenAgent(true)} className="gap-2" data-testid="b2b-new-agent">
            <UserPlus className="h-4 w-4" />
            Kullanıcı
          </Button>
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" data-testid="b2b-error">
          {error}
        </div>
      ) : null}

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Building2 className="h-4 w-4 text-muted-foreground" />
            Acenteler
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table data-testid="agency-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Ad</TableHead>
                  <TableHead>İndirim</TableHead>
                  <TableHead>Komisyon</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agencies.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={3} className="py-6 text-muted-foreground">Kayıt yok.</TableCell>
                  </TableRow>
                ) : (
                  agencies.map((a) => (
                    <TableRow key={a.id}>
                      <TableCell className="font-medium text-foreground">{a.name}</TableCell>
                      <TableCell className="text-foreground/80">{a.discount_percent}%</TableCell>
                      <TableCell className="text-foreground/80">{a.commission_percent}%</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
          <div className="mt-3 text-xs text-muted-foreground">
            Not: b2b_agent kullanıcıları için “demo login” aynı giriş ekranından yapılır.
          </div>
        </CardContent>
      </Card>

      <AgencyForm open={openAgency} onOpenChange={setOpenAgency} onSaved={load} />
      <AgentForm open={openAgent} onOpenChange={setOpenAgent} agencies={agencies} onSaved={load} />
    </div>
  );
}
