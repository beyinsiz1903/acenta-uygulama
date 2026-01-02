import React, { useEffect, useState } from "react";
import axios from "axios";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";

const STATUS_OPTIONS = [
  "new",
  "contacted",
  "qualified",
  "lost",
  "won",
];

const statusLabel = {
  new: "Yeni",
  contacted: "Arandı",
  qualified: "Nitelikli",
  lost: "Kaybedildi",
  won: "Kazanıldı",
};

const AdminLeads = ({ user, tenant, onLogout }) => {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [updatingId, setUpdatingId] = useState(null);
  const [notes, setNotes] = useState({});

  const loadLeads = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append("status", statusFilter);
      if (search) params.append("q", search);
      const res = await axios.get(`/admin/leads?${params.toString()}`);
      setLeads(res.data?.leads || []);
    } catch (e) {
      console.error(e);
      toast.error("Lead listesi yüklenemedi");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLeads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleUpdate = async (leadId, newStatus) => {
    setUpdatingId(leadId);
    try {
      const payload = {};
      if (newStatus) payload.status = newStatus;
      if (notes[leadId]) payload.note = notes[leadId];
      const res = await axios.patch(`/admin/leads/${leadId}`, payload);
      if (res.data?.ok) {
        toast.success("Lead güncellendi");
        loadLeads();
      } else {
        toast.error("Lead güncellenemedi");
      }
    } catch (e) {
      console.error(e);
      toast.error("Lead güncellenemedi");
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="admin-leads">
      <div className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">PMS Lite Lead Listesi</h1>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Filtreler</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid md:grid-cols-3 gap-3">
              <div>
                <Label>Status</Label>
                <Select
                  value={statusFilter}
                  onValueChange={(val) => setStatusFilter(val === "all" ? "" : val)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Tümü" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tümü</SelectItem>
                    {STATUS_OPTIONS.map((s) => (
                      <SelectItem key={s} value={s}>
                        {statusLabel[s]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Arama</Label>
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="İsim, otel, telefon..."
                />
              </div>
              <div className="flex items-end">
                <Button onClick={loadLeads} disabled={loading} className="w-full">
                  {loading ? "Yükleniyor..." : "Listeyi Yenile"}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Leadler</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-xs text-gray-500">
                  <th className="px-2 py-1 text-left">Tarih</th>
                  <th className="px-2 py-1 text-left">Otel</th>
                  <th className="px-2 py-1 text-left">Bölge</th>
                  <th className="px-2 py-1 text-left">Oda</th>
                  <th className="px-2 py-1 text-left">İsim</th>
                  <th className="px-2 py-1 text-left">Telefon</th>
                  <th className="px-2 py-1 text-left">Status</th>
                  <th className="px-2 py-1 text-left">Not</th>
                  <th className="px-2 py-1 text-left">Aksiyon</th>
                </tr>
              </thead>
              <tbody>
                {leads.length === 0 && (
                  <tr>
                    <td colSpan={9} className="px-2 py-4 text-center text-xs text-gray-500">
                      Henüz PMS Lite lead kaydı yok.
                    </td>
                  </tr>
                )}
                {leads.map((lead) => {
                  const created = lead.created_at
                    ? new Date(lead.created_at).toLocaleString("tr-TR")
                    : "-";
                  return (
                    <tr key={lead.lead_id} className="border-b last:border-0">
                      <td className="px-2 py-1 align-top whitespace-nowrap">{created}</td>
                      <td className="px-2 py-1 align-top">{lead.property_name}</td>
                      <td className="px-2 py-1 align-top">{lead.location}</td>
                      <td className="px-2 py-1 align-top">{lead.rooms_count}</td>
                      <td className="px-2 py-1 align-top">{lead.full_name}</td>
                      <td className="px-2 py-1 align-top">{lead.phone}</td>
                      <td className="px-2 py-1 align-top">
                        <Badge variant="outline">{statusLabel[lead.status] || lead.status}</Badge>
                      </td>
                      <td className="px-2 py-1 align-top w-48">
                        <Input
                          value={notes[lead.lead_id] ?? lead.note ?? ""}
                          onChange={(e) =>
                            setNotes((prev) => ({ ...prev, [lead.lead_id]: e.target.value }))
                          }
                          className="text-xs"
                        />
                      </td>
                      <td className="px-2 py-1 align-top w-40">
                        <div className="flex flex-col gap-1">
                          <Select
                            onValueChange={(val) => handleUpdate(lead.lead_id, val)}
                            disabled={updatingId === lead.lead_id}
                          >
                            <SelectTrigger className="h-8 text-xs">
                              <SelectValue placeholder="Durum değiştir" />
                            </SelectTrigger>
                            <SelectContent>
                              {STATUS_OPTIONS.map((s) => (
                                <SelectItem key={s} value={s}>
                                  {statusLabel[s]}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-8 text-xs"
                            disabled={updatingId === lead.lead_id}
                            onClick={() => handleUpdate(lead.lead_id, null)}
                          >
                            Notu Kaydet
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default AdminLeads;
