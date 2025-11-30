import React, { useEffect, useState } from "react";
import Layout from "@/components/Layout";
import axios from "axios";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Building2, Wrench, Filter, RefreshCw, AlertTriangle, CheckCircle } from "lucide-react";

const MaintenanceWorkOrders = ({ user, tenant, onLogout }) => {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("open");
  const [priority, setPriority] = useState("all");
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const params = {};
      if (status && status !== "all") params.status = status;
      if (priority && priority !== "all") params.priority = priority;
      const res = await axios.get("/maintenance/work-orders", { params });
      setItems(res.data.items || []);
    } catch (err) {
      console.error("Failed to load maintenance work orders", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleUpdateStatus = async (id, newStatus) => {
    try {
      await axios.patch(`/maintenance/work-orders/${id}`, { status: newStatus });
      await loadData();
    } catch (err) {
      console.error("Failed to update work order", err);
    }
  };

  const renderStatusBadge = (value) => {
    const v = value || "open";
    let color = "bg-gray-100 text-gray-700";
    if (v === "open") color = "bg-red-100 text-red-700";
    else if (v === "in_progress") color = "bg-yellow-100 text-yellow-700";
    else if (v === "completed") color = "bg-green-100 text-green-700";
    else if (v === "cancelled") color = "bg-gray-200 text-gray-700";
    return <Badge className={color}>{v}</Badge>;
  };

  const renderPriorityBadge = (value) => {
    const v = value || "normal";
    let color = "bg-gray-100 text-gray-700";
    if (v === "urgent") color = "bg-red-600 text-white";
    else if (v === "high") color = "bg-red-100 text-red-700";
    else if (v === "normal") color = "bg-blue-100 text-blue-700";
    else if (v === "low") color = "bg-gray-100 text-gray-700";
    return <Badge className={color}>{v}</Badge>;
  };

  return (
    <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="pms">
      <div className="p-4 md:p-6 max-w-6xl mx-auto space-y-4">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div>
            <h1 className="text-xl md:text-2xl font-bold flex items-center gap-2">
              <Wrench className="w-5 h-5 text-amber-600" />
              Maintenance Work Orders
            </h1>
            <p className="text-xs md:text-sm text-gray-600">
              Kat Hizmetleri, Ön Büro veya sensörler tarafından oluşturulan tüm bakım iş emirlerini takip edin.
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={loadData}
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} />
            Yenile
          </Button>
        </div>

        {/* Filters */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Filter className="w-4 h-4" />
              Filtreler
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div>
              <div className="text-xs text-gray-600 mb-1">Durum</div>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tümü</SelectItem>
                  <SelectItem value="open">Open</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <div className="text-xs text-gray-600 mb-1">Öncelik</div>
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue placeholder="Priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tümü</SelectItem>
                  <SelectItem value="urgent">Urgent</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex justify-end">
              <Button size="sm" onClick={loadData} disabled={loading}>
                Uygula
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* List */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              Work Orders ({items.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="py-10 text-center text-gray-500 text-sm flex items-center justify-center gap-2">
                <RefreshCw className="w-5 h-5 animate-spin" />
                Yükleniyor...
              </div>
            ) : items.length === 0 ? (
              <div className="py-10 text-center text-gray-500 text-sm">
                Kayıtlı bakım iş emri bulunmuyor.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs md:text-sm">
                  <thead>
                    <tr className="border-b text-left text-gray-600">
                      <th className="py-2 pr-3">Oda</th>
                      <th className="py-2 pr-3">Issue</th>
                      <th className="py-2 pr-3">Kaynak</th>
                      <th className="py-2 pr-3">Raporlayan</th>
                      <th className="py-2 pr-3 text-right">Öncelik</th>
                      <th className="py-2 pr-3 text-right">Durum</th>
                      <th className="py-2 pr-3 text-right">İşlem</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((wo) => {
                      const created = wo.created_at ? new Date(wo.created_at).toLocaleString("tr-TR") : "";
                      return (
                        <tr key={wo.id} className="border-b last:border-0 hover:bg-gray-50">
                          <td className="py-2 pr-3 whitespace-nowrap">
                            <div className="font-medium text-gray-900">Room {wo.room_number || "-"}</div>
                            <div className="text-[11px] text-gray-500">{created}</div>
                          </td>
                          <td className="py-2 pr-3 whitespace-nowrap">
                            <div className="text-[11px] font-semibold text-gray-800">{wo.issue_type}</div>
                            <div className="text-[11px] text-gray-500 max-w-xs truncate" title={wo.description || ""}>
                              {wo.description || "-"}
                            </div>
                          </td>
                          <td className="py-2 pr-3 text-[11px] text-gray-600">
                            {wo.source || "-"}
                          </td>
                          <td className="py-2 pr-3 text-[11px] text-gray-600">
                            {wo.reported_by_role || "-"}
                          </td>
                          <td className="py-2 pr-3 text-right">
                            {renderPriorityBadge(wo.priority)}
                          </td>
                          <td className="py-2 pr-3 text-right">
                            {renderStatusBadge(wo.status)}
                          </td>
                          <td className="py-2 pr-3 text-right">
                            {wo.status !== "completed" ? (
                              <div className="inline-flex gap-1">
                                <Button
                                  size="xs"
                                  variant="outline"
                                  onClick={() => handleUpdateStatus(wo.id, "in_progress")}
                                >
                                  <AlertTriangle className="w-3 h-3 mr-1" />
                                  Start
                                </Button>
                                <Button
                                  size="xs"
                                  variant="outline"
                                  className="border-green-300 text-green-700"
                                  onClick={() => handleUpdateStatus(wo.id, "completed")}
                                >
                                  <CheckCircle className="w-3 h-3 mr-1" />
                                  Done
                                </Button>
                              </div>
                            ) : (
                              <span className="text-[11px] text-gray-400">Closed</span>
                            )}
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
    </Layout>
  );
};

export default MaintenanceWorkOrders;
