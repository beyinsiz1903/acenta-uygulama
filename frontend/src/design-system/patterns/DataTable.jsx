/**
 * Syroce Design System (SDS) — DataTable
 *
 * Enterprise-grade table component with sorting, filtering, pagination,
 * row selection, empty/loading states, and automatic list virtualization.
 *
 * Built on @tanstack/react-table + @tanstack/react-virtual + shadcn Table primitives.
 *
 * Virtualization: Automatically enabled when visible row count exceeds
 * `virtualizeThreshold` (default 100). This keeps DOM node count low
 * for large datasets while preserving the same API for consumers.
 */
import React, { useState, useMemo, useRef } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Checkbox } from "../../components/ui/checkbox";
import { Skeleton } from "../../components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { cn } from "../../lib/utils";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Search,
} from "lucide-react";

// ─── Selection column helper ───
export const selectionColumn = {
  id: "select",
  header: ({ table }) => (
    <Checkbox
      checked={
        table.getIsAllPageRowsSelected() ||
        (table.getIsSomePageRowsSelected() && "indeterminate")
      }
      onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
      aria-label="Tümünü seç"
      data-testid="datatable-select-all"
    />
  ),
  cell: ({ row }) => (
    <Checkbox
      checked={row.getIsSelected()}
      onCheckedChange={(value) => row.toggleSelected(!!value)}
      aria-label="Satır seç"
      data-testid={`datatable-select-row-${row.index}`}
    />
  ),
  enableSorting: false,
  enableHiding: false,
  size: 40,
};

// ─── Sortable header helper ───
export function SortableHeader({ column, children }) {
  const sorted = column.getIsSorted();
  return (
    <Button
      variant="ghost"
      size="sm"
      className="-ml-3 h-8 gap-1 font-medium"
      onClick={() => column.toggleSorting(sorted === "asc")}
      data-testid={`datatable-sort-${column.id}`}
    >
      {children}
      {sorted === "asc" ? (
        <ArrowUp className="h-3.5 w-3.5" />
      ) : sorted === "desc" ? (
        <ArrowDown className="h-3.5 w-3.5" />
      ) : (
        <ArrowUpDown className="h-3.5 w-3.5 opacity-40" />
      )}
    </Button>
  );
}

// ─── Skeleton rows for loading ───
function SkeletonRows({ columns, rows = 5 }) {
  return Array.from({ length: rows }).map((_, i) => (
    <TableRow key={`skeleton-${i}`}>
      {columns.map((col, j) => (
        <TableCell key={`skeleton-${i}-${j}`}>
          <Skeleton className="h-4 w-full max-w-[200px]" />
        </TableCell>
      ))}
    </TableRow>
  ));
}

// ─── Pagination component ───
function DataTablePagination({ table, pageSizeOptions = [10, 20, 50] }) {
  return (
    <div className="flex items-center justify-between px-2 py-3" data-testid="datatable-pagination">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>
          {table.getFilteredSelectedRowModel().rows.length > 0 && (
            <>{table.getFilteredSelectedRowModel().rows.length} / </>
          )}
          {table.getFilteredRowModel().rows.length} kayıt
        </span>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Sayfa başı:</span>
          <Select
            value={String(table.getState().pagination.pageSize)}
            onValueChange={(value) => table.setPageSize(Number(value))}
          >
            <SelectTrigger className="h-8 w-[70px]" data-testid="datatable-page-size">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {pageSizeOptions.map((size) => (
                <SelectItem key={size} value={String(size)}>
                  {size}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-1 text-sm text-muted-foreground">
          Sayfa {table.getState().pagination.pageIndex + 1} / {table.getPageCount() || 1}
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
            data-testid="datatable-first-page"
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            data-testid="datatable-prev-page"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            data-testid="datatable-next-page"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
            data-testid="datatable-last-page"
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Main DataTable component ───
export function DataTable({
  data = [],
  columns,
  loading = false,
  emptyState,
  // Search
  searchable = false,
  searchPlaceholder = "Ara...",
  searchValue: externalSearchValue,
  onSearchChange: externalSearchChange,
  // Pagination
  pageSize = 10,
  pageSizeOptions,
  // Sorting
  defaultSort,
  // Selection
  selectable = false,
  onSelectionChange,
  // Row click
  onRowClick,
  // Toolbar
  toolbar,
  // Styling
  className,
  // Virtualization — auto-enabled when row count > threshold
  virtualizeThreshold = 100,
  rowHeight = 48,
}) {
  const [sorting, setSorting] = useState(
    defaultSort ? [{ id: defaultSort.column, desc: defaultSort.direction === "desc" }] : []
  );
  const [rowSelection, setRowSelection] = useState({});
  const [internalSearch, setInternalSearch] = useState("");
  const [columnFilters, setColumnFilters] = useState([]);

  const searchValue = externalSearchValue ?? internalSearch;
  const setSearchValue = externalSearchChange ?? setInternalSearch;

  const finalColumns = useMemo(() => {
    if (selectable) {
      return [selectionColumn, ...columns];
    }
    return columns;
  }, [columns, selectable]);

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data,
    columns: finalColumns,
    state: {
      sorting,
      rowSelection,
      columnFilters,
      globalFilter: searchValue,
    },
    onSortingChange: setSorting,
    onRowSelectionChange: (updater) => {
      const newSelection = typeof updater === "function" ? updater(rowSelection) : updater;
      setRowSelection(newSelection);
      if (onSelectionChange) {
        const selectedRows = Object.keys(newSelection)
          .filter((key) => newSelection[key])
          .map((key) => data[parseInt(key)]);
        onSelectionChange(selectedRows);
      }
    },
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setSearchValue,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: { pageSize },
    },
  });

  const rows = table.getRowModel().rows;
  const shouldVirtualize = !loading && rows.length >= virtualizeThreshold;

  return (
    <div className={cn("space-y-3", className)} data-testid="datatable-container">
      {/* Toolbar area */}
      {(searchable || toolbar) && (
        <div className="flex items-center justify-between gap-3">
          {searchable && (
            <div className="relative max-w-sm">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={searchPlaceholder}
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                className="pl-9 h-9"
                data-testid="datatable-search"
              />
            </div>
          )}
          {toolbar && <div className="flex items-center gap-2">{toolbar}</div>}
        </div>
      )}

      {/* Table */}
      <div className="rounded-lg border bg-card">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    style={{ width: header.getSize() !== 150 ? header.getSize() : undefined }}
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {loading ? (
              <SkeletonRows columns={finalColumns} />
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={finalColumns.length} className="h-24 text-center">
                  {emptyState || (
                    <p className="text-muted-foreground">Kayıt bulunamadı.</p>
                  )}
                </TableCell>
              </TableRow>
            ) : shouldVirtualize ? (
              <VirtualizedTableBody
                rows={rows}
                rowHeight={rowHeight}
                onRowClick={onRowClick}
              />
            ) : (
              rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                  className={onRowClick ? "cursor-pointer" : undefined}
                  onClick={() => onRowClick?.(row.original)}
                  data-testid={`datatable-row-${row.index}`}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {!loading && data.length > 0 && (
        <DataTablePagination table={table} pageSizeOptions={pageSizeOptions} />
      )}
    </div>
  );
}

// ─── Virtualized table body for large datasets ───
function VirtualizedTableBody({ rows, rowHeight, onRowClick }) {
  const parentRef = useRef(null);

  // eslint-disable-next-line react-hooks/incompatible-library
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowHeight,
    overscan: 10,
  });

  return (
    <tr>
      <td colSpan={999} className="p-0">
        <div
          ref={parentRef}
          className="max-h-[600px] overflow-auto"
          data-testid="datatable-virtual-scroll"
        >
          <div style={{ height: `${virtualizer.getTotalSize()}px`, position: "relative" }}>
            {virtualizer.getVirtualItems().map((virtualRow) => {
              const row = rows[virtualRow.index];
              return (
                <div
                  key={row.id}
                  data-index={virtualRow.index}
                  ref={virtualizer.measureElement}
                  className={cn(
                    "flex items-center border-b",
                    onRowClick && "cursor-pointer hover:bg-muted/50",
                    row.getIsSelected() && "bg-muted"
                  )}
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                  onClick={() => onRowClick?.(row.original)}
                  data-testid={`datatable-row-${row.index}`}
                >
                  {row.getVisibleCells().map((cell) => (
                    <div
                      key={cell.id}
                      className="px-4 py-3 text-sm"
                      style={{
                        width: cell.column.getSize() !== 150 ? cell.column.getSize() : undefined,
                        flex: cell.column.getSize() === 150 ? "1 1 0%" : undefined,
                      }}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </td>
    </tr>
  );
}

export default DataTable;
