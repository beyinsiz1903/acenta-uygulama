import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { api, apiErrorMessage } from "../lib/api";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";

export default function PublicTourDetailPage() {
  const { id } = useParams();
  const [tour, setTour] = useState(null);
  const [loading, setLoading] = useState(true);

  const [bookingOpen, setBookingOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [desiredDate, setDesiredDate] = useState("");
  const [pax, setPax] = useState("1");
  const [note, setNote] = useState("");

  // Gallery & lightbox state
  const images = useMemo(
    () =>
      (tour?.images || [])
        .map((img) => (typeof img === "string" ? img.trim() : ""))
        .filter(Boolean),
    [tour]
  );
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  // Load tour details
  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const resp = await api.get(`/public/tours/${id}`);
        if (!alive) return;
        setTour(resp.data || null);
      } catch (e) {
        console.error(apiErrorMessage(e) || e);
        if (!alive) return;
        setTour(null);
      } finally {
        if (alive) setLoading(false);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, [id]);

  const cover = useMemo(() => (images[0] ? images[0] : null), [images]);

  const openAt = useCallback(
    (index) => {
      if (!images.length) return;
      const safeIndex = ((index % images.length) + images.length) % images.length;
      setActiveIndex(safeIndex);
      setLightboxOpen(true);
    },
    [images.length]
  );

  const next = useCallback(() => {
    if (!images.length) return;
    openAt(activeIndex + 1);
  }, [activeIndex, images.length, openAt]);

  const prev = useCallback(() => {
    if (!images.length) return;
    openAt(activeIndex - 1);
  }, [activeIndex, images.length, openAt]);

  // Keyboard navigation when lightbox is open
  useEffect(() => {
    if (!lightboxOpen) return;

    const handler = (event) => {
      if (event.key === "ArrowRight") {
        event.preventDefault();
        next();
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        prev();
      } else if (event.key === "Escape") {
        event.preventDefault();
        setLightboxOpen(false);
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [lightboxOpen, next, prev]);

  const resetForm = () => {
    setFullName("");
    setPhone("");
    setEmail("");
    setDesiredDate("");
    setPax("1");
    setNote("");
  };

  const submitBooking = async (e) => {
    e.preventDefault();
    if (!id) return;
    if (!fullName.trim() || !phone.trim() || !desiredDate) {
      toast.error("Lütfen ad soyad, telefon ve tarih alanlarını doldurun.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post(`/public/tours/${id}/book`, {
        full_name: fullName.trim(),
        phone: phone.trim(),
        email: email.trim() || null,
        desired_date: desiredDate,
        pax: Number(pax || 1),
        note: note.trim() || null,
      });
      toast.success("Talebiniz alındı. Acenta en kısa sürede sizinle iletişime geçecek.");
      resetForm();
      setBookingOpen(false);
    } catch (e) {
      toast.error(apiErrorMessage(e) || "Talep oluşturulamadı");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-4 text-sm text-gray-600">Yükleniyor…</div>
    );
  }

  if (!tour) {
    return (
      <div className="max-w-4xl mx-auto p-4 text-sm text-gray-600">Tur bulunamadı.</div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="rounded-xl border overflow-hidden bg-white">
        <div className="h-56 bg-gray-100">
          {cover ? (
            <img src={cover} alt={tour.title} className="h-56 w-full object-cover" />
          ) : (
            <div className="h-56 w-full flex items-center justify-center text-sm text-gray-500">
              Görsel yok
            </div>
          )}
        </div>

        <div className="p-4">
          <h1 className="text-xl font-semibold">{tour.title}</h1>
          <div className="text-sm text-gray-600 mt-2 whitespace-pre-wrap">
            {tour.description || "—"}
          </div>

          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm">
              <span className="font-semibold">{tour.price ?? 0}</span>{" "}
              <span className="text-gray-600">{tour.currency || "TRY"}</span>
            </div>

            <Button onClick={() => setBookingOpen(true)}>Rezervasyon Yap</Button>
          </div>

          {images.length > 1 && (
            <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3">
              {images.map((url, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => openAt(idx)}
                  className={
                    "relative block focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 rounded-lg overflow-hidden" +
                    (idx === activeIndex ? " ring-2 ring-blue-500" : "")
                  }
                >
                  <img
                    src={url}
                    alt={`img-${idx}`}
                    className="h-20 w-full object-cover"
                  />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <Dialog open={bookingOpen} onOpenChange={setBookingOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rezervasyon Talebi</DialogTitle>
            <DialogDescription>
              {tour.title} turu için talep formunu doldurun; acenta en kısa sürede sizi arayacaktır.
            </DialogDescription>
          </DialogHeader>

          <form className="space-y-3 mt-2" onSubmit={submitBooking}>
            <div>
              <div className="text-xs font-medium mb-1">Ad Soyad</div>
              <Input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
            </div>

            <div>
              <div className="text-xs font-medium mb-1">Telefon</div>
              <Input value={phone} onChange={(e) => setPhone(e.target.value)} required />
            </div>
            <div>
              <div className="text-xs font-medium mb-1">E-posta (opsiyonel)</div>
              <Input value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <div className="text-xs font-medium mb-1">Tarih</div>
                <Input
                  type="date"
                  min={new Date().toISOString().slice(0, 10)}
                  value={desiredDate}
                  onChange={(e) => setDesiredDate(e.target.value)}
                  required
                />
              </div>
              <div>
                <div className="text-xs font-medium mb-1">Kişi sayısı</div>
                <Input
                  type="number"
                  min={1}
                  max={50}
                  value={pax}
                  onChange={(e) => setPax(e.target.value)}
                />
              </div>
            </div>
            <div>
              <div className="text-xs font-medium mb-1">Not</div>
              <Textarea
                rows={4}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Opsiyonel notunuz..."
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  resetForm();
                  setBookingOpen(false);
                }}
                disabled={submitting}
              >
                Vazgeç
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Gönderiliyor…" : "Talep Gönder"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Lightbox dialog for gallery */}
      <Dialog open={lightboxOpen} onOpenChange={setLightboxOpen}>
        <DialogContent className="max-w-3xl w-[95vw] p-4 sm:p-6">
          <div className="flex flex-col gap-3">
            {/* Top bar */}
            <div className="flex items-center justify-between text-xs sm:text-sm text-gray-600">
              <span className="font-medium truncate mr-2">{tour.title}</span>
              {images.length > 0 && (
                <span>
                  {activeIndex + 1} / {images.length}
                </span>
              )}
            </div>

            {/* Main image with arrows */}
            <div className="relative bg-black/80 rounded-lg flex items-center justify-center overflow-hidden min-h-[220px] sm:min-h-[320px]">
              {images.length > 0 && (
                <img
                  src={images[activeIndex]}
                  alt={`tour-image-${activeIndex}`}
                  className="max-h-[60vh] w-auto object-contain"
                />
              )}

              {images.length > 1 && (
                <>
                  <button
                    type="button"
                    onClick={prev}
                    className="absolute left-2 sm:left-3 top-1/2 -translate-y-1/2 rounded-full bg-white/80 hover:bg-white text-gray-800 shadow px-2 py-1 text-xs sm:text-sm"
                  >
                    
                    <span className="sr-only">Önceki</span>
                    ‹
                  </button>
                  <button
                    type="button"
                    onClick={next}
                    className="absolute right-2 sm:right-3 top-1/2 -translate-y-1/2 rounded-full bg-white/80 hover:bg-white text-gray-800 shadow px-2 py-1 text-xs sm:text-sm"
                  >
                    <span className="sr-only">Sonraki</span>
                    ›
                  </button>
                </>
              )}
            </div>

            {/* Thumbnails inside dialog */}
            {images.length > 1 && (
              <div className="mt-2 grid grid-cols-4 sm:grid-cols-6 gap-2">
                {images.map((url, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setActiveIndex(idx)}
                    className={
                      "relative block rounded-md overflow-hidden border" +
                      (idx === activeIndex ? " border-blue-600" : " border-transparent")
                    }
                  >
                    <img
                      src={url}
                      alt={`thumb-${idx}`}
                      className="h-14 w-full object-cover"
                    />
                  </button>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
