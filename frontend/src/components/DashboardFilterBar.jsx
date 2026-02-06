import React, { useState } from 'react';
import {
  Filter, Calendar, Download, RotateCcw,
  ChevronDown, Maximize2, Minimize2,
} from 'lucide-react';
import {
  PRESETS, STATUS_OPTIONS, DEFAULT_FILTERS,
} from '../lib/dashboardFilters';

/* ------------------------------------------------------------------ */
/*  Chip                                                                */
/* ------------------------------------------------------------------ */
function Chip({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`px-2.5 py-1 text-[11px] font-medium rounded-md border transition-colors
        ${active
          ? 'bg-primary text-primary-foreground border-primary'
          : 'bg-card text-muted-foreground border-border/60 hover:bg-muted/50'
        }
      `}
    >
      {label}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  Select                                                              */
/* ------------------------------------------------------------------ */
function MiniSelect({ value, onChange, options, label }) {
  return (
    <div className="flex items-center gap-1.5">
      {label && <span className="text-[11px] text-muted-foreground">{label}</span>}
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="appearance-none bg-card border border-border/60 rounded-md px-2.5 py-1 pr-6 text-[11px] font-medium text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        >
          {options.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground pointer-events-none" />
      </div>
    </div>
  );
}

/* ================================================================== */
/*  FILTER BAR                                                         */
/* ================================================================== */
export default function DashboardFilterBar({
  filters,
  onFiltersChange,
  onApply,
  onReset,
  onExport,
  density,
  onDensityChange,
}) {
  const [expanded, setExpanded] = useState(false);

  const updateFilter = (key, value) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  const isDefault = filters.preset === DEFAULT_FILTERS.preset
    && filters.status === DEFAULT_FILTERS.status
    && !filters.product;

  return (
    <div
      className="rounded-[10px] border border-border/60 bg-card px-3 py-2.5"
      data-testid="dashboard-filter-bar"
    >
      {/* Main row */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter className="h-3.5 w-3.5 text-muted-foreground shrink-0" />

        {/* Presets */}
        <div className="flex items-center gap-1">
          {PRESETS.map((p) => (
            <Chip
              key={p.value}
              label={p.label}
              active={filters.preset === p.value}
              onClick={() => updateFilter('preset', p.value)}
            />
          ))}
        </div>

        <div className="hidden sm:block h-4 w-px bg-border/60" />

        {/* Status */}
        <MiniSelect
          label="Durum:"
          value={filters.status}
          onChange={(v) => updateFilter('status', v)}
          options={STATUS_OPTIONS}
        />

        {/* Spacer */}
        <div className="flex-1" />

        {/* Density toggle */}
        <button
          onClick={() => onDensityChange(density === 'compact' ? 'comfort' : 'compact')}
          className="flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded-md border border-border/60 bg-card text-muted-foreground hover:bg-muted/50 transition-colors"
          title={density === 'compact' ? 'Rahat görünüm' : 'Kompakt görünüm'}
          data-testid="density-toggle"
        >
          {density === 'compact'
            ? <><Maximize2 className="h-3 w-3" /> Rahat</>
            : <><Minimize2 className="h-3 w-3" /> Kompakt</>
          }
        </button>

        {/* Export */}
        <button
          onClick={onExport}
          className="flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded-md border border-border/60 bg-card text-muted-foreground hover:bg-muted/50 transition-colors"
          title="CSV olarak dışa aktar"
          data-testid="filter-export"
        >
          <Download className="h-3 w-3" /> CSV
        </button>

        {/* Expand on mobile */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="sm:hidden flex items-center gap-1 px-2 py-1 text-[11px] rounded-md border border-border/60 bg-card text-muted-foreground"
        >
          <ChevronDown className={`h-3 w-3 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </button>

        {/* Apply / Reset */}
        <button
          onClick={onApply}
          className="px-3 py-1 text-[11px] font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          data-testid="filter-apply"
        >
          Uygula
        </button>

        {!isDefault && (
          <button
            onClick={onReset}
            className="flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded-md border border-border/60 text-muted-foreground hover:bg-muted/50 transition-colors"
            data-testid="filter-reset"
          >
            <RotateCcw className="h-3 w-3" /> Sıfırla
          </button>
        )}
      </div>

      {/* Expanded filters (mobile) */}
      {expanded && (
        <div className="mt-2 pt-2 border-t border-border/40 flex flex-wrap items-center gap-2 sm:hidden">
          <MiniSelect
            label="Durum:"
            value={filters.status}
            onChange={(v) => updateFilter('status', v)}
            options={STATUS_OPTIONS}
          />
        </div>
      )}

      {/* Disclaimer */}
      {filters.status !== 'all' && (
        <p className="text-[10px] text-muted-foreground/70 mt-1.5">
          Bazı metrikler özet veridir; filtreler grafikleri ve listeleri etkiler.
        </p>
      )}
    </div>
  );
}
