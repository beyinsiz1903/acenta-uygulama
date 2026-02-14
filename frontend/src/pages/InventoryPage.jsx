import React, { useCallback, useContext, useEffect, useMemo, useState } from "react";
import { addMonths, endOfMonth, format, startOfMonth, subMonths } from "date-fns";
import { CalendarDays, ChevronLeft, ChevronRight, Edit3, Layers, Save, Sparkles, Table2 } from "lucide-react";
import { DayPicker } from "react-day-picker";

import { api, apiErrorMessage } from "../lib/api";
import { formatMoney } from "../lib/format";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "../components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { cn } from "../lib/utils";

const InventoryCtx = React.createContext({ invMap: new Map() });


function ymd(d) {
  return format(d, "yyyy-MM-dd");
}

function daysInMonth(date) {
  const d = startOfMonth(date);
  const out = [];
  while (d <= endOfMonth(date)) {
    out.push(new Date(d));
    d.setDate(d.getDate() + 1);
  }
  return out;
}

function CalendarDayCell({ date, activeModifiers, inv, cnFn }) {
  const cap = inv ? `${inv.capacity_available}/${inv.capacity_total}` : "-";
  const price = inv?.price;
  const closed = !!inv?.restrictions?.closed;

  return (
    <div
      className={cnFn(
        "flex h-10 w-10 flex-col items-center justify-center rounded-md border",
        activeModifiers.selected
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border hover:border-foreground/20",
        closed ? "bg-rose-50/50" : "bg-background"
      )}
    >
      <div className={cnFn("text-xs leading-none", activeModifiers.selected ? "text-primary-foreground" : "text-foreground")}>
        {date.getDate()}
      </div>
      <div
        className={cnFn(
          "mt-0.5 text-2xs leading-none",
          activeModifiers.selected
            ? "text-white/80"
            : closed
              ? "text-rose-700"
              : "text-muted-foreground"
        )}
      >
        {cap}
      </div>
      {price != null ? (
        <div className={cnFn("mt-0.5 text-2xs leading-none", activeModifiers.selected ? "text-primary-foreground" : "text-foreground/80")}>
          {Number(price).toFixed(0)}
        </div>
      ) : null}
    </div>
  );
}



function DayContent(props) {
  const { invMap } = useContext(InventoryCtx);
  const dateStr = ymd(props.date);
  const inv = invMap.get(dateStr);

  return <CalendarDayCell date={props.date} activeModifiers={props.activeModifiers} inv={inv} cnFn={cn} />;
}

export default function InventoryPage() {
  const [products, setProducts] = useState([]);
  const [productId, setProductId] = useState("");
  const [month, setMonth] = useState(() => new Date());
  const [view, setView] = useState("calendar"); // calendar | grid

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [openDay, setOpenDay] = useState(false);
  const [selectedDay, setSelectedDay] = useState(null);

  // Bulk update controls
  const [bulkStart, setBulkStart] = useState(ymd(new Date()));
  const [bulkEnd, setBulkEnd] = useState(ymd(new Date()));
  const [bulkCapTotal, setBulkCapTotal] = useState(20);
  const [bulkCapAvail, setBulkCapAvail] = useState(20);
  const [bulkPrice, setBulkPrice] = useState("");
  const [bulkClosed, setBulkClosed] = useState(false);
  const [bulkLoading, setBulkLoading] = useState(false);

  const start = useMemo(() => ymd(startOfMonth(month)), [month]);
  const end = useMemo(() => ymd(endOfMonth(month)), [month]);

  const invMap = useMemo(() => {
    const map = new Map();
    for (const r of rows) map.set(r.date, r);
    return map;
  }, [rows]);

  const loadProducts = useCallback(async () => {
    const resp = await api.get("/products");
    const list = resp.data || [];
    setProducts(list);
    setProductId((prev) => prev || list[0]?.id || "");
  }, []);

  const loadInventory = useCallback(
    async (pid) => {
      if (!pid) return;
      setLoading(true);
      setError("");
      try {
        const resp = await api.get("/inventory", {
          params: { product_id: pid, start, end },
        });
        setRows(resp.data || []);
      } catch (e) {
        const msg = apiErrorMessage(e);
        if (msg === "Not Found" || msg === "Request failed with status code 404") {
          setRows([]);
          setError("");
        } else {
          setError(msg);
        }
      } finally {
        setLoading(false);
      }
    },
    [start, end]
  );

  useEffect(() => {
    const t = setTimeout(() => {
      loadProducts().catch((e) => {
        const msg = apiErrorMessage(e);
        if (msg === "Not Found" || msg === "Request failed with status code 404") {
          setProducts([]);
          setProductId("");
          setError("");
        } else {
          setError(msg);
        }
      });
    }, 0);
    return () => clearTimeout(t);
  }, [loadProducts]);

  useEffect(() => {
    if (!productId) {
      setLoading(false);
      setRows([]);
      return;
    }
    const t = setTimeout(() => {
      loadInventory(productId);
    }, 0);
    return () => clearTimeout(t);
  }, [productId, month, loadInventory]);

  const selectedInv = useMemo(() => {
    if (!selectedDay) return null;
    return invMap.get(ymd(selectedDay)) || null;
  }, [invMap, selectedDay]);

  const dayEditorInitial = useMemo(() => {
    const d = selectedDay ? ymd(selectedDay) : "";
    return {
      date: d,
      capacity_total: selectedInv?.capacity_total ?? 0,
      capacity_available: selectedInv?.capacity_available ?? 0,
      price: selectedInv?.price ?? "",
      closed: !!selectedInv?.restrictions?.closed,
    };
  }, [selectedDay, selectedInv]);

  const [dayCapTotal, setDayCapTotal] = useState(0);
  const [dayCapAvail, setDayCapAvail] = useState(0);
  const [dayPrice, setDayPrice] = useState("");
  const [dayClosed, setDayClosed] = useState(false);
  const [daySaving, setDaySaving] = useState(false);

  useEffect(() => {
    setDayCapTotal(dayEditorInitial.capacity_total);
    setDayCapAvail(dayEditorInitial.capacity_available);
    setDayPrice(dayEditorInitial.price);
    setDayClosed(dayEditorInitial.closed);
  }, [dayEditorInitial]);

  async function saveDay() {
    if (!selectedDay) return;
    setDaySaving(true);
    try {
      await api.post("/inventory/upsert", {
        product_id: productId,
        date: ymd(selectedDay),
        capacity_total: Number(dayCapTotal || 0),
        capacity_available: Number(dayCapAvail || 0),
        price: dayPrice === "" || dayPrice === null ? null : Number(dayPrice),
        restrictions: { closed: !!dayClosed, cta: false, ctd: false },
      });
      await loadInventory(productId);
      setOpenDay(false);
    } catch (e) {
      alert(apiErrorMessage(e));
    } finally {
      setDaySaving(false);
    }
  }

  async function applyBulk() {
    if (!bulkStart || !bulkEnd || !productId) return;

    const summaryLines = [
      `Tarih aralığı: ${bulkStart} → ${bulkEnd}`,
      `Kapasite / Müsait: ${bulkCapTotal} / ${bulkCapAvail}`,
      `Fiyat: ${bulkPrice === "" || bulkPrice === null ? "(değişmeyecek / null)" : bulkPrice}`,
      `Günleri kapat: ${bulkClosed ? "Evet" : "Hayır"}`,
    ];

    const ok = window.confirm(
      "Aşağıdaki ayarlarla toplu işlem uygulamak üzeresiniz:\n\n" + summaryLines.join("\n") + "\n\nDevam etmek istiyor musunuz?"
    );
    if (!ok) return;

    setBulkLoading(true);
    try {
      await api.post("/inventory/bulk_upsert", {
        product_id: productId,
        start_date: bulkStart,
        end_date: bulkEnd,
        capacity_total: Number(bulkCapTotal || 0),
        capacity_available: Number(bulkCapAvail || 0),
        price: bulkPrice === "" || bulkPrice === null ? null : Number(bulkPrice),
        closed: !!bulkClosed,
      });
      await loadInventory(productId);
    } catch (e) {
      alert(apiErrorMessage(e));
    } finally {
      setBulkLoading(false);
    }
  }

  const monthDays = useMemo(() => daysInMonth(month), [month]);

  const gridRows = useMemo(() => {
    return monthDays.map((d) => {
      const date = ymd(d);
      const inv = invMap.get(date) || null;
      return {
        date,
        dow: format(d, "EEE"),
        capacity_total: inv?.capacity_total ?? 0,
        capacity_available: inv?.capacity_available ?? 0,
        price: inv?.price ?? null,
        closed: !!inv?.restrictions?.closed,
      };
    });
  }, [monthDays, invMap]);

  function openDayEditor(dateStr) {
    const parts = (dateStr || "").split("-");
    if (parts.length !== 3) return;
    const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    setSelectedDay(d);
    setOpenDay(true);
  }


  const modifiers = useMemo(() => {
    const closed = [];
    for (const r of rows) {
      if (r?.restrictions?.closed) {
        const parts = (r.date || "").split("-");
        if (parts.length === 3) {
          closed.push(new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2])));
        }
      }
    }
    return { closed };
  }, [rows]);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Müsaitlik & Kontenjan</h2>
          <p className="text-sm text-muted-foreground">
            Takvimden gün seçerek kapasite/fiyat düzenleyin veya tarih aralığına toplu uygulayın.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-8">
          <Card className="rounded-2xl shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <CalendarDays className="h-4 w-4 text-muted-foreground" />
                    Müsaitlik
                  </CardTitle>
                  <div className="mt-1 text-xs text-muted-foreground">Aralık: {start} → {end}</div>
                </div>

                <div className="flex flex-col md:flex-row gap-2 md:items-end">
                  <div className="space-y-2">
                    <Label>Ürün</Label>
                    <Select value={productId} onValueChange={setProductId}>
                      <SelectTrigger data-testid="inventory-product">
                        <SelectValue placeholder="Ürün seç" />
                      </SelectTrigger>
                      <SelectContent>
                        {products.map((p) => (
                          <SelectItem key={p.id} value={p.id}>
                            {p.title} ({p.type})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      className="gap-2"
                      onClick={() => setMonth((m) => subMonths(m, 1))}
                      data-testid="inventory-prev-month"
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Önceki
                    </Button>
                    <Button
                      variant="outline"
                      className="gap-2"
                      onClick={() => setMonth((m) => addMonths(m, 1))}
                      data-testid="inventory-next-month"
                    >
                      Sonraki
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>

                  <Button
                    variant="outline"
                    className="gap-2"
                    onClick={() => loadInventory(productId)}
                    data-testid="inventory-refresh"
                  >
                    <Layers className="h-4 w-4" />
                    Yenile
                  </Button>
                </div>
              </div>
            </CardHeader>

            <CardContent>
              {error && error !== "Not Found" ? (
                <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="inventory-error">
                  {error}
                </div>
              ) : null}

              <Tabs value={view} onValueChange={setView}>
                <TabsList className="mb-3">
                  <TabsTrigger value="calendar" className="gap-2" data-testid="inv-view-calendar">
                    <CalendarDays className="h-4 w-4" /> Takvim
                  </TabsTrigger>
                  <TabsTrigger value="grid" className="gap-2" data-testid="inv-view-grid">
                    <Table2 className="h-4 w-4" /> Grid
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="calendar">
                  <InventoryCtx.Provider value={{ invMap }}>
                    <div className="rounded-2xl border bg-white p-3">
                      <DayPicker
                      mode="single"
                      selected={selectedDay}
                      onSelect={(d) => {
                        if (!d) return;
                        setSelectedDay(d);
                        setOpenDay(true);
                      }}
                      month={month}
                      onMonthChange={setMonth}
                      showOutsideDays
                      modifiers={modifiers}
                      modifiersClassNames={{
                        closed: "bg-rose-50 text-rose-800 rounded-md",
                      }}
                      classNames={{
                        months: "flex flex-col space-y-4",
                        month: "space-y-4",
                        caption: "flex justify-center pt-1 relative items-center",
                        caption_label: "text-sm font-medium",
                        nav: "hidden",
                        table: "w-full border-collapse space-y-1",
                        head_row: "flex",
                        head_cell: "text-muted-foreground rounded-md w-10 font-normal text-[0.8rem]",
                        row: "flex w-full mt-2",
                        cell: "relative p-0 text-center text-sm w-10 h-10",
                        day: "h-10 w-10 p-0 font-normal aria-selected:opacity-100",
                      }}
                      components={{
                        DayContent: DayContent,
                      }}
                    />

                    {loading ? <div className="mt-3 text-sm text-muted-foreground">Yükleniyor...</div> : !productId ? (
                      <div className="mt-4 flex flex-col items-center gap-2 py-4 text-center">
                        <CalendarDays className="h-8 w-8 text-muted-foreground/40" />
                        <p className="text-sm font-medium text-muted-foreground">Henüz ürün yok</p>
                        <p className="text-xs text-muted-foreground/70">Müsaitlik takvimini görüntülemek için önce bir ürün oluşturun.</p>
                      </div>
                    ) : null}

                      <div className="mt-3 text-xs text-muted-foreground">
                        Hücre içeriği: <span className="font-medium">müsait/toplam</span> ve opsiyonel fiyat.
                      </div>
                    </div>
                  </InventoryCtx.Provider>
                </TabsContent>

                <TabsContent value="grid">
                  <div className="overflow-x-auto rounded-2xl border bg-card">
                    <Table data-testid="inventory-grid-table">
                      <TableHeader>
                        <TableRow>
                          <TableHead className="px-3">Tarih</TableHead>
                          <TableHead className="px-3">Gün</TableHead>
                          <TableHead className="px-3">Kapasite</TableHead>
                          <TableHead className="px-3">Müsait</TableHead>
                          <TableHead className="px-3">Fiyat</TableHead>
                          <TableHead className="px-3">Durum</TableHead>
                          <TableHead className="px-3 text-right">İşlem</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {loading ? (
                          <TableRow>
                            <TableCell colSpan={7} className="py-6 px-3 text-muted-foreground">
                              Yükleniyor...
                            </TableCell>
                          </TableRow>
                        ) : !productId ? (
                          <TableRow>
                            <TableCell colSpan={7} className="py-8 px-3 text-center text-muted-foreground">
                              <div className="flex flex-col items-center gap-2">
                                <CalendarDays className="h-8 w-8 text-muted-foreground/40" />
                                <p className="text-sm font-medium">Henüz ürün yok</p>
                                <p className="text-xs">Müsaitlik verisi görüntülemek için önce bir ürün oluşturun.</p>
                              </div>
                            </TableCell>
                          </TableRow>
                        ) : gridRows.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={7} className="py-8 px-3 text-center text-muted-foreground">
                              <div className="flex flex-col items-center gap-2">
                                <CalendarDays className="h-8 w-8 text-muted-foreground/40" />
                                <p className="text-sm font-medium">Bu ay için envanter verisi yok</p>
                                <p className="text-xs">Toplu güncelle bölümünden veri ekleyebilirsiniz.</p>
                              </div>
                            </TableCell>
                          </TableRow>
                        ) : (
                          gridRows.map((r) => (
                            <TableRow key={r.date}>
                              <TableCell className="px-3 font-medium text-foreground">{r.date}</TableCell>
                              <TableCell className="px-3 text-muted-foreground">{r.dow}</TableCell>
                              <TableCell className="px-3 text-foreground/80">{r.capacity_total}</TableCell>
                              <TableCell className="px-3 text-foreground/80">{r.capacity_available}</TableCell>
                              <TableCell className="px-3 text-foreground/80">
                                {r.price == null ? <span className="text-muted-foreground">(rate plan)</span> : formatMoney(r.price, "TRY")}
                              </TableCell>
                              <TableCell className="px-3">
                                <span
                                  className={cn(
                                    "rounded-full border px-2 py-1 text-xs font-medium",
                                    r.closed
                                      ? "border-rose-200 bg-rose-50 text-rose-700"
                                      : "border-emerald-200 bg-emerald-50 text-emerald-700"
                                  )}
                                >
                                  {r.closed ? "Kapalı" : "Açık"}
                                </span>
                              </TableCell>
                              <TableCell className="px-3 text-right">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => openDayEditor(r.date)}
                                  data-testid={`grid-open-${r.date}`}
                                >
                                  Düzenle
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>

        <div className="col-span-12 lg:col-span-4">
          <Card className="rounded-2xl shadow-sm">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-muted-foreground" />
                Toplu Güncelle
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Başlangıç</Label>
                  <Input type="date" value={bulkStart} onChange={(e) => setBulkStart(e.target.value)} data-testid="bulk-start" />
                </div>
                <div className="space-y-2">
                  <Label>Bitiş</Label>
                  <Input type="date" value={bulkEnd} onChange={(e) => setBulkEnd(e.target.value)} data-testid="bulk-end" />
                </div>
                <div className="space-y-2">
                  <Label>Kapasite</Label>
                  <Input type="number" value={bulkCapTotal} onChange={(e) => setBulkCapTotal(e.target.value)} data-testid="bulk-cap-total" />
                </div>
                <div className="space-y-2">
                  <Label>Müsait</Label>
                  <Input type="number" value={bulkCapAvail} onChange={(e) => setBulkCapAvail(e.target.value)} data-testid="bulk-cap-avail" />
                </div>
                <div className="space-y-2 col-span-2">
                  <Label>Fiyat (boş bırak → null)</Label>
                  <Input type="number" value={bulkPrice} onChange={(e) => setBulkPrice(e.target.value)} data-testid="bulk-price" />
                </div>
                <div className="col-span-2 flex items-center justify-between rounded-xl border bg-accent/40 px-3 py-2">
                  <div>
                    <div className="text-sm font-medium text-foreground">Günleri kapat</div>
                    <div className="text-xs text-muted-foreground">Seçili aralıkta satış kapalı</div>
                  </div>
                  <input type="checkbox" checked={bulkClosed} onChange={(e) => setBulkClosed(e.target.checked)} data-testid="bulk-closed" />
                </div>
              </div>

              <div className="mt-3">
                <Button onClick={applyBulk} disabled={bulkLoading || !productId} className="w-full gap-2" data-testid="bulk-apply">
                  {bulkLoading ? "Uygulanıyor..." : "Toplu Uygula"}
                </Button>
              </div>

              <div className="mt-3 text-xs text-muted-foreground space-y-1">
                <div>
                  Özet: {bulkStart} → {bulkEnd}, Kapasite/Müsait: {bulkCapTotal}/{bulkCapAvail}, Günleri kapat: {bulkClosed ? "Evet" : "Hayır"}
                </div>
                <div>Not: Bu işlem her gün için upsert yapar.</div>
              </div>
            </CardContent>
          </Card>

          <Card className="mt-4 rounded-2xl shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">Seçili Gün Özeti</CardTitle>
            </CardHeader>
            <CardContent>
              {selectedDay ? (
                <div className="space-y-2 text-sm">
                  <div className="font-semibold text-foreground" data-testid="day-summary-date">{ymd(selectedDay)}</div>
                  <div className="text-foreground/80">Kapasite: {selectedInv?.capacity_total ?? 0}</div>
                  <div className="text-foreground/80">Müsait: {selectedInv?.capacity_available ?? 0}</div>
                  <div className="text-foreground/80">Fiyat: {selectedInv?.price != null ? formatMoney(selectedInv.price, "TRY") : "(rate plan)"}</div>
                  <div className={cn("text-sm", selectedInv?.restrictions?.closed ? "text-rose-700" : "text-foreground/80")}>
                    Durum: {selectedInv?.restrictions?.closed ? "Kapalı" : "Açık"}
                  </div>
                  <Button
                    variant="outline"
                    className="w-full gap-2"
                    onClick={() => setOpenDay(true)}
                    disabled={!selectedDay}
                    data-testid="day-open-editor"
                  >
                    <Edit3 className="h-4 w-4" />
                    Düzenle
                  </Button>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">Takvimden bir gün seçin.</div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <Sheet open={openDay} onOpenChange={setOpenDay}>
        <SheetContent side="right" className="sm:max-w-xl" data-testid="inventory-day-drawer">
          <SheetHeader>
            <SheetTitle>Gün Düzenle</SheetTitle>
            <div className="text-xs text-muted-foreground">{selectedDay ? ymd(selectedDay) : "-"}</div>
          </SheetHeader>

          <div className="mt-5 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Kapasite</Label>
                <Input type="number" value={dayCapTotal} onChange={(e) => setDayCapTotal(e.target.value)} data-testid="day-cap-total" />
              </div>
              <div className="space-y-2">
                <Label>Müsait</Label>
                <Input type="number" value={dayCapAvail} onChange={(e) => setDayCapAvail(e.target.value)} data-testid="day-cap-avail" />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Fiyat (boş bırak → null)</Label>
              <Input type="number" value={dayPrice} onChange={(e) => setDayPrice(e.target.value)} data-testid="day-price" />
            </div>

            <div className="flex items-center justify-between rounded-xl border bg-accent/40 px-3 py-2">
              <div>
                <div className="text-sm font-medium text-foreground">Kapalı</div>
                <div className="text-xs text-muted-foreground">Bu tarih satışa kapalı</div>
              </div>
              <input type="checkbox" checked={dayClosed} onChange={(e) => setDayClosed(e.target.checked)} data-testid="day-closed" />
            </div>

            <Button onClick={saveDay} disabled={daySaving} className="w-full gap-2" data-testid="day-save">
              <Save className="h-4 w-4" />
              {daySaving ? "Kaydediliyor..." : "Kaydet"}
            </Button>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
