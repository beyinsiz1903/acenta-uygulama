import React, { useEffect, useState } from "react";
import {
  getApprovalTasks,
  approveApprovalTask,
  rejectApprovalTask,
  apiErrorMessage,
  runScaleUIProof,
  approveScaleUIProof,
} from "../lib/api";
import { useToast } from "../hooks/use-toast";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";

function formatDateTime(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("tr-TR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AdminApprovalsPage() {
  const { toast } = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [rowLoading, setRowLoading] = useState({});
  const [error, setError] = useState("");

  const [proof, setProof] = useState(null);
  const [proofLoading, setProofLoading] = useState(false);
  const [approveProofLoading, setApproveProofLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const data = await getApprovalTasks({ status: "pending", limit: 50 });
      setItems(data?.items || []);
    } catch (e) {
      const msg = apiErrorMessage(e);
      // "Not Found" durumunda bekleyen onay görevi yok gibi davran; kırmızı hata göstermeyelim.
      if (msg === "Not Found") {
        setItems([]);
      } else {
        setError(msg);
        toast({ title: "Onay listesi yüklenemedi", description: msg, variant: "destructive" });
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const handleDecision = async (id, action) => {
    setRowLoading((prev) => ({ ...prev, [id]: true }));
    try {
      if (action === "approve") {
        await approveApprovalTask(id, {});
        toast({ title: "Görev onaylandı" });
      } else {
        await rejectApprovalTask(id, {});
        toast({ title: "Görev reddedildi" });
      }
      setItems((prev) => prev.filter((x) => x.id !== id));
    } catch (e) {
      const msg = apiErrorMessage(e);
      toast({ title: `Görev ${action === "approve" ? "onaylanamadı" : "reddedilemedi"}`, description: msg, variant: "destructive" });
    } finally {
      setRowLoading((prev) => ({ ...prev, [id]: false }));
    }
  };

  const hasItems = items && items.length > 0;

  const runProofHarness = async () => {
    try {
      setProofLoading(true);
      const data = await runScaleUIProof();
      setProof(data);
      toast({
        title: "SCALE proof run created",
        description: "Match blocked + request-unblock + pending task generated.",
      });
      await load();
    } catch (e) {
      toast({
        title: "SCALE proof çalıştırılamadı",
        description: apiErrorMessage(e),
        variant: "destructive",
      });
    } finally {
      setProofLoading(false);
    }
  };

  const approveProofHarness = async () => {
    if (!proof?.request_unblock?.task_id) return;
    try {
      setApproveProofLoading(true);
      const data = await approveScaleUIProof(proof.request_unblock.task_id, "SCALE UI proof approve");
      setProof((prev) => ({ ...(prev || {}), approve_result: data }));
      toast({
        title: "SCALE proof görevi onaylandı",
        description: "Match unblocked and audit events written.",
      });
      await load();
    } catch (e) {
      toast({
        title: "Failed to approve SCALE proof task",
        description: apiErrorMessage(e),
        variant: "destructive",
      });
    } finally {
      setApproveProofLoading(false);
    }
  };

  return (
    <div className="p-4 md:p-6" data-testid="approvals-page">
      <Card className="mb-4">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">SCALE UI Proof Harness</CardTitle>
        </CardHeader>
        <CardContent className="pt-0 text-xs space-y-2">
          <p className="text-muted-foreground">
            Generates a demo blocked match, unblock request and approval audit trail for SCALE v1 UI proof.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              data-testid="scale-proof-run"
              onClick={runProofHarness}
              disabled={proofLoading}
            >
              {proofLoading ? "Running..." : "Run SCALE Proof"}
            </Button>
            {proof?.request_unblock?.task_id && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                data-testid="scale-proof-approve"
                onClick={approveProofHarness}
                disabled={approveProofLoading}
              >
                {approveProofLoading ? "Approving..." : "Approve Proof Task"}
              </Button>
            )}
          </div>
          <pre
            className="mt-2 max-h-64 overflow-auto rounded bg-muted p-2 text-xs"
            data-testid="scale-proof-pack"
          >
            {proof ? JSON.stringify(proof, null, 2) : "// no proof run yet"}
          </pre>
        </CardContent>
      </Card>

      <div className="mb-4 flex flex-col gap-1 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="text-xl font-semibold">Onay Görevleri</div>
          <div className="text-sm text-muted-foreground">
            Bloke kaldırma ve benzeri kritik match onay görevlerini buradan yönetebilirsiniz.
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>Durum: bekleyen</span>
          <Button type="button" size="sm" variant="outline" onClick={() => load()} disabled={loading}>
            {loading ? "Yenileniyor..." : "Yenile"}
          </Button>
        </div>
      </div>

      {error ? (
        <div
          className="mb-3 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          data-testid="approvals-error"
        >
          {error}
        </div>
      ) : null}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Pending approval tasks</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          {!hasItems && !loading ? (
            <div
              className="py-8 text-sm text-muted-foreground text-center"
              data-testid="approvals-empty"
            >
              Bekleyen onay görevi yok.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-xs text-muted-foreground">
                    <th className="px-2 py-2 text-left">Requested at</th>
                    <th className="px-2 py-2 text-left">Type</th>
                    <th className="px-2 py-2 text-left">Target</th>
                    <th className="px-2 py-2 text-left">Requested by</th>
                    <th className="px-2 py-2 text-right w-40">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => {
                    const busy = !!rowLoading[item.id];
                    const target = item.target || {};
                    const matchId = target.match_id || "-";
                    return (
                      <tr
                        key={item.id}
                        className="border-b last:border-0 hover:bg-muted/40"
                        data-testid={`approval-row-${item.id}`}
                      >
                        <td className="px-2 py-2 text-xs">
                          {formatDateTime(item.requested_at)}
                        </td>
                        <td className="px-2 py-2 text-xs">
                          <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
                            {item.task_type || "-"}
                          </span>
                        </td>
                        <td className="px-2 py-2 text-xs">
                          <div className="font-mono text-xs">{matchId}</div>
                        </td>
                        <td className="px-2 py-2 text-xs">{item.requested_by_email || "-"}</td>
                        <td className="px-2 py-2 text-right">
                          <div className="inline-flex gap-2">
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              data-testid="approval-approve-btn"
                              disabled={busy}
                              onClick={() => handleDecision(item.id, "approve")}
                            >
                              Approve
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              data-testid="approval-reject-btn"
                              disabled={busy}
                              onClick={() => handleDecision(item.id, "reject")}
                            >
                              Reject
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
