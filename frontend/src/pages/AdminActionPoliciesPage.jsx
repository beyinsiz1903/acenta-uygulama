import React, { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { useToast } from "../hooks/use-toast";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";

const ACTION_OPTIONS = [
  { value: "none", label: "Otomatik aksiyon yok" },
  { value: "watchlist", label: "İzleme listesi" },
  { value: "manual_review", label: "Manuel inceleme" },
  { value: "block", label: "Otomatik bloke" },
];

const REASON_OPTIONS = [
  { value: "rate", label: "Yüksek no-show oranı" },
  { value: "repeat", label: "Tekrarlayan no-show (7g)" },
];

function RuleRow({ rule, index, onChange, onRemove }) {
  const when = rule.when || { high_risk: true, reasons_any: [] };
  const then = rule.then || {
    action: "watchlist",
    requires_approval_to_unblock: false,
    notify_channels: [],
  };

  const toggleReason = (value) => {
    const current = when.reasons_any || [];
    const exists = current.includes(value);
    const next = exists ? current.filter((v) => v !== value) : [...current, value];
    onChange(index, { ...rule, when: { ...when, reasons_any: next } });
  };

  return (
    <tr className="border-b last:border-0">
      <td className="px-2 py-2 text-xs align-top">
        <div className="font-medium mb-1">High risk</div>
        <div className="text-[11px] text-muted-foreground">reasons_any</div>
      </td>
      <td className="px-2 py-2 align-top">
        <div className="flex flex-col gap-1 text-xs">
          {REASON_OPTIONS.map((opt) => {
            const checked = (when.reasons_any || []).includes(opt.value);
            return (
              <label key={opt.value} className="inline-flex items-center gap-1">
                <input
                  type="checkbox"
                  className="h-3 w-3"
                  checked={checked}
                  onChange={() => toggleReason(opt.value)}
                />
                <span>{opt.label}</span>
              </label>
            );
          })}
        </div>
      </td>
      <td className="px-2 py-2 align-top">
        <select
          className="h-8 rounded-md border bg-background px-2 text-xs"
          value={then.action}
          onChange={(e) =>
            onChange(index, {
              ...rule,
              then: { ...then, action: e.target.value },
            })
          }
        >
          {ACTION_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <div className="mt-1 text-[11px] flex items-center gap-1">
          <input
            id={`requires-approval-${index}`}
            type="checkbox"
            className="h-3 w-3"
            checked={then.requires_approval_to_unblock || false}
            onChange={(e) =>
              onChange(index, {
                ...rule,
                then: { ...then, requires_approval_to_unblock: e.target.checked },
              })
            }
          />
          <label htmlFor={`requires-approval-${index}`} className="select-none">
            Requires approval to unblock
          </label>
        </div>
      </td>
      <td className="px-2 py-2 align-top text-right">
        <Button variant="ghost" size="sm" type="button" onClick={() => onRemove(index)}>
          Remove
        </Button>
      </td>
    </tr>
  );
}

export default function AdminActionPoliciesPage() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [defaultAction, setDefaultAction] = useState("watchlist");
  const [rules, setRules] = useState([]);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const res = await api.get("/admin/action-policies/match-risk");
      const policy = res.data?.policy || {};
      setEnabled(Boolean(policy.enabled ?? true));
      setDefaultAction(policy.default_action || "watchlist");
      setRules(policy.rules || []);
    } catch (e) {
      const msg = apiErrorMessage(e);
      // "Not Found" durumunda politikalar hen tanmlanmam sayyoruz ve bof state gfsteriyoruz.
      if (msg !== "Not Found") {
        setError(msg);
        toast({ title: "Aksiyon politikaları yüklenemedi", description: msg, variant: "destructive" });
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRuleChange = (index, nextRule) => {
    setRules((prev) => prev.map((r, i) => (i === index ? nextRule : r)));
  };

  const handleAddRule = () => {
    setRules((prev) => [
      ...prev,
      {
        when: { high_risk: true, reasons_any: [] },
        then: { action: "watchlist", requires_approval_to_unblock: true, notify_channels: [] },
      },
    ]);
  };

  const handleRemoveRule = (index) => {
    setRules((prev) => prev.filter((_, i) => i !== index));
  };

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = {
        enabled,
        default_action: defaultAction,
        rules,
      };
      const res = await api.put("/admin/action-policies/match-risk", payload);
      const policy = res.data?.policy || payload;
      setEnabled(Boolean(policy.enabled ?? true));
      setDefaultAction(policy.default_action || "watchlist");
      setRules(policy.rules || []);
      toast({ title: "Action policies saved", description: "Match-risk action policies updated." });
    } catch (e) {
      const msg = apiErrorMessage(e);
      setError(msg);
      toast({ title: "Politikalar kaydedilemedi", description: msg, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="p-4 md:p-6" data-testid="action-policies-page">
      <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="text-xl font-semibold">Match Aksiyon Politikaları (Risk)</div>
          <div className="text-sm text-muted-foreground">
            High-risk match durumunda otomatik watchlist / block davranışlarını tanımlayın.
          </div>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs text-muted-foreground" htmlFor="action-policies-enabled">
            Politikalar aktif
          </label>
          <input
            id="action-policies-enabled"
            data-testid="action-policies-enabled"
            type="checkbox"
            className="h-4 w-4"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
          />
        </div>
      </div>

      {error && error !== "Not Found" ? (
        <div className="mb-3 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Default action</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <select
            data-testid="action-policies-default-action"
            className="h-9 rounded-md border bg-background px-2 text-sm"
            value={defaultAction}
            onChange={(e) => setDefaultAction(e.target.value)}
            disabled={loading}
          >
            {ACTION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-muted-foreground">
            Yüksek riskli bir match için hiçbir kural eşleşmediğinde uygulanacak varsayılan davranış.
          </p>
        </CardContent>
      </Card>

      <form onSubmit={handleSave} className="mt-4 space-y-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Rules</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="overflow-x-auto">
              <table
                className="w-full text-sm"
                data-testid="action-policies-rules-table"
              >
                <thead>
                  <tr className="border-b text-xs text-muted-foreground">
                    <th className="px-2 py-2 text-left w-40">When</th>
                    <th className="px-2 py-2 text-left">Reasons</th>
                    <th className="px-2 py-2 text-left w-56">Then</th>
                    <th className="px-2 py-2 text-right w-24">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-2 py-6 text-center text-xs text-muted-foreground">
                        Henüz kural yok. İlk kuralınızı ekleyin.
                      </td>
                    </tr>
                  ) : (
                    rules.map((rule, idx) => (
                      <RuleRow
                        key={idx}
                        rule={rule}
                        index={idx}
                        onChange={handleRuleChange}
                        onRemove={handleRemoveRule}
                      />
                    ))
                  )}
                </tbody>
              </table>
            </div>
            <div className="mt-3 flex justify-between items-center">
              <Button type="button" variant="outline" size="sm" onClick={handleAddRule}>
                Add rule
              </Button>
              <Button type="submit" size="sm" disabled={saving || loading} data-testid="action-policies-save">
                {saving ? "Saving..." : "Save policies"}
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
