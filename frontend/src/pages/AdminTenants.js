import React, { useEffect, useState } from 'react';
import axios from 'axios';
import Layout from '@/components/Layout';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip';
import { Link } from 'react-router-dom';

const MODULE_GROUPS = [
  {
    id: 'pms',
    title: 'PMS & Operasyon',
    description: 'Ön büro, oda yönetimi ve günlük operasyon modülleri',
    items: [
      { key: 'pms', label: 'PMS (Masaüstü)', hint: 'Ana PMS ekranı, rezervasyon ve oda yönetimi' },
      { key: 'pms_mobile', label: 'PMS Mobil Ana Erişim', hint: 'Personel için mobil PMS ana paneli' },
      { key: 'mobile_housekeeping', label: 'Mobil Housekeeping', hint: 'Kat hizmetleri için mobil görev listesi ve oda durumu' },
      { key: 'mobile_revenue', label: 'Mobil Revenue', hint: 'Gelir yöneticileri için mobil revenue ekranları' },
      { key: 'gm_dashboards', label: 'GM & Executive Dashboardlar', hint: 'Genel Müdür ve üst yönetim için özet dashboardlar' },
    ],
  },
  {
    id: 'reports_finance',
    title: 'Raporlama & Finans',
    description: 'Gelir, doluluk ve fatura/finans raporları',
    items: [
      { key: 'reports', label: 'Raporlar', hint: 'Flash report, doluluk, gelir ve forecast raporları' },
      { key: 'invoices', label: 'Fatura & Finans Modülleri', hint: 'Fatura, alacak takibi ve mali raporlar' },
    ],
  },
  {
    id: 'ai',
    title: 'Yapay Zeka Modülleri',
    description: 'AI destekli fiyatlama, chatbot ve analitik özellikler',
    items: [
      { key: 'ai', label: 'AI Genel Anahtar', hint: 'Tüm AI modüllerini toplu aç/kapat (alt modüllerin üst anahtarı)' },
      { key: 'ai_chatbot', label: 'AI Chatbot', hint: 'Misafir sorularına yanıt veren akıllı asistan' },
      { key: 'ai_pricing', label: 'AI Dynamic Pricing', hint: 'Doluluk, tarih ve rakip fiyatlarına göre oda fiyat önerileri' },
      { key: 'ai_whatsapp', label: 'AI WhatsApp Concierge', hint: 'WhatsApp üzerinden concierge ve misafir iletişimi' },
      { key: 'ai_predictive', label: 'AI Tahminler (Predictive Analytics)', hint: 'Talep ve performans tahminleri' },
      { key: 'ai_reputation', label: 'AI Reputation / Review Analizi', hint: 'Yorum ve puanlamaları otomatik analiz eder' },
      { key: 'ai_revenue_autopilot', label: 'AI Revenue Autopilot', hint: 'Gelir yönetimi aksiyonlarını otomatikleştirme' },
      { key: 'ai_social_radar', label: 'AI Social Media Radar', hint: 'Sosyal medya ve online görünürlük takibi' },
    ],
  },
];

const AdminTenants = ({ user, tenant, onLogout }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [tenants, setTenants] = useState([]);
  const [error, setError] = useState(null);

  const loadTenants = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get('/admin/tenants');
      setTenants(res.data?.tenants || []);
    } catch (err) {
      console.error('Failed to load tenants', err);
      setError('Otelleri yüklerken bir hata oluştu');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTenants();
  }, []);

  const handleToggle = async (tenantId, moduleKey, value) => {
    setSaving(true);
    setError(null);
    try {
      const currentTenant = tenants.find((t) => t.id === tenantId || t._id === tenantId);
      const currentModules = currentTenant?.modules || {};
      const updatedModules = { ...currentModules, [moduleKey]: value };

      const res = await axios.patch(`/admin/tenants/${tenantId}/modules`, {
        modules: updatedModules,
      });

      const updated = res.data;
      setTenants((prev) =>
        prev.map((t) =>
          t.id === tenantId || t._id === tenantId
            ? { ...t, modules: updated.modules }
            : t
        )
      );
    } catch (err) {
      console.error('Failed to update modules', err);
      setError('Modülleri güncellerken bir hata oluştu');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="admin-tenants">
      <div className="p-4 md:p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Otel Modül Yönetimi</h1>
            <p className="text-sm text-gray-600">
              Her otel için hangi modüllerin aktif olacağını buradan yönetebilirsiniz.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={loadTenants} disabled={loading}>
            Yenile
          </Button>
        </div>

        {error && (
          <div className="p-3 rounded-md bg-red-50 text-red-700 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-sm text-gray-500">Oteller yükleniyor...</div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {tenants.map((t) => (
              <Card key={t.id || t._id}>
                <CardHeader>
                  <CardTitle className="text-base">
                    {t.property_name || t.name || 'Otel'}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {MODULE_KEYS.map(({ key, label }) => {
                      const enabled = (t.modules && t.modules[key]) !== false;
                      return (
                        <div key={key} className="flex items-center justify-between py-1">
                          <span className="text-sm text-gray-700">{label}</span>
                          <Switch
                            checked={enabled}
                            disabled={saving}
                            onCheckedChange={(val) => handleToggle(t.id || t._id, key, val)}
                          />
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default AdminTenants;
