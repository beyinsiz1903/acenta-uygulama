import React, { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Loader2 } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function AdminCMSPagesPage() {
  const queryClient = useQueryClient();

  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [linkedCampaignSlug, setLinkedCampaignSlug] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const { data: pages = [], isLoading: loading, error: fetchError } = useQuery({
    queryKey: ["admin", "cms", "pages"],
    queryFn: async () => {
      const res = await api.get("/admin/cms/pages");
      return res.data?.items || [];
    },
    staleTime: 30_000,
  });
  const error = fetchError ? apiErrorMessage(fetchError) : "";

  async function handleCreate(e) {
    e.preventDefault();
    setFormError("");

    if (!slug.trim() || !title.trim()) {
      setFormError("Slug ve başlık zorunludur.");
      return;
    }

    setSaving(true);
    try {
      await api.post("/admin/cms/pages", {
        slug: slug.trim(),
        title: title.trim(),
        body,
        linked_campaign_slug: linkedCampaignSlug.trim() || null,
      });
      setSlug("");
      setTitle("");
      setBody("");
      setLinkedCampaignSlug("");
      queryClient.invalidateQueries({ queryKey: ["admin", "cms", "pages"] });
    } catch (e) {
      setFormError(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Sayfa Yönetimi</h1>
          <p className="text-sm text-muted-foreground mt-1">İçerik sayfaları yönetimi.</p>
        </div>
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Sayfalar yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Sayfa Yönetimi</h1>
          <p className="text-sm text-muted-foreground mt-1">İçerik sayfaları yönetimi.</p>
        </div>
        <div className="rounded-2xl border border-destructive/50 bg-destructive/5 p-8 flex flex-col items-center justify-center gap-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <div className="text-center">
            <p className="font-semibold text-foreground">Sayfalar yüklenemedi</p>
            <p className="text-sm text-muted-foreground mt-1">{error}</p>
          </div>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ["admin", "cms", "pages"] })}
            className="mt-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition"
          >
            Tekrar Dene
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Sayfa Yönetimi</h1>
        <p className="text-sm text-muted-foreground mt-1">Statik içerik sayfalarını (Hakkımızda vb.) yönetin.</p>
      </div>

      <div className="rounded-2xl border bg-card shadow-sm p-6">
        <h3 className="font-semibold mb-4">Yeni Sayfa Oluştur</h3>
        <form onSubmit={handleCreate} className="space-y-3">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <div className="space-y-1">
              <Label htmlFor="slug">Slug</Label>
              <Input
                id="slug"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="ornegin: hakkimizda"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="title">Başlık</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Örn: Hakkımızda"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="linked_campaign_slug">Bağlı Kampanya Slug</Label>
              <Input
                id="linked_campaign_slug"
                value={linkedCampaignSlug}
                onChange={(e) => setLinkedCampaignSlug(e.target.value)}
                placeholder="opsiyonel: yaz-firsatlari-2026"
              />
              <p className="text-xs text-muted-foreground">
                Bu sayfa kampanya landing olacaksa, ilgili kampanya slug girin.
              </p>
            </div>
          </div>
          <div className="space-y-1">
            <Label htmlFor="body">İçerik</Label>
            <textarea
              id="body"
              className="min-h-[120px] w-full rounded-md border bg-background px-2 py-1 text-sm"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Sayfa içeriği (markdown veya düz metin)..."
            />
          </div>
          {formError && <div className="text-xs text-destructive">{formError}</div>}
          <div className="flex justify-end">
            <Button type="submit" disabled={saving} className="gap-2">
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {saving ? "Kaydediliyor..." : "Sayfa Oluştur"}
            </Button>
          </div>
        </form>
      </div>

      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-semibold">Slug</TableHead>
              <TableHead className="font-semibold">Başlık</TableHead>
              <TableHead className="font-semibold">Yayın Durumu</TableHead>
              <TableHead className="font-semibold">Oluşturma</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pages.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-xs text-muted-foreground text-center py-6">
                  Henüz CMS sayfası yok.
                </TableCell>
              </TableRow>
            ) : (
              pages.map((page) => (
                <TableRow key={page.id}>
                  <TableCell className="font-mono text-xs">{page.slug}</TableCell>
                  <TableCell className="text-sm">{page.title}</TableCell>
                  <TableCell>
                    {page.published ? (
                      <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
                        Yayında
                      </Badge>
                    ) : (
                      <Badge variant="secondary">Taslak</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {page.created_at ? String(page.created_at).slice(0, 10) : "-"}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
