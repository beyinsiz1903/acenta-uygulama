import React, { useEffect, useState } from "react";
import { Ticket, Plus } from "lucide-react";

import { api, apiErrorMessage, getUser } from "../lib/api";
import { formatMoney } from "../lib/format";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";

export default function B2BBookingPage() {
  const user = getUser();
  const [products, setProducts] = useState([]);
  const [customers, setCustomers] = useState([]);

  const [productId, setProductId] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [pax, setPax] = useState(1);

  const [lastReservation, setLastReservation] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      setError("");
      try {
        const [p, c] = await Promise.all([api.get("/products"), api.get("/customers")]);
        setProducts(p.data || []);
        setCustomers(c.data || []);
        setProductId((p.data || [])[0]?.id || "");
        setCustomerId((c.data || [])[0]?.id || "");
      } catch (e) {
        setError(apiErrorMessage(e));
      }
    })();
  }, []);

  async function book() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.post("/b2b/book", {
        product_id: productId,
        customer_id: customerId,
        start_date: startDate,
        end_date: endDate || null,
        pax: Number(pax || 1),
      });
      setLastReservation(resp.data);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">B2B Rezervasyon</h2>
        <p className="text-sm text-muted-foreground">
          {user?.agency_id ? "Alt acente hesabı" : "Bu sayfa b2b_agent için."}
        </p>
      </div>

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Ticket className="h-4 w-4 text-muted-foreground" />
            Yeni Rezervasyon
          </CardTitle>
        </CardHeader>
        <CardContent>
          {error ? (
            <div className="mb-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="b2b-book-error">
              {error}
            </div>
          ) : null}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>Ürün</Label>
              <Select value={productId} onValueChange={setProductId}>
                <SelectTrigger data-testid="b2b-book-product">
                  <SelectValue placeholder="Ürün seç" />
                </SelectTrigger>
                <SelectContent>
                  {products.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Müşteri</Label>
              <Select value={customerId} onValueChange={setCustomerId}>
                <SelectTrigger data-testid="b2b-book-customer">
                  <SelectValue placeholder="Müşteri seç" />
                </SelectTrigger>
                <SelectContent>
                  {customers.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Başlangıç</Label>
              <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} data-testid="b2b-book-start" />
            </div>
            <div className="space-y-2">
              <Label>Bitiş</Label>
              <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} data-testid="b2b-book-end" />
            </div>
            <div className="space-y-2">
              <Label>Pax</Label>
              <Input type="number" value={pax} onChange={(e) => setPax(e.target.value)} data-testid="b2b-book-pax" />
            </div>
          </div>

          <div className="mt-4">
            <Button onClick={book} disabled={loading} className="gap-2" data-testid="b2b-book-submit">
              <Plus className="h-4 w-4" />
              {loading ? "Oluşturuluyor..." : "B2B Rezervasyon Oluştur"}
            </Button>
          </div>

          {lastReservation ? (
            <div className="mt-4 rounded-2xl border bg-accent/40 p-4" data-testid="b2b-book-result">
              <div className="text-sm font-semibold text-foreground">Oluşturuldu</div>
              <div className="mt-1 text-sm text-foreground/80">PNR: {lastReservation.pnr}</div>
              <div className="text-sm text-foreground/80">Toplam: {formatMoney(lastReservation.total_price, lastReservation.currency)}</div>
              <div className="text-xs text-muted-foreground">İndirim/komisyon acente ayarlarından hesaplanır.</div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
