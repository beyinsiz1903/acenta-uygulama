/**
 * Syroce Design System (SDS) — FilterBar
 *
 * Reusable search + filter bar with active filter chips.
 */
import React, { useState, useEffect, useCallback } from "react";
import { cn } from "../../lib/utils";
import { Input } from "../../components/ui/input";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { Search, X, RotateCcw } from "lucide-react";

function useDebounce(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export function FilterBar({
  search,
  filters = [],
  onReset,
  actions,
  className,
}) {
  const [searchInput, setSearchInput] = useState(search?.value || "");
  const debouncedSearch = useDebounce(searchInput);

  useEffect(() => {
    if (search?.onChange && debouncedSearch !== search.value) {
      search.onChange(debouncedSearch);
    }
  }, [debouncedSearch]);

  // Sync external value
  useEffect(() => {
    if (search?.value !== undefined && search.value !== searchInput) {
      setSearchInput(search.value);
    }
  }, [search?.value]);

  const activeFilterCount = filters.filter(
    (f) => f.value && f.value !== "" && f.value !== "all"
  ).length;

  const handleReset = useCallback(() => {
    setSearchInput("");
    onReset?.();
  }, [onReset]);

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)} data-testid="filter-bar">
      {/* Search */}
      {search && (
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={search.placeholder || "Ara..."}
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-9 h-9 w-[220px]"
            data-testid="filter-bar-search"
          />
          {searchInput && (
            <button
              onClick={() => setSearchInput("")}
              className="absolute right-2 top-2.5 text-muted-foreground hover:text-foreground"
              data-testid="filter-bar-search-clear"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      )}

      {/* Filter dropdowns */}
      {filters.map((filter) => (
        <Select
          key={filter.key}
          value={filter.value || "all"}
          onValueChange={(val) => filter.onChange(val === "all" ? "" : val)}
        >
          <SelectTrigger
            className="h-9 w-auto min-w-[130px]"
            data-testid={`filter-bar-${filter.key}`}
          >
            <SelectValue placeholder={filter.label} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{filter.label} (Tümü)</SelectItem>
            {filter.options.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ))}

      {/* Reset */}
      {(activeFilterCount > 0 || searchInput) && (
        <Button
          variant="ghost"
          size="sm"
          onClick={handleReset}
          className="h-9 gap-1.5 text-muted-foreground"
          data-testid="filter-bar-reset"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Sıfırla
          {activeFilterCount > 0 && (
            <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
              {activeFilterCount}
            </Badge>
          )}
        </Button>
      )}

      {/* Spacer + toolbar actions */}
      {actions && <div className="ml-auto flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export default FilterBar;
