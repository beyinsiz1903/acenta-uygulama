import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";

export default function AgencyTourEditPage() {
  const { id } = useParams();
  const isNew = !id || id === "new";
  const nav = useNavigate();

  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(!isNew);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("0");
  const [currency, setCurrency] = useState("TRY");
  const [status, setStatus] = useState("draft");
  const [imagesText, setImagesText] = useState("");

  useEffect(() => {
    if (isNew) return;
    let alive = true;
    async function load() {
      setLoading(true);
      try {
        const resp = await api.get("/agency/tours");
        const list = Array.isArray(resp.data) ? resp.data : [];
        const item = list.find((x) => x.id === id);
        if (!alive) return;
        if (!item) {
          setLoading(false);
          return;
        }
        setTitle(item.title || "");
        setDescription(item.description || "");
        setPrice(String(item.price ?? 0));
        setCurrency(item.currency || "TRY");
        setStatus(item.status || "draft");
        setImagesText(Array.isArray(item.images) ? item.images.join("\n") : "");
      } catch (e) {
        console.error(apiErrorMessage(e) || e);
      } finally {
        if (alive) setLoading(false);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, [id, isNew]);

  const imagesPreview = useMemo(() => {
    const urls = imagesText
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    return urls.slice(0, 6);
  }, [imagesText]);

  const save = async () => {
    if (!title.trim()) {
      alert("Başlık zorunlu");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        title: title.trim(),
        description,
        price: Number(price || 0),
        currency: (currency || "TRY").trim(),
        status,
        images: imagesText,
      };

      if (isNew) {
        await api.post("/agency/tours", payload);
      } else {
        await api.put(`/agency/tours/${id}`, payload);
      }
      nav("/app/agency/tours");
    } catch (e) {
      alert(apiErrorMessage(e) || "Kaydedilemedi");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="max-w-3xl mx-auto p-4 text-sm text-gray-600">Yükleniyor…</div>;
  }

  return (
    <div className="max-w-3xl mx-auto p-4">
      <div className="flex items-center justify-between gap-3 mb-4">
        <h1 className="text-xl font-semibold">{isNew ? "Yeni Tur" : "Tur Düzenle"}</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => nav(-1)} disabled={saving}>
            Geri
          </Button>
          <Button onClick={save} disabled={saving}>
            {saving ? "Kaydediliyor…" : "Kaydet"}
          </Button>
        </div>
      </div>

      <div className="rounded-xl border bg-white p-4 space-y-4">
        <div>
          <div className="text-sm font-medium mb-1">Başlık</div>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Örn: Sapanca Göl Turu"
          />
        </div>

        <div>
          <div className="text-sm font-medium mb-1">Açıklama</div>
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={5}
            placeholder="Tur açıklaması..."
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <div className="text-sm font-medium mb-1">Fiyat</div>
            <Input value={price} onChange={(e) => setPrice(e.target.value)} />
          </div>
          <div>
            <div className="text-sm font-medium mb-1">Para Birimi</div>
            <Input value={currency} onChange={(e) => setCurrency(e.target.value)} />
          </div>
          <div>
            <div className="text-sm font-medium mb-1">Durum</div>
            <select
              className="w-full border rounded-md h-10 px-3"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="draft">Taslak</option>
              <option value="active">Aktif</option>
            </select>
          </div>
        </div>

        <div>
          <div className="text-sm font-medium mb-1">Görseller (her satır 1 URL)</div>
          <Textarea
            value={imagesText}
            onChange={(e) => setImagesText(e.target.value)}
            rows={6}
            placeholder={"https://...\nhttps://..."}
          />
          {imagesPreview.length > 0 && (
            <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-3">
              {imagesPreview.map((u, idx) => (
                <img
                  key={idx}
                  src={u}
                  alt={`preview-${idx}`}
                  className="h-24 w-full object-cover rounded-lg border"
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
