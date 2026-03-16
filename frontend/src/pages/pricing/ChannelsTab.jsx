import React, { useState, useCallback, useEffect } from "react";
import { Plus, Trash2, Globe, Loader2 } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "../../components/ui/select";
import { toast } from "sonner";
import { pricingApi } from "./lib/pricingApi";
import { CHANNEL_ICONS, CHANNEL_COLORS } from "./lib/pricingConstants";

export function ChannelsTab() {
  const [channels, setChannels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ channel: "b2b", label: "", adjustment_pct: 0, commission_pct: 0 });

  const load = useCallback(async () => {
    setLoading(true);
    const data = await pricingApi("/channels");
    setChannels(Array.isArray(data) ? data : []);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    await pricingApi("/channels", { method: "POST", body: JSON.stringify({ ...form, adjustment_pct: parseFloat(form.adjustment_pct), commission_pct: parseFloat(form.commission_pct) }) });
    toast.success("Kanal eklendi");
    setShowAdd(false);
    load();
  };

  const remove = async (ruleId) => {
    await pricingApi(`/channels/${ruleId}`, { method: "DELETE" });
    toast.success("Kanal silindi");
    load();
  };

  return (
    <div className="space-y-4" data-testid="channels-tab">
      <div className="flex justify-between items-center">
        <h3 className="text-sm font-medium">Kanal Fiyatlandirmasi</h3>
        <Button size="sm" onClick={() => setShowAdd(!showAdd)} data-testid="add-channel-btn"><Plus className="w-3 h-3 mr-1" /> Kanal Ekle</Button>
      </div>

      {showAdd && (
        <Card className="border-dashed">
          <CardContent className="p-4 grid grid-cols-4 gap-3">
            <div>
              <Label className="text-xs">Kanal</Label>
              <Select value={form.channel} onValueChange={v => setForm(p => ({...p, channel: v}))}>
                <SelectTrigger data-testid="ch-type"><SelectValue /></SelectTrigger>
                <SelectContent>{["b2b","b2c","corporate","whitelabel"].map(c => <SelectItem key={c} value={c}>{c.toUpperCase()}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Etiket</Label>
              <Input value={form.label} onChange={e => setForm(p => ({...p, label: e.target.value}))} placeholder="B2B Agency" />
            </div>
            <div>
              <Label className="text-xs">Fiyat Ayarlama %</Label>
              <Input type="number" value={form.adjustment_pct} onChange={e => setForm(p => ({...p, adjustment_pct: e.target.value}))} />
            </div>
            <div className="flex items-end">
              <Button data-testid="save-channel-btn" onClick={create} size="sm">Kaydet</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin" /></div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {channels.map((ch) => {
            const Icon = CHANNEL_ICONS[ch.channel] || Globe;
            const colorClass = CHANNEL_COLORS[ch.channel] || "bg-gray-50 text-gray-700 border-gray-200";
            return (
              <Card key={ch.rule_id} className={`border ${colorClass.split(" ").pop()}`} data-testid={`channel-card-${ch.channel}`}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className={`p-2 rounded-lg ${colorClass.split(" ").slice(0, 2).join(" ")}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => remove(ch.rule_id)}>
                      <Trash2 className="w-3.5 h-3.5 text-red-400" />
                    </Button>
                  </div>
                  <h4 className="font-semibold text-sm">{ch.label || ch.channel.toUpperCase()}</h4>
                  <p className="text-xs text-muted-foreground mt-1">{ch.channel}</p>
                  <div className="mt-3 flex gap-3">
                    <div>
                      <p className="text-[10px] text-muted-foreground">Fiyat Ayarlama</p>
                      <p className="font-mono text-sm font-bold">{ch.adjustment_pct >= 0 ? "+" : ""}{ch.adjustment_pct}%</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground">Komisyon</p>
                      <p className="font-mono text-sm font-bold">{ch.commission_pct}%</p>
                    </div>
                  </div>
                  <Badge variant={ch.active ? "default" : "secondary"} className="mt-2 text-[10px]">
                    {ch.active ? "Aktif" : "Pasif"}
                  </Badge>
                </CardContent>
              </Card>
            );
          })}
          {channels.length === 0 && (
            <div className="col-span-4 text-center py-8 text-sm text-muted-foreground">Henuz kanal yok</div>
          )}
        </div>
      )}
    </div>
  );
}
