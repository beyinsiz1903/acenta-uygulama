import React, { useEffect, useState } from "react";
import { AlertCircle, Megaphone, Plus } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

function AudienceBadge({ audience }) {
  if (audience === "agency") {
    return <Badge variant="secondary">Belirli acenta</Badge>;
  }
  return <Badge variant="outline">Tüm B2B acentalar</Badge>;
}

export default function AdminB2BAnnouncementsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState("all");
  const [agencyId, setAgencyId] = useState("");
  const [daysValid, setDaysValid] = useState("7");
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const res = await api.get("/admin/b2b/announcements");
      setItems(res.data?.items || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const payload = {
        title: title.trim(),
        body: body.trim(),
        audience,
        agency_id: audience === "agency" ? agencyId.trim() || null : null,
      };
      const days = parseInt(daysValid, 10);
      if (!Number.isNaN(days) && days > 0) {
        payload.days_valid = days;
      }
      await api.post("/admin/b2b/announcements", payload);
      setTitle("");
      setBody("");
      setAgencyId("");
      setDaysValid("7");
      await load();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  async function handleToggle(id) {
    try {
      await api.post(`/admin/b2b/announcements/${id}/toggle`);
      await load();
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-foreground">B2B Duyuruları</h1>
        <p className="text-sm text-muted-foreground">
          B2B portal giriş sayfasında gösterilecek basit duyuruları yönetin.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <Megaphone className="h-4 w-4" /> Yeni Duyuru Oluştur
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="space-y-3">
            <div className="space-y-1">
              <Label htmlFor="title">Başlık</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Örn: Ödeme vadelerinde güncelleme"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="body">Mesaj</Label>
              <textarea
                id="body"
                className="min-h-[80px] w-full rounded-md border bg-background px-2 py-1 text-sm"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="B2B acentalara gösterilecek mesaj..."
              />
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <div className="space-y-1">
                <Label htmlFor="audience">Hedef kitle</Label>
                <select
                  id="audience"
                  className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                >
                  <option value="all">Tüm B2B acentalar</option>
                  <option value="agency">Belirli acenta</option>
                </select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="agency_id">Acenta ID (opsiyonel)</Label>
                <Input
                  id="agency_id"
                  value={agencyId}
                  onChange={(e) => setAgencyId(e.target.value)}
                  placeholder="Sadece audience='agency' için zorunlu"
                  disabled={audience !== "agency"}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="days_valid">Geçerlilik (gün)</Label>
                <Input
                  id="days_valid"
                  type="number"
                  min={1}
                  value={daysValid}
                  onChange={(e) => setDaysValid(e.target.value)}
                />
              </div>
            </div>
            <div className="flex justify-end">
              <Button type="submit" disabled={saving} className="gap-2">
                <Plus className="h-4 w-4" />
                {saving ? "Kaydediliyor..." : "Duyuru Oluştur"}
              </Button>
            </div>
            {error && (
              <div className="mt-2 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
                <AlertCircle className="h-4 w-4 mt-0.5" />
                <div>{error}</div>
              </div>
            )}
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Mevcut Duyurular</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-xs text-muted-foreground">Yükleniyor...</p>
          ) : items.length === 0 ? (
            <p className="text-xs text-muted-foreground">Henüz tanımlı bir B2B duyurusu yok.</p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Başlık</TableHead>
                    <TableHead className="text-xs">Hedef</TableHead>
                    <TableHead className="text-xs">Aktif</TableHead>
                    <TableHead className="text-xs">Geçerlilik</TableHead>
                    <TableHead className="text-xs">Oluşturan</TableHead>
                    <TableHead className="text-xs text-right">Aksiyon</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((it) => (
                    <TableRow key={it.id}>
                      <TableCell className="text-xs max-w-[260px]">
                        <div className="font-medium truncate">{it.title}</div>
                        <div className="mt-1 text-xs text-muted-foreground line-clamp-2">{it.body}</div>
                      </TableCell>
                      <TableCell className="text-xs">
                        <AudienceBadge audience={it.audience} />
                      </TableCell>
                      <TableCell className="text-xs">
                        {it.is_active ? (
                          <Badge variant="secondary">Aktif</Badge>
                        ) : (
                          <Badge variant="outline">Pasif</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {it.valid_until ? `${it.valid_from?.slice(0, 10)} → ${it.valid_until?.slice(0, 10)}` : "Süresiz"}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {it.created_by || "-"}
                      </TableCell>
                      <TableCell className="text-xs text-right">
                        <Button
                          type="button"
                          size="xs"
                          variant="outline"
                          onClick={() => handleToggle(it.id)}
                        >
                          {it.is_active ? "Pasifleştir" : "Aktifleştir"}
                        </Button>
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
