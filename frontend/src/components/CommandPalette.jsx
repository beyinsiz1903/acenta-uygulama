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
} from "./ui/command";
import {
  ArrowRight,
  FileText,
  Loader2,
  Search,
  Users,
  Ticket,
  Building2,
  MapPin,
} from "lucide-react";
import { api } from "../lib/api";
import { cn } from "../lib/utils";
import { getPersonaNavSections, getPersonaAccountLinks, flattenNavItems } from "../navigation";

// ─── Backend search result type icons ───
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

/**
 * Builds searchable page list from persona navigation metadata.
 * - Includes all items with visibleInSearch: true
 * - Excludes legacy: true items
 * - Groups by sectionGroup
 */
function buildSearchablePages(persona) {
  const sections = getPersonaNavSections(persona);
  const accountLinks = getPersonaAccountLinks(persona);

  // Flatten all nav items (includes directAccessOnly items)
  const allItems = flattenNavItems(sections);

  // Add account links with a group
  const accountItems = (accountLinks || [])
    .filter((l) => l.to && l.visibleInSearch !== false)
    .map((l) => ({ ...l, sectionGroup: "HESAP" }));

  const combined = [...allItems, ...accountItems];

  // Filter: visibleInSearch AND not legacy
  return combined.filter(
    (item) => item.visibleInSearch !== false && item.legacy !== true
  );
}

/**
 * Groups flat items by sectionGroup.
 * Returns Map<groupName, items[]> preserving insertion order.
 */
function groupBySection(items) {
  const groups = new Map();
  for (const item of items) {
    const g = item.sectionGroup || "DİĞER";
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g).push(item);
  }
  return groups;
}

export function CommandPalette({ open, onOpenChange, persona = "admin" }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const abortRef = useRef(null);
  const debounceRef = useRef(null);

  // Build persona-based searchable pages
  const searchablePages = useMemo(() => buildSearchablePages(persona), [persona]);
  const groupedPages = useMemo(() => groupBySection(searchablePages), [searchablePages]);

  // Filter pages by local query (instant, no backend call needed for navigation)
  const filteredPageGroups = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (trimmed.length < 1) return groupedPages;

    const filtered = new Map();
    for (const [group, items] of groupedPages) {
      const matched = items.filter((item) => {
        const label = (item.label || "").toLowerCase();
        const path = (item.to || "").toLowerCase();
        const aliases = (item.moduleAliases || []).join(" ").toLowerCase();
        return label.includes(trimmed) || path.includes(trimmed) || aliases.includes(trimmed);
      });
      if (matched.length > 0) filtered.set(group, matched);
    }
    return filtered;
  }, [query, groupedPages]);

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setQuery("");
      setSearchResults(null);
      setIsSearching(false);
    }
  }, [open]);

  // Debounced backend search (customers, bookings, etc.)
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
      if (value) navigate(value);
    },
    [navigate, onOpenChange],
  );

  const hasQuery = query.trim().length >= 2;
  const hasBackendResults = searchResults && searchResults.total_results > 0;
  const searchSections = searchResults?.sections || {};
  const hasPageResults = filteredPageGroups.size > 0;

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

        {/* Empty state — only when query is typed and no results anywhere */}
        {!isSearching && hasQuery && !hasBackendResults && !hasPageResults && (
          <CommandEmpty data-testid="command-palette-empty">
            <span className="text-muted-foreground">Sonuç bulunamadı.</span>
          </CommandEmpty>
        )}

        {/* ─── Backend Search Results (customers, bookings, etc.) ─── */}
        {hasBackendResults &&
          Object.entries(searchSections).map(([sectionKey, items]) => {
            if (!items || items.length === 0) return null;
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

        {/* ─── Separator between backend results and pages ─── */}
        {hasBackendResults && hasPageResults && <CommandSeparator />}

        {/* ─── Navigation Pages (persona-based, grouped by section) ─── */}
        {hasPageResults &&
          Array.from(filteredPageGroups.entries()).map(([groupName, items]) => (
            <CommandGroup
              key={groupName}
              heading={groupName}
              data-testid={`command-palette-group-${groupName.toLowerCase().replace(/[^a-z0-9]/g, "-")}`}
            >
              {items.map((item) => {
                const Icon = item.icon || FileText;
                return (
                  <CommandItem
                    key={item.key}
                    value={`${item.label} ${item.to} ${(item.moduleAliases || []).join(" ")}`}
                    onSelect={() => handleSelect(item.to)}
                    data-testid={`command-palette-page-${item.key}`}
                  >
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    <div className="flex flex-col gap-0.5 min-w-0">
                      <span className="truncate text-sm">{item.label}</span>
                      <span className="truncate text-[11px] text-muted-foreground/60">{item.to}</span>
                    </div>
                    {item.directAccessOnly && (
                      <span className="ml-auto shrink-0 rounded-full bg-muted px-1.5 py-0.5 text-[9px] font-medium text-muted-foreground">
                        gizli
                      </span>
                    )}
                    <ArrowRight className="ml-auto h-3 w-3 shrink-0 text-muted-foreground/40" />
                  </CommandItem>
                );
              })}
            </CommandGroup>
          ))}
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
          {searchablePages.length} sayfa aranabilir
        </span>
      </div>
    </CommandDialog>
  );
}
