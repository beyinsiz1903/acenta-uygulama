import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";

function validityBadge(validity) {
  if (!validity || (!validity.from && !validity.to)) {
    return { label: "Geçerlilik yok", color: "bg-slate-100 text-foreground" };
  }
  const now = new Date();
  const from = validity.from ? new Date(validity.from) : null;
  const to = validity.to ? new Date(validity.to) : null;

  if (from && now < from) {
    return { label: "Yakında başlayacak", color: "bg-blue-100 text-blue-800" };
  }
  if (to && now > to) {
    return { label: "Süresi doldu", color: "bg-red-100 text-red-800" };
  }
  return { label: "Şu anda aktif", color: "bg-emerald-100 text-emerald-800" };
}

function AdminB2BDiscountsPage() {
  const navigate = useNavigate();
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [name, setName] = useState("");
  const [priority, setPriority] = useState(100);
  const [agencyId, setAgencyId] = useState("");
  const [productId, setProductId] = useState("");
  const [productType, setProductType] = useState("hotel");
  const [validFrom, setValidFrom] = useState("");
  const [validTo, setValidTo] = useState("");
  const [percent, setPercent] = useState(5);
  const [notes, setNotes] = useState("");

  const [expandedId, setExpandedId] = useState(null);

  const loadGroups = async () => {
    try {
      setLoading(true);
      const res = await api.get("/admin/b2b/discount-groups");
      setGroups(res.data.items || []);
      setError("");
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGroups();
  }, []);

  const onCreate = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      const payload = {
        name,
        priority: Number(priority) || 0,
        scope: {
          agency_id: agencyId || null,
          product_id: productId || null,
          product_type: productType || null,
        },
        validity:
          validFrom || validTo
            ? {
                from: validFrom || null,
                to: validTo || null,
              }
            : null,
        rules: [
          {
            type: "percent",
            value: Number(percent) || 0,
            applies_to: "markup_only",
          },
        ],
        notes: notes || null,
      };
      await api.post("/admin/b2b/discount-groups", payload);
      setName("");
      setPriority(100);
      setAgencyId("");
      setProductId("");
      setProductType("hotel");
      setValidFrom("");
      setValidTo("");
      setPercent(5);
      setNotes("");
      await loadGroups();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const toggleStatus = async (group) => {
    try {
      setLoading(true);
      const nextStatus = group.status === "active" ? "inactive" : "active";
      await api.put(`/admin/b2b/discount-groups/${group.id}`, { status: nextStatus });
      await loadGroups();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const onAddRule = async (group, value) => {
    try {
      setLoading(true);
      await api.post(`/admin/b2b/discount-groups/${group.id}/rules`, {
        type: "percent",
        value: Number(value) || 0,
        applies_to: "markup_only",
      });
      await loadGroups();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const onDeleteRule = async (group, idx) => {
    try {
      setLoading(true);
      await api.delete(`/admin/b2b/discount-groups/${group.id}/rules/${idx}`);
      await loadGroups();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">B2B İndirim Grupları</h1>
        <Button variant="ghost" size="sm" onClick={() => navigate("/app/admin")}>
          Geri dön
        </Button>
      </div>

      {error && (
        <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800">
          {error}
        </div>
      )}

      <form
        onSubmit={onCreate}
        className="rounded-2xl border bg-card p-4 space-y-3"
      >
        <div className="font-semibold text-sm mb-1">İndirim Grubu Oluştur</div>
        <div className="grid gap-3 md:grid-cols-3">
          <div className="space-y-1">
            <label className="text-xs font-medium">Ad</label>
            <Input
              data-testid="b2b-discount-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium">Öncelik</label>
            <Input
              type="number"
              data-testid="b2b-discount-priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium">İndirim %</label>
            <Input
              type="number"
              min={0}
              max={100}
              step={0.1}
              data-testid="b2b-discount-percent"
              value={percent}
              onChange={(e) => setPercent(e.target.value)}
            />
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="space-y-1">
            <label className="text-xs font-medium">Acenta ID</label>
            <Input
              data-testid="b2b-discount-agency-id"
              value={agencyId}
              onChange={(e) => setAgencyId(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium">Ürün ID</label>
            <Input
              data-testid="b2b-discount-product-id"
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium">Ürün Tipi</label>
            <select
              className="h-9 w-full rounded-md border bg-background px-2 text-sm"
              data-testid="b2b-discount-product-type"
              value={productType}
              onChange={(e) => setProductType(e.target.value)}
            >
              <option value="hotel">hotel</option>
            </select>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="space-y-1">
            <label className="text-xs font-medium">Geçerlilik Başlangıcı</label>
            <Input
              type="date"
              data-testid="b2b-discount-valid-from"
              value={validFrom}
              onChange={(e) => setValidFrom(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium">Geçerlilik Bitişi</label>
            <Input
              type="date"
              data-testid="b2b-discount-valid-to"
              value={validTo}
              onChange={(e) => setValidTo(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium">Notlar</label>
            <Textarea
              rows={2}
              data-testid="b2b-discount-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button
            type="submit"
            size="sm"
            data-testid="b2b-discount-create"
            disabled={loading}
          >
            Oluştur
          </Button>
        </div>
      </form>

      <div className="rounded-2xl border bg-card p-4 space-y-2">
        <div className="flex items-center justify-between mb-2">
          <div className="font-semibold text-sm">İndirim Grupları</div>
          <Button variant="outline" size="xs" onClick={loadGroups} disabled={loading}>
            Yenile
          </Button>
        </div>

        {groups.length === 0 ? (
          <div className="text-xs text-muted-foreground">Şu anda tanımlı indirim grubu bulunmuyor.</div>
        ) : (
          <div className="space-y-2">
            {groups.map((g) => {
              const badge = validityBadge(g.validity || {});
              const rules = g.rules || [];
              const mainRule = rules[0];
              const ruleSummary = mainRule
                ? `${mainRule.value}% ${mainRule.applies_to}`
                : "-";

              return (
                <div
                  key={g.id}
                  data-testid={`b2b-discount-row-${g.id}`}
                  className="rounded-xl border bg-background p-3 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <div className="text-xs font-semibold">{g.name}</div>
                      <div className="text-xs text-muted-foreground">
                        ID: {g.id} · Priority: {g.priority}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Kapsam: agency={g.scope?.agency_id || "*"}, product={g.scope?.product_id || "*"}, type={
                          g.scope?.product_type || "*"
                        }
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <div className="flex items-center gap-1">
                        <span
                          data-testid={`b2b-discount-validity-${g.id}`}
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-2xs font-semibold ${badge.color}`}
                        >
                          {badge.label}
                        </span>
                        <Button
                          type="button"
                          size="xs"
                          variant={g.status === "active" ? "default" : "outline"}
                          data-testid={`b2b-discount-toggle-${g.id}`}
                          onClick={() => toggleStatus(g)}
                          disabled={loading}
                        >
                          {g.status === "active" ? "Aktif" : "Pasif"}
                        </Button>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Kurallar: {ruleSummary}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <button
                      type="button"
                      className="underline"
                      data-testid={`b2b-discount-expand-${g.id}`}
                      onClick={() =>
                        setExpandedId((prev) => (prev === g.id ? null : g.id))
                      }
                    >
                      {expandedId === g.id ? "Detayları gizle" : "Detayları göster"}
                    </button>
                  </div>

                  {expandedId === g.id && (
                    <div className="mt-2 space-y-2">
                      <div className="text-xs font-semibold">Kurallar</div>
                      <div className="space-y-1">
                        {rules.length === 0 ? (
                          <div className="text-xs text-muted-foreground">
                            Henüz kural yok.
                          </div>
                        ) : (
                          rules.map((r, idx) => (
                            <div
                              key={`${g.id}-rule-${idx}`}
                              className="flex items-center justify-between rounded border bg-muted/40 px-2 py-1 text-xs"
                            >
                              <span>
                                {r.type} {r.value}% ({r.applies_to})
                              </span>
                              <Button
                                type="button"
                                size="xs"
                                variant="outline"
                                data-testid={`b2b-discount-rule-del-${g.id}-${idx}`}
                                onClick={() => onDeleteRule(g, idx)}
                                disabled={loading}
                              >
                                Sil
                              </Button>
                            </div>
                          ))
                        )}
                      </div>

                      <div className="flex items-center gap-2 mt-2">
                        <Input
                          type="number"
                          min={0}
                          max={100}
                          step={0.1}
                          placeholder="Yeni kural %"
                          className="h-8 w-24 text-xs"
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              const v = e.currentTarget.value;
                              if (!v) return;
                              onAddRule(g, v);
                              e.currentTarget.value = "";
                            }
                          }}
                        />
                        <Button
                          type="button"
                          size="xs"
                          data-testid={`b2b-discount-rule-add-${g.id}`}
                          onClick={() => {
                            const el = document.querySelector(
                              `input[placeholder='New rule %']`
                            );
                            if (!el || !el.value) return;
                            onAddRule(g, el.value);
                            el.value = "";
                          }}
                          disabled={loading}
                        >
                          Kural ekle
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default AdminB2BDiscountsPage;
