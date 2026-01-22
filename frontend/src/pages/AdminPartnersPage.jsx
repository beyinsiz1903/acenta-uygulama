import React, { useEffect, useState } from "react";
import { AlertCircle, Loader2, Users } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../components/ui/dialog";

function StatusBadge({ status }) {
  const s = (status || "").toLowerCase();
  if (s === "approved") {
    return (
      <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
        Onaylı
      </Badge>
    );
  }
  if (s === "blocked") {
    return <Badge variant="destructive">Engelli</Badge>;
  }
  return <Badge variant="outline">Beklemede</Badge>;
}

export default function AdminPartnersPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [name, setName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [apiKeyName, setApiKeyName] = useState("");
  const [defaultMarkup, setDefaultMarkup] = useState("0");
  const [notes, setNotes] = useState("");
  const [creating, setCreating] = useState(false);

  const [statusFilter, setStatusFilter] = useState("");
  const [summaryPartner, setSummaryPartner] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get("/admin/partners");
      setItems(res.data || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const resetForm = () => {
    setName("");
    setContactEmail("");
    setApiKeyName("");
    setDefaultMarkup("0");
    setNotes("");
  };

  const create = async (e) => {
    e.preventDefault();
    setError("");
    if (!name.trim()) {
      setError("Partner adı zorunludur.");
      return;
    }
    setCreating(true);
    try {
      const payload = {
        name: name.trim(),
        contact_email: contactEmail.trim() || null,
        api_key_name: apiKeyName.trim() || null,
        default_markup_percent: parseFloat(defaultMarkup || "0") || 0,
        notes: notes.trim() || null,
        status: "pending",
      };
      await api.post("/admin/partners", payload);
      resetForm();
      await load();
    } catch (e2) {
      setError(apiErrorMessage(e2));
    } finally {
      setCreating(false);
    }
  };

  const updateStatus = async (id, status) => {
    setError("");
    try {
      await api.patch(`/admin/partners/${id}`, { status });
      await load();
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Users className="h-5 w-5" />
        <div>
          <h1 className="text-lg font-semibold">Partnerler & Marketplace</h1>
          <p className="text-xs text-muted-foreground">
            Agentis.pro benzeri bir ağ için partner profillerinizi yönetin. Bu ekranda partner temel
            bilgilerini, durumunu ve varsayılan B2B markup oranlarını yapılandırabilirsiniz.
          </p>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
          <AlertCircle className="h-4 w-4 mt-0.5" />
          <div>{error}</div>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Yeni Partner</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={create} className="space-y-3 text-xs">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="space-y-1">
                <Label htmlFor="name">Partner adı</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Örn: Demo Turizm AŞ"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="email">İletişim e-posta</Label>
                <Input
                  id="email"
                  value={contactEmail}
                  onChange={(e) => setContactEmail(e.target.value)}
                  placeholder="opsiyonel: partner@example.com"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="apikey">API key adı</Label>
                <Input
                  id="apikey"
                  value={apiKeyName}
                  onChange={(e) => setApiKeyName(e.target.value)}
                  placeholder="opsiyonel: PARTNER-TR-01"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="space-y-1">
                <Label htmlFor="markup">Varsayılan B2B markup (%)</Label>
                <Input
                  id="markup"
                  type="number"
                  value={defaultMarkup}
                  onChange={(e) => setDefaultMarkup(e.target.value)}
                  placeholder="0"
                />
                <p className="text-[11px] text-muted-foreground">
                  Pozitif değerler partner satış fiyatına eklenecek marjı temsil eder.
                </p>
              </div>
              <div className="space-y-1 md:col-span-2">
                <Label htmlFor="notes">Notlar</Label>
                <Input
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="opsiyonel: sözleşme notları, özel koşullar vb."
                />
              </div>
            </div>

            <div className="flex justify-end">
              <Button type="submit" size="sm" disabled={creating}>
                {creating && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                Partner oluştur
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center justify-between">
            <span>Partner listesi</span>
            {loading && (
              <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" /> Yükleniyor...
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {items.length === 0 && !loading ? (
            <p className="text-xs text-muted-foreground">
              Henüz partner tanımlı değil. Yukarıdaki formdan ilk partnerinizi oluşturabilirsiniz.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Partner</TableHead>
                    <TableHead className="text-xs">E-posta</TableHead>
                    <TableHead className="text-xs">Durum</TableHead>
                    <TableHead className="text-xs">API key adı</TableHead>
                    <TableHead className="text-xs text-right">Vars. markup (%)</TableHead>
                    <TableHead className="text-xs text-right">İşlemler</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell className="text-xs">
                        <div className="flex flex-col">
                          <span className="font-medium truncate max-w-[220px]">{p.name}</span>
                          {p.notes && (
                            <span className="text-[10px] text-muted-foreground truncate max-w-[260px]">
                              {p.notes}
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs">
                        {p.contact_email || <span className="text-muted-foreground">-</span>}
                      </TableCell>
                      <TableCell className="text-xs">
                        <StatusBadge status={p.status} />
                      </TableCell>
                      <TableCell className="text-xs font-mono">
                        {p.api_key_name || <span className="text-muted-foreground">-</span>}
                      </TableCell>
                      <TableCell className="text-xs text-right">
                        {typeof p.default_markup_percent === "number"
                          ? p.default_markup_percent.toFixed(1)
                          : "0.0"}
                      </TableCell>
                      <TableCell className="text-xs text-right">
                        <div className="inline-flex gap-1">
                          <Button
                            type="button"
                            size="xs"
                            variant="outline"
                            className="h-6 px-2 text-[10px]"
                            onClick={() => updateStatus(p.id, "approved")}
                          >
                            Onayla
                          </Button>
                          <Button
                            type="button"
                            size="xs"
                            variant="outline"
                            className="h-6 px-2 text-[10px]"
                            onClick={() => updateStatus(p.id, "blocked")}
                          >
                            Engelle
                          </Button>
                          <Button
                            type="button"
                            size="xs"
                            variant="outline"
                            className="h-6 px-2 text-[10px]"
                            onClick={() => updateStatus(p.id, "pending")}
                          >
                            Beklemeye al
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
