import * as React from "react";
import { cn } from "@/lib/utils";

export interface ColumnDef<T> {
  header: string;
  accessorKey: keyof T | string;
  cell?: (item: T) => React.ReactNode;
  className?: string;
}

export interface DataGridProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  keyExtractor: (item: T, index: number) => string | number;
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
  className?: string;
}

export function DataGrid<T>({
  data,
  columns,
  keyExtractor,
  onRowClick,
  emptyMessage = "No investigation records found.",
  className,
}: DataGridProps<T>) {
  return (
    <div className={cn("overflow-hidden rounded-xl border border-white/10 bg-black/20 backdrop-blur-sm shadow-md", className)}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-white/10 bg-white/[0.03] text-xs font-semibold uppercase tracking-wider text-slate-300">
            <tr>
              {columns.map((col, idx) => (
                <th key={idx} className={cn("h-11 px-4 whitespace-nowrap", col.className)}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="p-8 text-center text-slate-400 text-sm italic">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((item, index) => (
                <tr
                  key={keyExtractor(item, index)}
                  onClick={onRowClick ? () => onRowClick(item) : undefined}
                  className={cn(
                    "transition-colors hover:bg-white/[0.04]",
                    onRowClick && "cursor-pointer active:bg-white/[0.08]"
                  )}
                >
                  {columns.map((col, cIdx) => (
                    <td key={cIdx} className={cn("p-4 align-middle text-slate-200 leading-relaxed", col.className)}>
                      {col.cell ? col.cell(item) : (item as any)[col.accessorKey]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
