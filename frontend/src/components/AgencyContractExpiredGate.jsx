import React from "react";
import { CalendarRange, CreditCard, LockKeyhole, ShieldAlert, Users } from "lucide-react";

import { formatContractWindow, formatSeatUsage } from "../lib/agencyContract";

export default function AgencyContractExpiredGate({ contract }) {
  if (!contract || contract.contract_status !== "expired") {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-[120] bg-[radial-gradient(circle_at_top,rgba(190,24,93,0.12),transparent_28%),linear-gradient(180deg,rgba(255,248,248,0.98)_0%,rgba(255,243,244,0.98)_44%,rgba(251,247,247,0.99)_100%)] backdrop-blur-sm"
      data-testid="agency-contract-expired-gate"
    >
      <div className="flex min-h-screen items-center justify-center px-4 py-8">
        <div className="w-full max-w-4xl overflow-hidden rounded-[2rem] border border-rose-200 bg-white/95 shadow-[0_40px_140px_rgba(136,19,55,0.18)]" data-testid="agency-contract-expired-card">
          <div className="grid gap-8 p-8 lg:grid-cols-[0.95fr_1.05fr] lg:p-12">
            <section className="space-y-5" data-testid="agency-contract-expired-copy-section">
              <div className="inline-flex items-center gap-2 rounded-full border border-rose-200 bg-rose-50 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-rose-700" data-testid="agency-contract-expired-badge">
                <LockKeyhole className="h-4 w-4" />
                Erişim Kısıtlandı
              </div>

              <div className="space-y-3">
                <h1 className="text-4xl font-extrabold tracking-[-0.04em] text-slate-900 sm:text-5xl" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="agency-contract-expired-title">
                  Sözleşme süresi sona erdi
                </h1>
                <p className="max-w-xl text-base leading-7 text-slate-600 md:text-lg" data-testid="agency-contract-expired-message">
                  {contract.lock_message}
                </p>
              </div>

              <div className="grid gap-3" data-testid="agency-contract-expired-guidance">
                {[
                  "Ödeme yenilendiğinde erişim tekrar açılır.",
                  "Verileriniz korunur; sadece kullanım kısıtlanır.",
                  "Yenileme için sistem yöneticinizle veya hesabı yöneten kişiyle iletişime geçin.",
                ].map((item, index) => (
                  <div key={item} className="flex items-center gap-3 rounded-2xl bg-rose-50/70 px-4 py-4" data-testid={`agency-contract-expired-guidance-${index + 1}`}>
                    <ShieldAlert className="h-4 w-4 text-rose-600" />
                    <span className="text-sm font-medium text-slate-800">{item}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="space-y-4" data-testid="agency-contract-expired-details-section">
              <div className="rounded-[1.75rem] border border-rose-100 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(255,244,246,0.98))] p-6 shadow-[0_20px_60px_rgba(136,19,55,0.08)]">
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-500" data-testid="agency-contract-expired-eyebrow">
                  Sözleşme Detayı
                </p>

                <div className="mt-5 grid gap-3 text-sm text-slate-700">
                  <div className="flex items-center gap-3 rounded-2xl bg-white/80 px-4 py-3" data-testid="agency-contract-expired-period">
                    <CalendarRange className="h-4 w-4 text-slate-500" />
                    <span>{formatContractWindow(contract)}</span>
                  </div>
                  <div className="flex items-center gap-3 rounded-2xl bg-white/80 px-4 py-3" data-testid="agency-contract-expired-payment-status">
                    <CreditCard className="h-4 w-4 text-slate-500" />
                    <span>{contract.payment_status_label || "Tanımsız"}</span>
                  </div>
                  <div className="flex items-center gap-3 rounded-2xl bg-white/80 px-4 py-3" data-testid="agency-contract-expired-seat-status">
                    <Users className="h-4 w-4 text-slate-500" />
                    <span>{formatSeatUsage(contract)}</span>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}