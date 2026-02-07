import React, { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { MessageSquare, Send, RefreshCw, Phone } from "lucide-react";

export default function AdminSMSPage() {
  const [logs, setLogs] = useState([]);
  const [templates, setTemplates] = useState({});
  const [loading, setLoading] = useState(true);
  const [showSend, setShowSend] = useState(false);
  const [sending, setSending] = useState(false);
  const [form, setForm] = useState({ to: "", template_key: "custom", variables: { message: "" } });

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [logsRes, tmplRes] = await Promise.all([
        api.get("/sms/logs"),
        api.get("/sms/templates"),
      ]);
      setLogs(logsRes.data?.items || []);
      setTemplates(tmplRes.data?.templates || {});
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSend = async () => {
    if (!form.to) return;
    try {
      setSending(true);
      await api.post("/sms/send", form);
      setShowSend(false);
      setForm({ to: "", template_key: "custom", variables: { message: "" } });
      await load();
    } catch (e) { alert(e.response?.data?.error?.message || e.message); } finally { setSending(false); }
  };

  return (
    <div className="p-6" data-testid="sms-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><MessageSquare className="h-6 w-6" /> SMS Bildirimleri</h1>
          <p className="text-sm text-muted-foreground mt-1">SMS gonderimi ve loglar. Provider: Mock (sandbox)</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw className="h-4 w-4 mr-1" /> Yenile</Button>
          <Button size="sm" onClick={() => setShowSend(!showSend)} data-testid="send-sms-btn"><Send className="h-4 w-4 mr-1" /> SMS Gonder</Button>
        </div>
      </div>

      {showSend && (
        <div className="rounded-lg border p-4 mb-6 bg-muted/20" data-testid="send-sms-form">
          <h3 className="text-sm font-semibold mb-3">SMS Gonder</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium block mb-1">Telefon</label>
              <input value={form.to} onChange={e => setForm(f => ({ ...f, to: e.target.value }))} className="w-full rounded-md border px-3 py-2 text-sm bg-background" placeholder="+905xx..." data-testid="sms-phone-input" />
            </div>
            <div>
              <label className="text-xs font-medium block mb-1">Sablon</label>
              <select value={form.template_key} onChange={e => setForm(f => ({ ...f, template_key: e.target.value }))} className="w-full rounded-md border px-3 py-2 text-sm bg-background" data-testid="sms-template-select">
                {Object.entries(templates).map(([k, v]) => <option key={k} value={k}>{k}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium block mb-1">Mesaj</label>
              <input value={form.variables.message || ""} onChange={e => setForm(f => ({ ...f, variables: { ...f.variables, message: e.target.value } }))} className="w-full rounded-md border px-3 py-2 text-sm bg-background" placeholder="Mesajiniz..." data-testid="sms-message-input" />
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-3">
            <Button variant="outline" size="sm" onClick={() => setShowSend(false)}>Iptal</Button>
            <Button size="sm" onClick={handleSend} disabled={sending || !form.to} data-testid="submit-sms-btn">{sending ? "Gonderiliyor..." : "Gonder"}</Button>
          </div>
        </div>
      )}

      {loading ? <div className="animate-pulse h-20 bg-muted rounded-lg" /> : logs.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground" data-testid="no-sms-logs"><MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-30" /><p>Henuz SMS gonderimi yok.</p></div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="bg-muted/50 border-b">
              <th className="text-left px-4 py-2.5 font-medium">Telefon</th>
              <th className="text-left px-4 py-2.5 font-medium">Sablon</th>
              <th className="text-left px-4 py-2.5 font-medium">Mesaj</th>
              <th className="text-left px-4 py-2.5 font-medium">Durum</th>
              <th className="text-left px-4 py-2.5 font-medium">Tarih</th>
            </tr></thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id} className="border-b last:border-0 hover:bg-muted/30" data-testid={`sms-row-${log.id}`}>
                  <td className="px-4 py-3 flex items-center gap-1"><Phone className="h-3.5 w-3.5 text-muted-foreground" /> {log.to}</td>
                  <td className="px-4 py-3"><Badge variant="outline">{log.template_key}</Badge></td>
                  <td className="px-4 py-3 text-muted-foreground text-xs max-w-[300px] truncate">{log.message}</td>
                  <td className="px-4 py-3"><Badge variant="outline" className="bg-green-50 text-green-700">{log.status}</Badge></td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{log.created_at ? new Date(log.created_at).toLocaleString("tr-TR") : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
