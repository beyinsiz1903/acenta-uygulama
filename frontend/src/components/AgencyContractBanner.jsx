import React from "react";
import { AlertTriangle, CalendarRange, Users } from "lucide-react";

import { formatContractWindow, formatSeatUsage, getContractStatusMeta } from "../lib/agencyContract";

export default function AgencyContractBanner({ contract }) {
  if (!contract || contract.contract_status !== "expiring_soon") {
    return null;
  }

  const statusMeta = getContractStatusMeta(contract.contract_status);

  return (
    <div
      className="rounded-2xl border border-amber-200 bg-[linear-gradient(135deg,rgba(255,247,237,0.98),rgba(255,251,235,0.98))] px-4 py-4 shadow-sm"
      data-testid="agency-contract-warning-banner"
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-white/80 px-3 py-1 text-xs font-semibold text-amber-700" data-testid="agency-contract-warning-status">
            <AlertTriangle className="h-3.5 w-3.5" />
            {statusMeta.label}
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900" data-testid="agency-contract-warning-title">
              Sözleşme yenileme hatırlatması
            </p>
            <p className="mt-1 text-sm text-slate-700" data-testid="agency-contract-warning-message">
              {contract.warning_message}
            </p>
          </div>
        </div>

        <div className="grid gap-2 text-xs text-slate-700 sm:min-w-[260px]">
          <div className="flex items-center gap-2 rounded-xl bg-white/80 px-3 py-2" data-testid="agency-contract-warning-period">
            <CalendarRange className="h-3.5 w-3.5 text-slate-500" />
            <span>{formatContractWindow(contract)}</span>
          </div>
          <div className="flex items-center gap-2 rounded-xl bg-white/80 px-3 py-2" data-testid="agency-contract-warning-seats">
            <Users className="h-3.5 w-3.5 text-slate-500" />
            <span>{formatSeatUsage(contract)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}