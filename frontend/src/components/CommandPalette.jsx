import React, { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
  CommandShortcut,
} from "./ui/command";
import {
  LayoutGrid,
  Ticket,
  Users,
  DollarSign,
  BarChart3,
  Settings,
  Search,
  Plus,
  Building2,
  ArrowRight,
  MapPin,
  Loader2,
  FileText,
  Zap,
} from "lucide-react";
import { api } from "../lib/api";
import { cn } from "../lib/utils";

// ─── Quick Actions ───
const QUICK_ACTIONS = [
  {
    id: "new-booking",
    label: "Yeni Rezervasyon",
    icon: Plus,
    action: "/app/agency/bookings/new",
    shortcut: "N",
    group: "actions",
  },
];

// ─── Navigation Pages ───
const NAV_PAGES = [
  { id: "nav-dashboard", label: "Dashboard", icon: LayoutGrid, path: "/app", shortcut: "G D" },
  { id: "nav-reservations", label: "Rezervasyonlar", icon: Ticket, path: "/app/reservations", shortcut: "G R" },
  { id: "nav-customers", label: "Müşteriler", icon: Users, path: "/app/crm/customers", shortcut: "G C" },
  { id: "nav-finance", label: "Finans & Mutabakat", icon: DollarSign, path: "/app/admin/finance/settlements", shortcut: "G F" },
  { id: "nav-reports", label: "Raporlar", icon: BarChart3, path: "/app/reports" },
  { id: "nav-hotels", label: "Oteller", icon: Building2, path: "/app/agency/hotels" },
  { id: "nav-tours", label: "Turlar", icon: MapPin, path: "/app/tours" },
  { id: "nav-integrations", label: "Entegrasyonlar", icon: Zap, path: "/app/admin/integrations" },
  { id: "nav-settings", label: "Ayarlar", icon: Settings, path: "/app/settings", shortcut: "G S" },
];

const SEARCH_TYPE_ICONS = {
  customer: Users,
  booking: Ticket,
  hotel: Building2,
  tour: MapPin,
};

const SEARCH_TYPE_LABELS = {
  customers: "Müşteriler",
  bookings: "Rezervasyonlar",
  hotels: "Oteller",
  tours: "Turlar",
};

export function CommandPalette({ open, onOpenChange }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const abortRef = useRef(null);
  const debounceRef = useRef(null);

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setQuery("");
      setSearchResults(null);
      setIsSearching(false);
    }
  }, [open]);

  // Debounced backend search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (abortRef.current) abortRef.current.abort();

    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setSearchResults(null);
      setIsSearching(false);
      return;
    }

    setIsSearching(true);
    debounceRef.current = setTimeout(async () => {
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const { data } = await api.get("/search", {
          params: { q: trimmed, limit: 5 },
          signal: controller.signal,
        });
        setSearchResults(data);
      } catch (err) {
        if (err?.code !== "ERR_CANCELED") {
          setSearchResults(null);
        }
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  const handleSelect = useCallback(
    (value) => {
      onOpenChange(false);
      // value is the path/route
      if (value) navigate(value);
    },
    [navigate, onOpenChange],
  );

  const hasQuery = query.trim().length >= 2;
  const hasResults = searchResults && searchResults.total_results > 0;
  const searchSections = searchResults?.sections || {};

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput
        placeholder="Sayfa, müşteri, rezervasyon ara..."
        value={query}
        onValueChange={setQuery}
        data-testid="command-palette-input"
      />
      <CommandList>
        {/* Loading indicator */}
        {isSearching && (
          <div className="flex items-center justify-center gap-2 py-4 text-sm text-muted-foreground" data-testid="command-palette-loading">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Aranıyor...</span>
          </div>
        )}

        {/* Empty state */}
        {!isSearching && hasQuery && !hasResults && (
          <CommandEmpty data-testid="command-palette-empty">
            <span className="text-muted-foreground">Sonuç bulunamadı.</span>
          </CommandEmpty>
        )}

        {/* ─── Backend Search Results ─── */}
        {hasResults &&
          Object.entries(searchSections).map(([sectionKey, items]) => {
            if (!items || items.length === 0) return null;
            const SectionIcon = SEARCH_TYPE_ICONS[items[0]?.type] || FileText;
            return (
              <CommandGroup
                key={sectionKey}
                heading={SEARCH_TYPE_LABELS[sectionKey] || sectionKey}
                data-testid={`command-palette-section-${sectionKey}`}
              >
                {items.map((item) => {
                  const Icon = SEARCH_TYPE_ICONS[item.type] || FileText;
                  return (
                    <CommandItem
                      key={item.id}
                      value={`${item.type}-${item.title}-${item.subtitle}`}
                      onSelect={() => handleSelect(item.route)}
                      data-testid={`command-palette-result-${item.type}-${item.id}`}
                    >
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <div className="flex flex-col gap-0.5 min-w-0">
                        <span className="truncate text-sm font-medium">{item.title}</span>
                        {item.subtitle && (
                          <span className="truncate text-xs text-muted-foreground">{item.subtitle}</span>
                        )}
                      </div>
                      {item.status && (
                        <span
                          className={cn(
                            "ml-auto shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium",
                            item.status === "confirmed" && "bg-emerald-500/10 text-emerald-600",
                            item.status === "pending" && "bg-amber-500/10 text-amber-600",
                            item.status === "cancelled" && "bg-red-500/10 text-red-600",
                            item.status === "draft" && "bg-muted text-muted-foreground",
                          )}
                        >
                          {item.status}
                        </span>
                      )}
                      <ArrowRight className="ml-auto h-3 w-3 shrink-0 text-muted-foreground/40" />
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            );
          })}

        {/* ─── Quick Actions (shown when no search query) ─── */}
        {!hasQuery && (
          <>
            <CommandGroup heading="Hızlı İşlemler" data-testid="command-palette-quick-actions">
              {QUICK_ACTIONS.map((action) => {
                const Icon = action.icon;
                return (
                  <CommandItem
                    key={action.id}
                    value={action.label}
                    onSelect={() => handleSelect(action.action)}
                    data-testid={`command-palette-action-${action.id}`}
                  >
                    <div className="flex h-6 w-6 items-center justify-center rounded-md border bg-background">
                      <Icon className="h-3.5 w-3.5" />
                    </div>
                    <span>{action.label}</span>
                    {action.shortcut && <CommandShortcut>{action.shortcut}</CommandShortcut>}
                  </CommandItem>
                );
              })}
            </CommandGroup>

            <CommandSeparator />

            {/* ─── Navigation Pages ─── */}
            <CommandGroup heading="Sayfalar" data-testid="command-palette-pages">
              {NAV_PAGES.map((page) => {
                const Icon = page.icon;
                return (
                  <CommandItem
                    key={page.id}
                    value={page.label}
                    onSelect={() => handleSelect(page.path)}
                    data-testid={`command-palette-page-${page.id}`}
                  >
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    <span>{page.label}</span>
                    {page.shortcut && <CommandShortcut>{page.shortcut}</CommandShortcut>}
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </>
        )}
      </CommandList>

      {/* Footer with hints */}
      <div className="border-t px-3 py-2 flex items-center justify-between text-[11px] text-muted-foreground" data-testid="command-palette-footer">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
              ↑↓
            </kbd>
            gezin
          </span>
          <span className="flex items-center gap-1">
            <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
              ↵
            </kbd>
            seç
          </span>
          <span className="flex items-center gap-1">
            <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
              esc
            </kbd>
            kapat
          </span>
        </div>
        <span className="hidden sm:inline text-muted-foreground/60">
          <Search className="inline h-3 w-3 mr-1" />
          2+ karakter ile arama yapın
        </span>
      </div>
    </CommandDialog>
  );
}
