import React, { useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { toast } from "sonner";

function CouponInput({ quoteId, onUpdated }) {
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);

  const handleApply = async () => {
    if (!code.trim()) return;
    setLoading(true);
    try {
      const resp = await api.post(`/b2b/quotes/${quoteId}/apply-coupon`, null, {
        params: { code: code.trim() },
      });
      onUpdated?.(resp.data);
      const c = resp.data.coupon;
      if (c && c.status === "APPLIED") {
        toast.success(`Kupon uygulandı: ${c.code}`);
      } else if (c) {
        toast.error(`Kupon uygulanamadı: ${c.reason || c.status}`);
      } else {
        toast.error("Kupon uygulanamadı.");
      }
    } catch (e) {
      toast.error(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    setLoading(true);
    try {
      const resp = await api.delete(`/b2b/quotes/${quoteId}/coupon`);
      onUpdated?.(resp.data);
      toast.success("Kupon kaldırıldı.");
    } catch (e) {
      toast.error(apiErrorMessage(e));
    } finally {
      setLoading(false);
      setCode("");
    }
  };

  return (
    <div className="flex flex-col sm:flex-row gap-2 items-start sm:items-center mt-2">
      <Input
        value={code}
        onChange={(e) => setCode(e.target.value.toUpperCase())}
        placeholder="Kupon kodu"
        className="sm:w-48"
      />
      <div className="flex gap-2">
        <Button type="button" size="sm" onClick={handleApply} disabled={loading || !code.trim()}>
          Uygula
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={handleClear} disabled={loading}>
          Kaldır
        </Button>
      </div>
    </div>
  );
}

export default CouponInput;
