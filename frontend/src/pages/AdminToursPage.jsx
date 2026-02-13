import React, { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import {
  Plus, Trash2, Edit2, Upload, X, MapPin, Clock,
  Globe, Save, Loader2, ArrowLeft, CheckCircle,
  Image as ImageIcon,
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

function formatPrice(price, currency) {
  if (!price) return "-";
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency: currency || "EUR", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(price);
}

const EMPTY_TOUR = {
  name: "", description: "", destination: "", departure_city: "", category: "",
  base_price: 0, currency: "EUR", status: "active", duration_days: 1,
  max_participants: 0, cover_image: "", images: [], itinerary: [],
  includes: [], excludes: [], highlights: [],
};

export default function AdminToursPage() {
  const [tours, setTours] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [view, setView] = useState("list");
  const [selectedTour, setSelectedTour] = useState(null);
  const [form, setForm] = useState({ ...EMPTY_TOUR });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [uploading, setUploading] = useState(false);

  const loadTours = useCallback(async () => {
    setLoading(true);
    try { const res = await api.get("/admin/tours"); setTours(res.data || []); }
    catch(e) { setError("Turlar yuklenirken hata olustu."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadTours(); }, [loadTours]);

  const handleCreate = () => { setForm({ ...EMPTY_TOUR }); setSelectedTour(null); setView("create"); setSaveError(""); };

  const handleEdit = (tour) => {
    setForm({
      name: tour.name || "", description: tour.description || "",
      destination: tour.destination || "", departure_city: tour.departure_city || "",
      category: tour.category || "", base_price: tour.base_price || 0,
      currency: tour.currency || "EUR", status: tour.status || "active",
      duration_days: tour.duration_days || 1, max_participants: tour.max_participants || 0,
      cover_image: tour.cover_image || "", images: tour.images || [],
      itinerary: tour.itinerary || [], includes: tour.includes || [],
      excludes: tour.excludes || [], highlights: tour.highlights || [],
    });
    setSelectedTour(tour); setView("edit"); setSaveError("");
  };

  const handleDelete = async (tourId) => {
    if (!window.confirm("Bu turu silmek istediginizden emin misiniz?")) return;
    try { await api.delete("/admin/tours/" + tourId); await loadTours(); }
    catch(e) { alert("Tur silinirken hata olustu."); }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) { setSaveError("Tur adi zorunludur."); return; }
    setSaving(true); setSaveError("");
    try {
      if (view === "edit" && selectedTour) { await api.put("/admin/tours/" + selectedTour.id, form); }
      else { await api.post("/admin/tours", form); }
      await loadTours(); setView("list");
    } catch (err) { setSaveError(err?.response?.data?.message || "Kaydetme hatasi."); }
    finally { setSaving(false); }
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const res = await api.post("/admin/tours/upload-image", fd, { headers: { "Content-Type": "multipart/form-data" } });
      if (res.data?.url) {
        if (!form.cover_image) setForm((f) => ({ ...f, cover_image: res.data.url }));
        setForm((f) => ({ ...f, images: [...f.images, res.data.url] }));
      }
    } catch(e) { alert("Resim yuklenirken hata olustu."); }
    finally { setUploading(false); e.target.value = ""; }
  };

  const removeImage = (idx) => {
    const newImages = form.images.filter((_, i) => i !== idx);
    setForm((f) => ({ ...f, images: newImages, cover_image: f.cover_image === f.images[idx] ? (newImages[0] || "") : f.cover_image }));
  };
  const setCoverImg = (url) => setForm((f) => ({ ...f, cover_image: url }));
  const addItineraryDay = () => setForm((f) => ({ ...f, itinerary: [...f.itinerary, { title: (f.itinerary.length + 1) + ". Gun", description: "" }] }));
  const updateItineraryDay = (idx, field, value) => { const items = [...form.itinerary]; items[idx] = { ...items[idx], [field]: value }; setForm((f) => ({ ...f, itinerary: items })); };
  const removeItineraryDay = (idx) => setForm((f) => ({ ...f, itinerary: f.itinerary.filter((_, i) => i !== idx) }));
  const addListItem = (field) => setForm((f) => ({ ...f, [field]: [...f[field], ""] }));
  const updateListItem = (field, idx, value) => { const items = [...form[field]]; items[idx] = value; setForm((f) => ({ ...f, [field]: items })); };
  const removeListItem = (field, idx) => setForm((f) => ({ ...f, [field]: f[field].filter((_, i) => i !== idx) }));
  const resolveImg = (src) => !src ? "" : src.startsWith("/api/") ? BACKEND_URL + src : src;

  if (view === "list") {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div><h1 className="text-2xl font-bold">Tur Yonetimi</h1><p className="text-sm text-muted-foreground">{tours.length} tur kayitli</p></div>
          <Button onClick={handleCreate}><Plus className="h-4 w-4 mr-1" />Yeni Tur</Button>
        </div>
        {loading && <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>}
        {error && <p className="text-red-500 text-sm">{error}</p>}
        {!loading && tours.length === 0 && (
          <Card className="p-8 text-center">
            <Globe className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="font-semibold mb-1">Henuz tur yok</h3>
            <p className="text-sm text-muted-foreground mb-4">Yeni tur ekleyerek baslayabilirsiniz.</p>
            <Button onClick={handleCreate}><Plus className="h-4 w-4 mr-1" />Ilk Turu Olustur</Button>
          </Card>
        )}
        {tours.length > 0 && (
          <div className="grid gap-4">
            {tours.map((tour) => {
              const coverUrl = tour.cover_image ? resolveImg(tour.cover_image) : "";
              return (
                <Card key={tour.id} className="flex overflow-hidden hover:shadow-md transition">
                  <div className="w-32 h-24 flex-shrink-0 bg-muted">
                    {coverUrl ? <img src={coverUrl} alt={tour.name} className="w-full h-full object-cover" /> :
                      <div className="w-full h-full flex items-center justify-center"><ImageIcon className="h-8 w-8 text-muted-foreground/30" /></div>}
                  </div>
                  <div className="flex-1 p-3 flex items-center justify-between">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-sm truncate">{tour.name}</h3>
                        <Badge variant={tour.status === "active" ? "default" : "secondary"} className="text-xs">{tour.status === "active" ? "Aktif" : "Pasif"}</Badge>
                        {tour.category && <Badge variant="outline" className="text-xs">{tour.category}</Badge>}
                      </div>
                      <div className="flex gap-3 text-xs text-muted-foreground">
                        {tour.destination && <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{tour.destination}</span>}
                        {tour.duration_days > 0 && <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{tour.duration_days} gun</span>}
                        <span className="font-medium text-foreground">{formatPrice(tour.base_price, tour.currency)}</span>
                      </div>
                    </div>
                    <div className="flex gap-1 flex-shrink-0">
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleEdit(tour)}><Edit2 className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500" onClick={() => handleDelete(tour.id)}><Trash2 className="h-4 w-4" /></Button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => setView("list")}><ArrowLeft className="h-4 w-4 mr-1" />Geri</Button>
        <h1 className="text-xl font-bold">{view === "edit" ? "Tur Duzenle" : "Yeni Tur Olustur"}</h1>
      </div>
      <form onSubmit={handleSave} className="space-y-6">
        <Card className="p-6 space-y-4">
          <h2 className="font-semibold text-lg">Temel Bilgiler</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1"><Label>Tur Adi *</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Ornek: Kapadokya Kultur Turu" required /></div>
            <div className="space-y-1"><Label>Kategori</Label><Input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="Ornek: Kultur, Deniz..." /></div>
            <div className="space-y-1"><Label>Destinasyon</Label><Input value={form.destination} onChange={(e) => setForm({ ...form, destination: e.target.value })} placeholder="Ornek: Kapadokya" /></div>
            <div className="space-y-1"><Label>Kalkis Sehri</Label><Input value={form.departure_city} onChange={(e) => setForm({ ...form, departure_city: e.target.value })} placeholder="Ornek: Istanbul" /></div>
            <div className="space-y-1"><Label>Sure (Gun)</Label><Input type="number" min={1} value={form.duration_days} onChange={(e) => setForm({ ...form, duration_days: parseInt(e.target.value) || 1 })} /></div>
            <div className="space-y-1"><Label>Maks. Katilimci</Label><Input type="number" min={0} value={form.max_participants} onChange={(e) => setForm({ ...form, max_participants: parseInt(e.target.value) || 0 })} placeholder="0 = sinir yok" /></div>
            <div className="space-y-1"><Label>Kisi Basi Fiyat</Label><Input type="number" min={0} step="0.01" value={form.base_price} onChange={(e) => setForm({ ...form, base_price: parseFloat(e.target.value) || 0 })} /></div>
            <div className="space-y-1"><Label>Para Birimi</Label>
              <select className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}>
                <option value="EUR">EUR</option><option value="USD">USD</option><option value="TRY">TRY</option><option value="GBP">GBP</option>
              </select></div>
            <div className="space-y-1"><Label>Durum</Label>
              <select className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                <option value="active">Aktif</option><option value="inactive">Pasif</option><option value="draft">Taslak</option>
              </select></div>
          </div>
          <div className="space-y-1"><Label>Aciklama</Label>
            <textarea className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[100px]" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Tur hakkinda detayli aciklama..." />
          </div>
        </Card>
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-lg">Resimler</h2>
            <label className="cursor-pointer">
              <input type="file" accept="image/*" className="hidden" onChange={handleImageUpload} disabled={uploading} />
              <span className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm cursor-pointer hover:bg-accent">
                {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />} Resim Yukle
              </span>
            </label>
          </div>
          {form.images.length === 0 ? (
            <div className="border-2 border-dashed rounded-lg p-8 text-center">
              <ImageIcon className="h-8 w-8 mx-auto text-muted-foreground/40 mb-2" />
              <p className="text-sm text-muted-foreground">Henuz resim eklenmemis.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {form.images.map((img, i) => (
                <div key={i} className="relative group rounded-lg overflow-hidden border">
                  <img src={resolveImg(img)} alt={"Tour " + (i+1)} className="w-full h-24 object-cover" />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition flex items-center justify-center gap-1 opacity-0 group-hover:opacity-100">
                    <button type="button" className="bg-white rounded-full p-1.5 shadow" onClick={() => setCoverImg(img)}>
                      <CheckCircle className={"h-3.5 w-3.5 " + (form.cover_image === img ? "text-green-500" : "text-gray-600")} />
                    </button>
                    <button type="button" className="bg-white rounded-full p-1.5 shadow" onClick={() => removeImage(i)}>
                      <X className="h-3.5 w-3.5 text-red-500" />
                    </button>
                  </div>
                  {form.cover_image === img && <Badge className="absolute bottom-1 left-1 text-[10px] px-1.5 py-0">Kapak</Badge>}
                </div>
              ))}
            </div>
          )}
          <div className="space-y-1">
            <Label>URL ile resim ekle</Label>
            <div className="flex gap-2">
              <Input id="img-url-input" placeholder="https://example.com/resim.jpg" />
              <Button type="button" variant="outline" size="sm" onClick={() => {
                const input = document.getElementById("img-url-input");
                const url = input?.value?.trim();
                if (url) {
                  if (!form.cover_image) setForm((f) => ({ ...f, cover_image: url, images: [...f.images, url] }));
                  else setForm((f) => ({ ...f, images: [...f.images, url] }));
                  if (input) input.value = "";
                }
              }}>Ekle</Button>
            </div>
          </div>
        </Card>
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-lg">One Cikan Ozellikler</h2>
            <Button type="button" variant="outline" size="sm" onClick={() => addListItem("highlights")}><Plus className="h-4 w-4 mr-1" />Ekle</Button>
          </div>
          {form.highlights.length === 0 ? <p className="text-sm text-muted-foreground">Henuz ozellik eklenmemis.</p> : (
            <div className="space-y-2">{form.highlights.map((h, i) => (
              <div key={i} className="flex gap-2">
                <Input value={h} onChange={(e) => updateListItem("highlights", i, e.target.value)} placeholder="Ornek: Profesyonel rehber" />
                <Button type="button" variant="ghost" size="icon" onClick={() => removeListItem("highlights", i)}><X className="h-4 w-4" /></Button>
              </div>
            ))}</div>
          )}
        </Card>
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-lg">Tur Programi (Gun Gun)</h2>
            <Button type="button" variant="outline" size="sm" onClick={addItineraryDay}><Plus className="h-4 w-4 mr-1" />Gun Ekle</Button>
          </div>
          {form.itinerary.length === 0 ? <p className="text-sm text-muted-foreground">Henuz program eklenmemis.</p> : (
            <div className="space-y-4">{form.itinerary.map((day, i) => (
              <div key={i} className="border rounded-lg p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-primary">{i + 1}. Gun</span>
                  <Button type="button" variant="ghost" size="icon" className="h-7 w-7" onClick={() => removeItineraryDay(i)}><Trash2 className="h-3.5 w-3.5 text-red-500" /></Button>
                </div>
                <Input value={day.title || ""} onChange={(e) => updateItineraryDay(i, "title", e.target.value)} placeholder="Gun basligi" />
                <textarea className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[60px]" value={day.description || ""} onChange={(e) => updateItineraryDay(i, "description", e.target.value)} placeholder="Gun aciklamasi..." />
              </div>
            ))}</div>
          )}
        </Card>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-base text-green-600">Fiyata Dahil</h2>
              <Button type="button" variant="outline" size="sm" onClick={() => addListItem("includes")}><Plus className="h-3.5 w-3.5" /></Button>
            </div>
            {form.includes.length === 0 ? <p className="text-sm text-muted-foreground">Ekle butonuna tiklayin.</p> : (
              <div className="space-y-2">{form.includes.map((item, i) => (
                <div key={i} className="flex gap-2">
                  <Input value={item} onChange={(e) => updateListItem("includes", i, e.target.value)} placeholder="Ornek: Ulasim" />
                  <Button type="button" variant="ghost" size="icon" onClick={() => removeListItem("includes", i)}><X className="h-4 w-4" /></Button>
                </div>
              ))}</div>
            )}
          </Card>
          <Card className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-base text-red-600">Fiyata Dahil Degil</h2>
              <Button type="button" variant="outline" size="sm" onClick={() => addListItem("excludes")}><Plus className="h-3.5 w-3.5" /></Button>
            </div>
            {form.excludes.length === 0 ? <p className="text-sm text-muted-foreground">Ekle butonuna tiklayin.</p> : (
              <div className="space-y-2">{form.excludes.map((item, i) => (
                <div key={i} className="flex gap-2">
                  <Input value={item} onChange={(e) => updateListItem("excludes", i, e.target.value)} placeholder="Ornek: Kisisel harcamalar" />
                  <Button type="button" variant="ghost" size="icon" onClick={() => removeListItem("excludes", i)}><X className="h-4 w-4" /></Button>
                </div>
              ))}</div>
            )}
          </Card>
        </div>
        {saveError && <p className="text-sm text-red-500">{saveError}</p>}
        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={() => setView("list")}>Iptal</Button>
          <Button type="submit" disabled={saving}>
            {saving ? <><Loader2 className="h-4 w-4 animate-spin mr-1" />Kaydediliyor...</> : <><Save className="h-4 w-4 mr-1" />{view === "edit" ? "Guncelle" : "Olustur"}</>}
          </Button>
        </div>
      </form>
    </div>
  );
}
