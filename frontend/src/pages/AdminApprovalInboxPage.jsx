import React, { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { CheckCircle, XCircle, Clock, ShieldCheck, Filter } from "lucide-react";
import { cn } from "../lib/utils";

const STATUS_TABS = [
  { key: "all", label: "Tümü" },
  { key: "pending", label: "Bekleyen", icon: Clock, color: "bg-yellow-100 text-yellow-800" },
  { key: "approved", label: "Onaylanan", icon: CheckCircle, color: "bg-green-100 text-green-800" },
  { key: "rejected", label: "Reddedilen", icon: XCircle, color: "bg-red-100 text-red-800" },
];

export default function AdminApprovalInboxPage() {
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("all");
  const [actionLoading, setActionLoading] = useState(null);
  const [rejectModal, setRejectModal] = useState(null);
  const [rejectNote, setRejectNote] = useState("");

  const loadApprovals = useCallback(async () => {
    try {
      setLoading(true);
      const params = activeTab !== "all" ? { status: activeTab } : {};
      const res = await api.get("/approvals", { params });
      setApprovals(res.data?.items || []);
    } catch (e) {
      console.error("Failed to load approvals:", e);
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => { loadApprovals(); }, [loadApprovals]);

  const handleApprove = async (id) => {
    try {
      setActionLoading(id);
      await api.post(`/approvals/${id}/approve`, {});
      await loadApprovals();
    } catch (e) {
      const msg = e.response?.data?.error?.message || e.message;
      alert("Onaylama hatası: " + msg);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async () => {
    if (!rejectModal) return;
    try {
      setActionLoading(rejectModal);
      await api.post(`/approvals/${rejectModal}/reject`, { note: rejectNote });
      setRejectModal(null);
      setRejectNote("");
      await loadApprovals();
    } catch (e) {
      const msg = e.response?.data?.error?.message || e.message;
      alert("Reddetme hatası: " + msg);
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusBadge = (status) => {
    const map = {
      pending: { label: "Bekleyen", variant: "outline", className: "border-yellow-400 text-yellow-700 bg-yellow-50" },
      approved: { label: "Onaylandı", variant: "outline", className: "border-green-400 text-green-700 bg-green-50" },
      rejected: { label: "Reddedildi", variant: "outline", className: "border-red-400 text-red-700 bg-red-50" },
    };
    const s = map[status] || { label: status, variant: "outline", className: "" };
    return <Badge variant={s.variant} className={s.className} data-testid={`status-${status}`}>{s.label}</Badge>;
  };

  return (
    <div className="p-6" data-testid="approval-inbox-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ShieldCheck className="h-6 w-6" />
            Onay İstekleri
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Bekleyen onayları yönetin. Yüksek tutarlı işlemler ve iadeler.
          </p>
        </div>
      </div>

      {/* Status Tabs */}
      <div className="flex gap-1 mb-4 border-b" data-testid="approval-tabs">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            data-testid={`tab-${tab.key}`}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
              activeTab === tab.key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {tab.label}
            {tab.key !== "all" && (
              <span className="ml-1.5 text-xs">
                ({approvals.filter(a => tab.key === "all" || a.status === tab.key).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-muted rounded-lg animate-pulse" />
          ))}
        </div>
      ) : approvals.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground" data-testid="no-approvals">
          <ShieldCheck className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p>Henüz onay isteği yok.</p>
        </div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50 border-b">
                <th className="text-left px-4 py-2.5 font-medium">Tür</th>
                <th className="text-left px-4 py-2.5 font-medium">İşlem</th>
                <th className="text-left px-4 py-2.5 font-medium">Talep Eden</th>
                <th className="text-left px-4 py-2.5 font-medium">Durum</th>
                <th className="text-left px-4 py-2.5 font-medium">Tarih</th>
                <th className="text-right px-4 py-2.5 font-medium">Aksiyonlar</th>
              </tr>
            </thead>
            <tbody>
              {approvals.map((item) => (
                <tr key={item.id} className="border-b last:border-0 hover:bg-muted/30" data-testid={`approval-row-${item.id}`}>
                  <td className="px-4 py-3 font-medium">{item.entity_type}</td>
                  <td className="px-4 py-3">{item.action}</td>
                  <td className="px-4 py-3 text-muted-foreground">{item.requested_by}</td>
                  <td className="px-4 py-3">{getStatusBadge(item.status)}</td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">
                    {item.created_at ? new Date(item.created_at).toLocaleDateString("tr-TR") : "-"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {item.status === "pending" ? (
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          onClick={() => handleApprove(item.id)}
                          disabled={actionLoading === item.id}
                          data-testid={`approve-btn-${item.id}`}
                          className="gap-1 h-7 text-xs"
                        >
                          <CheckCircle className="h-3.5 w-3.5" />
                          Onayla
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => setRejectModal(item.id)}
                          disabled={actionLoading === item.id}
                          data-testid={`reject-btn-${item.id}`}
                          className="gap-1 h-7 text-xs"
                        >
                          <XCircle className="h-3.5 w-3.5" />
                          Reddet
                        </Button>
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">
                        {item.approved_by || item.rejected_by || "-"}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Reject Modal */}
      {rejectModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" data-testid="reject-modal">
          <div className="bg-background border rounded-lg p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold mb-3">Onay İsteğini Reddet</h3>
            <textarea
              value={rejectNote}
              onChange={(e) => setRejectNote(e.target.value)}
              placeholder="Red sebebi (opsiyonel)..."
              className="w-full rounded-md border px-3 py-2 text-sm bg-background min-h-[80px]"
              data-testid="reject-note-input"
            />
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="outline" onClick={() => { setRejectModal(null); setRejectNote(""); }}>
                İptal
              </Button>
              <Button variant="destructive" onClick={handleReject} data-testid="confirm-reject-btn">
                Reddet
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
