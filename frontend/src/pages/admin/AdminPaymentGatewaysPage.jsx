import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import {
  CreditCard, Plus, Edit, Trash2, X, Check, AlertCircle, Zap,
} from "lucide-react";

const PROVIDER_LABELS = {
  iyzico: { label: "İyzico", color: "bg-blue-100 text-blue-800" },
  paytr: { label: "PayTR", color: "bg-purple-100 text-purple-800" },
  stripe: { label: "Stripe", color: "bg-indigo-100 text-indigo-800" },
};

const CREDENTIAL_FIELDS = {
  iyzico: [
    { key: "api_key", label: "API Key" },
    { key: "secret_key", label: "Secret Key" },
  ],
  paytr: [
    { key: "merchant_id", label: "Merchant ID" },
    { key: "merchant_key", label: "Merchant Key" },
    { key: "merchant_salt", label: "Merchant Salt" },
  ],
  stripe: [
    { key: "secret_key", label: "Secret Key" },
    { key: "publishable_key", label: "Publishable Key" },
    { key: "webhook_secret", label: "Webhook Secret" },
  ],
};

const emptyForm = {
  provider: "iyzico", label: "", is_active: false, is_default: false,
  mode: "test", credentials: {}, supported_currencies: ["TRY"],
  max_installment: 12, commission_rate: 0,
};

export default function AdminPaymentGatewaysPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [creds, setCreds] = useState({});

  const { data, isLoading } = useQuery({
    queryKey: ["admin-payment-gateways"],
    queryFn: () => api.get("/admin/payment-gateways").then((r) => r.data),
  });

  const createMut = useMutation({
    mutationFn: (body) => api.post("/admin/payment-gateways", body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-payment-gateways"] }); setShowForm(false); },
  });
  const updateMut = useMutation({
    mutationFn: ({ id, ...body }) => api.patch(`/admin/payment-gateways/${id}`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-payment-gateways"] }); setEditItem(null); setShowForm(false); },
  });
  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/admin/payment-gateways/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-payment-gateways"] }),
  });
  const testMut = useMutation({
    mutationFn: (id) => api.post(`/admin/payment-gateways/${id}/test`),
  });

  const F = (field) => (e) => setForm({ ...form, [field]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const handleSubmit = (e) => {
    e.preventDefault();
    const payload = {
      ...form,
      credentials: creds,
      max_installment: Number(form.max_installment),
      commission_rate: Number(form.commission_rate),
      supported_currencies: typeof form.supported_currencies === "string"
        ? form.supported_currencies.split(",").map(s => s.trim())
        : form.supported_currencies,
    };
    if (editItem) updateMut.mutate({ id: editItem.id, ...payload });
    else createMut.mutate(payload);
  };

  const openCreate = () => { setForm(emptyForm); setCreds({}); setEditItem(null); setShowForm(true); };
  const openEdit = (item) => {
    setForm({ ...emptyForm, ...item, supported_currencies: Array.isArray(item.supported_currencies) ? item.supported_currencies.join(", ") : "TRY" });
    setCreds({});
    setEditItem(item);
    setShowForm(true);
  };

  const items = data?.items || [];
  const credFields = CREDENTIAL_FIELDS[form.provider] || [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <CreditCard className="w-6 h-6 text-indigo-600" />
          <h1 className="text-2xl font-bold">Ödeme Altyapıları</h1>
        </div>
        <button onClick={openCreate} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
          <Plus className="w-4 h-4" /> Yeni Sağlayıcı
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="border rounded-xl p-4 bg-blue-50">
          <div className="flex items-center gap-2 mb-2"><img src="https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/Iyzico_logo.svg/120px-Iyzico_logo.svg.png" alt="iyzico" className="h-6" onError={(e) => { e.target.style.display = "none"; }} /><span className="font-semibold text-blue-800">İyzico</span></div>
          <p className="text-xs text-gray-600">3D Secure, Taksit, Marketplace, Alt Üye İşyeri</p>
        </div>
        <div className="border rounded-xl p-4 bg-purple-50">
          <span className="font-semibold text-purple-800">PayTR</span>
          <p className="text-xs text-gray-600">iFrame, Sanal POS, Havale/EFT, Mobil Ödeme</p>
        </div>
        <div className="border rounded-xl p-4 bg-indigo-50">
          <span className="font-semibold text-indigo-800">Stripe</span>
          <p className="text-xs text-gray-600">Uluslararası ödemeler, Abonelik, Connect</p>
        </div>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">{editItem ? "Sağlayıcı Düzenle" : "Yeni Ödeme Sağlayıcı"}</h2>
              <button onClick={() => { setShowForm(false); setEditItem(null); }}><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              {!editItem && (
                <div><label className="block text-sm font-medium mb-1">Sağlayıcı *</label><select value={form.provider} onChange={(e) => { setForm({ ...form, provider: e.target.value }); setCreds({}); }} className="w-full px-3 py-2 border rounded-lg">
                  <option value="iyzico">İyzico</option>
                  <option value="paytr">PayTR</option>
                  <option value="stripe">Stripe</option>
                </select></div>
              )}
              <div><label className="block text-sm font-medium mb-1">Etiket</label><input value={form.label} onChange={F("label")} placeholder="Canlı / Test vb." className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Mod</label><select value={form.mode} onChange={F("mode")} className="w-full px-3 py-2 border rounded-lg"><option value="test">Test (Sandbox)</option><option value="live">Canlı</option></select></div>

              <div className="border-t pt-3">
                <h3 className="text-sm font-semibold mb-2">API Bilgileri</h3>
                {credFields.map((cf) => (
                  <div key={cf.key} className="mb-2">
                    <label className="block text-xs font-medium mb-1">{cf.label}</label>
                    <input type="password" value={creds[cf.key] || ""} onChange={(e) => setCreds({ ...creds, [cf.key]: e.target.value })} placeholder={editItem ? "Değiştirmek için girin" : ""} className="w-full px-3 py-2 border rounded-lg text-sm" />
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div><label className="block text-sm font-medium mb-1">Maks. Taksit</label><input type="number" value={form.max_installment} onChange={F("max_installment")} className="w-full px-3 py-2 border rounded-lg" /></div>
                <div><label className="block text-sm font-medium mb-1">Komisyon (%)</label><input type="number" step="0.01" value={form.commission_rate} onChange={F("commission_rate")} className="w-full px-3 py-2 border rounded-lg" /></div>
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2"><input type="checkbox" checked={form.is_active} onChange={F("is_active")} /> Aktif</label>
                <label className="flex items-center gap-2"><input type="checkbox" checked={form.is_default} onChange={F("is_default")} /> Varsayılan</label>
              </div>

              <div className="flex gap-3 justify-end">
                <button type="button" onClick={() => { setShowForm(false); setEditItem(null); }} className="px-4 py-2 border rounded-lg">İptal</button>
                <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">{editItem ? "Güncelle" : "Ekle"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Yükleniyor...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12">
          <CreditCard className="w-12 h-12 mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500">Henüz ödeme sağlayıcı yapılandırılmamış</p>
          <button onClick={openCreate} className="mt-3 text-indigo-600 hover:text-indigo-800 text-sm">Hemen ekleyin</button>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((gw) => {
            const prov = PROVIDER_LABELS[gw.provider] || { label: gw.provider, color: "bg-gray-100 text-gray-800" };
            return (
              <div key={gw.id} className="border rounded-xl p-4 flex items-center justify-between hover:shadow transition-shadow">
                <div className="flex items-center gap-4">
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${prov.color}`}>{prov.label}</span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{gw.label || gw.provider}</span>
                      {gw.is_default && <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded-full">Varsayılan</span>}
                      {gw.is_active ? <span className="flex items-center gap-1 text-green-600 text-xs"><Check className="w-3 h-3" /> Aktif</span> : <span className="flex items-center gap-1 text-gray-400 text-xs"><AlertCircle className="w-3 h-3" /> Pasif</span>}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Mod: {gw.mode === "live" ? "Canlı" : "Test"} | Maks. Taksit: {gw.max_installment} | Komisyon: %{gw.commission_rate}
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => testMut.mutate(gw.id)} className="flex items-center gap-1 px-3 py-1.5 border rounded-lg text-sm hover:bg-gray-50"><Zap className="w-3 h-3" /> Test</button>
                  <button onClick={() => openEdit(gw)} className="flex items-center gap-1 px-3 py-1.5 border rounded-lg text-sm hover:bg-gray-50"><Edit className="w-3 h-3" /></button>
                  <button onClick={() => { if (window.confirm("Bu sağlayıcıyı silmek istediğinize emin misiniz?")) deleteMut.mutate(gw.id); }} className="flex items-center gap-1 px-3 py-1.5 border rounded-lg text-sm text-red-600 hover:bg-red-50"><Trash2 className="w-3 h-3" /></button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {testMut.data && (
        <div className={`border rounded-xl p-4 ${testMut.data.data?.test_result === "success" ? "bg-green-50 border-green-200" : "bg-yellow-50 border-yellow-200"}`}>
          <p className="font-medium">{testMut.data.data?.provider} Test Sonucu: {testMut.data.data?.test_result}</p>
          <p className="text-sm text-gray-600">{testMut.data.data?.details}</p>
        </div>
      )}
    </div>
  );
}
