/**
 * Dashboard filter state management
 * Handles URL query params + localStorage persistence
 */

const STORAGE_KEY = 'dashboard_filters';
const DENSITY_KEY = 'dashboard_density';

export const PRESETS = [
  { value: 'today', label: 'Bugün', days: 1 },
  { value: '7d', label: '7G', days: 7 },
  { value: '14d', label: '14G', days: 14 },
  { value: '30d', label: '30G', days: 30 },
  { value: 'this_month', label: 'Bu Ay', days: null },
];

export const STATUS_OPTIONS = [
  { value: 'all', label: 'Tümü' },
  { value: 'pending', label: 'Beklemede' },
  { value: 'approved', label: 'Onaylı' },
  { value: 'paid', label: 'Ödendi' },
];

export const DEFAULT_FILTERS = {
  preset: '30d',
  from: '',
  to: '',
  status: 'all',
  product: '',
  density: 'compact',
};

function getThisMonthRange() {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth(), 1);
  return {
    from: from.toISOString().slice(0, 10),
    to: now.toISOString().slice(0, 10),
  };
}

export function getPresetDays(preset) {
  const p = PRESETS.find((pr) => pr.value === preset);
  return p?.days || 30;
}

export function getPresetDateRange(preset) {
  if (preset === 'this_month') return getThisMonthRange();
  const days = getPresetDays(preset);
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - days);
  return { from: from.toISOString().slice(0, 10), to: to.toISOString().slice(0, 10) };
}

export function parseQueryToFilters(searchStr) {
  const params = new URLSearchParams(searchStr);
  return {
    preset: params.get('preset') || '',
    from: params.get('from') || '',
    to: params.get('to') || '',
    status: params.get('status') || 'all',
    product: params.get('product') || '',
    density: params.get('density') || 'compact',
  };
}

export function filtersToQuery(filters) {
  const params = new URLSearchParams();
  if (filters.preset) params.set('preset', filters.preset);
  if (filters.from) params.set('from', filters.from);
  if (filters.to) params.set('to', filters.to);
  if (filters.status && filters.status !== 'all') params.set('status', filters.status);
  if (filters.product) params.set('product', filters.product);
  if (filters.density && filters.density !== 'compact') params.set('density', filters.density);
  const str = params.toString();
  return str ? `?${str}` : '';
}

export function loadFromLocalStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return null;
}

export function saveToLocalStorage(filters) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
  } catch { /* ignore */ }
}

export function loadDensity() {
  try {
    return localStorage.getItem(DENSITY_KEY) || 'compact';
  } catch { return 'compact'; }
}

export function saveDensity(density) {
  try {
    localStorage.setItem(DENSITY_KEY, density);
  } catch { /* ignore */ }
}

/**
 * Merge sources: URL > localStorage > defaults
 */
export function resolveFilters(searchStr) {
  const urlFilters = parseQueryToFilters(searchStr);
  const stored = loadFromLocalStorage();
  const hasUrlParams = searchStr && searchStr.length > 1;

  if (hasUrlParams) {
    // URL overrides everything
    return {
      ...DEFAULT_FILTERS,
      ...urlFilters,
      density: urlFilters.density || loadDensity(),
    };
  }

  if (stored) {
    return {
      ...DEFAULT_FILTERS,
      ...stored,
      density: stored.density || loadDensity(),
    };
  }

  return { ...DEFAULT_FILTERS, density: loadDensity() };
}

/**
 * Export dashboard data as CSV
 */
export function exportDashboardCSV({ kpis, chartData, attentionItems, chartMetric, dateRange }) {
  const lines = [];
  lines.push('Dashboard Export');
  lines.push(`Period: ${dateRange.from || 'N/A'} — ${dateRange.to || 'N/A'}`);
  lines.push('');

  // KPIs
  lines.push('== KPI Summary ==');
  lines.push('Metric,Value');
  if (kpis) {
    Object.entries(kpis).forEach(([k, v]) => lines.push(`${k},${v}`));
  }
  lines.push('');

  // Chart
  lines.push('== Chart Data ==');
  lines.push(`Day,${chartMetric === 'revenue' ? 'Revenue' : 'Count'}`);
  if (chartData) {
    chartData.forEach((d) => lines.push(`${d.day},${d[chartMetric] || 0}`));
  }
  lines.push('');

  // Attention
  lines.push('== Attention Items ==');
  lines.push('Item,Count');
  if (attentionItems) {
    attentionItems.forEach((it) => lines.push(`${it.label},${it.count}`));
  }

  const csv = lines.join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `dashboard_export_${dateRange.from || 'all'}_${dateRange.to || 'all'}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
