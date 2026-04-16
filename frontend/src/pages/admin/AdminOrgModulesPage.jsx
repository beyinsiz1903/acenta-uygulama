import React, { useState, useEffect, useMemo, useCallback } from "react";
import { api } from "../../lib/api";
import {
  Loader2, Save, RotateCcw, CheckSquare, Square, Package,
  ChevronDown, ChevronRight, Search, ToggleLeft, ToggleRight,
} from "lucide-react";
import { toast } from "sonner";

function ModuleToggle({ mod, enabled, onToggle }) {
  return (
    <button
      onClick={() => onToggle(mod.key)}
      className="flex items-center gap-3 w-full text-left px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors group"
      data-testid={`module-toggle-${mod.key}`}
    >
      {enabled ? (
        <CheckSquare className="w-5 h-5 text-primary flex-shrink-0" />
      ) : (
        <Square className="w-5 h-5 text-muted-foreground flex-shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium">{mod.label}</div>
        {mod.description && (
          <div className="text-xs text-muted-foreground mt-0.5 truncate">{mod.description}</div>
        )}
      </div>
    </button>
  );
}

function ModuleGroup({ group, enabledSet, onToggle, onToggleGroup }) {
  const [expanded, setExpanded] = useState(true);
  const allEnabled = group.modules.every((m) => enabledSet.has(m.key));
  const someEnabled = group.modules.some((m) => enabledSet.has(m.key));
  const enabledCount = group.modules.filter((m) => enabledSet.has(m.key)).length;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )}
          <span className="text-sm font-bold uppercase tracking-wider text-foreground">
            {group.group}
          </span>
          <span className="text-xs text-muted-foreground">
            {enabledCount}/{group.modules.length}
          </span>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onToggleGroup(group, !allEnabled); }}
          className="text-xs text-primary hover:underline"
          data-testid={`group-toggle-${group.group}`}
        >
          {allEnabled ? "Tümünü Kaldır" : "Tümünü Seç"}
        </button>
      </button>
      {expanded && (
        <div className="border-t border-gray-100 dark:border-gray-700 px-2 py-1">
          {group.modules.map((mod) => (
            <ModuleToggle
              key={mod.key}
              mod={mod}
              enabled={enabledSet.has(mod.key)}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function AdminOrgModulesPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [registry, setRegistry] = useState(null);
  const [enabledModules, setEnabledModules] = useState([]);
  const [allEnabled, setAllEnabled] = useState(true);
  const [originalModules, setOriginalModules] = useState([]);
  const [search, setSearch] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [regRes, modRes] = await Promise.all([
        api.get("/admin/org-modules/registry"),
        api.get("/admin/org-modules"),
      ]);
      setRegistry(regRes.data);
      const enabled = modRes.data?.enabled_modules || [];
      const isAllEnabled = modRes.data?.all_enabled !== false;
      if (isAllEnabled) {
        const allKeys = (regRes.data?.groups || []).flatMap((g) => g.modules.map((m) => m.key));
        setEnabledModules(allKeys);
        setOriginalModules(allKeys);
      } else {
        setEnabledModules(enabled);
        setOriginalModules(enabled);
      }
      setAllEnabled(isAllEnabled);
    } catch (e) {
      toast.error("Modül bilgileri yüklenemedi");
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const enabledSet = useMemo(() => new Set(enabledModules), [enabledModules]);

  const hasChanges = useMemo(() => {
    const orig = new Set(originalModules);
    if (orig.size !== enabledSet.size) return true;
    for (const k of enabledSet) { if (!orig.has(k)) return true; }
    return false;
  }, [originalModules, enabledSet]);

  const toggle = (key) => {
    setEnabledModules((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const toggleGroup = (group, enable) => {
    const keys = group.modules.map((m) => m.key);
    setEnabledModules((prev) => {
      const withoutGroup = prev.filter((k) => !keys.includes(k));
      return enable ? [...withoutGroup, ...keys] : withoutGroup;
    });
  };

  const selectAll = () => {
    if (!registry) return;
    const allKeys = registry.groups.flatMap((g) => g.modules.map((m) => m.key));
    setEnabledModules(allKeys);
  };

  const clearAll = () => setEnabledModules([]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const allKeys = registry.groups.flatMap((g) => g.modules.map((m) => m.key));
      const isAll = allKeys.every((k) => enabledModules.includes(k));
      if (isAll) {
        await api.delete("/admin/org-modules");
        toast.success("Tüm modüller aktif edildi (kısıtlama yok)");
      } else {
        await api.put("/admin/org-modules", { enabled_modules: enabledModules });
        toast.success(`${enabledModules.length} modül aktif olarak kaydedildi`);
      }
      setOriginalModules([...enabledModules]);
      window.dispatchEvent(new CustomEvent("org-modules-updated"));
    } catch (e) {
      toast.error(e.response?.data?.error?.message || "Kaydetme hatası");
    }
    setSaving(false);
  };

  const handleReset = async () => {
    setSaving(true);
    try {
      await api.delete("/admin/org-modules");
      toast.success("Modül kısıtlamaları kaldırıldı — tüm modüller açık");
      await loadData();
      window.dispatchEvent(new CustomEvent("org-modules-updated"));
    } catch (e) {
      toast.error("Sıfırlama hatası");
    }
    setSaving(false);
  };

  const filteredGroups = useMemo(() => {
    if (!registry?.groups) return [];
    if (!search.trim()) return registry.groups;
    const q = search.toLowerCase();
    return registry.groups
      .map((g) => ({
        ...g,
        modules: g.modules.filter(
          (m) => m.label.toLowerCase().includes(q) || m.key.includes(q) ||
            (m.description && m.description.toLowerCase().includes(q))
        ),
      }))
      .filter((g) => g.modules.length > 0);
  }, [registry, search]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="org-modules-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Package className="w-6 h-6 text-primary" />
            Modül Yönetimi
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Acentenizin kullanacağı modülleri seçin. Kapalı modüller menüde ve sistemde görünmez.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            disabled={saving}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-sm disabled:opacity-50"
            data-testid="reset-modules"
          >
            <RotateCcw className="w-4 h-4" />
            Tümünü Aç
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors text-sm font-medium"
            data-testid="save-modules"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Kaydet
          </button>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Modül ara..."
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
            data-testid="module-search"
          />
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-muted-foreground">
            {enabledModules.length}/{registry?.all_keys?.length || 0} modül aktif
          </span>
          <button onClick={selectAll} className="text-primary hover:underline text-xs" data-testid="select-all">Tümünü Seç</button>
          <span className="text-muted-foreground">|</span>
          <button onClick={clearAll} className="text-red-500 hover:underline text-xs" data-testid="clear-all">Tümünü Kaldır</button>
        </div>
      </div>

      {hasChanges && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 text-sm text-amber-800 dark:text-amber-200 flex items-center gap-2">
          <ToggleLeft className="w-4 h-4 flex-shrink-0" />
          Kaydedilmemiş değişiklikler var. Değişiklikleri uygulamak için "Kaydet" butonuna tıklayın.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filteredGroups.map((group) => (
          <ModuleGroup
            key={group.group}
            group={group}
            enabledSet={enabledSet}
            onToggle={toggle}
            onToggleGroup={toggleGroup}
          />
        ))}
      </div>

      {filteredGroups.length === 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border p-10 text-center">
          <Package className="w-10 h-10 mx-auto text-muted-foreground/40" />
          <p className="mt-3 font-medium">Aramanızla eşleşen modül bulunamadı</p>
        </div>
      )}
    </div>
  );
}
