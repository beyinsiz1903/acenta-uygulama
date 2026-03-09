import React from "react";
import { BarChart3, CalendarRange, CircleDollarSign, LayoutDashboard, Users2 } from "lucide-react";

const KPI_CARDS = [
  {
    label: "Aktif rezervasyon",
    value: "128",
    delta: "+18%",
    icon: CalendarRange,
    tone: "bg-blue-50 text-blue-700 border-blue-100",
  },
  {
    label: "Tahsilat oranı",
    value: "%94",
    delta: "+9%",
    icon: CircleDollarSign,
    tone: "bg-sky-50 text-sky-700 border-sky-100",
  },
  {
    label: "Aktif müşteri",
    value: "672",
    delta: "+24",
    icon: Users2,
    tone: "bg-slate-50 text-slate-700 border-slate-200",
  },
];

const BOOKING_ROWS = [
  { id: "SR-1048", guest: "Merve Arslan", status: "Onaylandı", amount: "₺28.400" },
  { id: "SR-1049", guest: "Atlas Travel", status: "Tahsilat Bekliyor", amount: "₺16.900" },
  { id: "SR-1051", guest: "Yamaç Tur", status: "Operasyonda", amount: "₺31.600" },
];

const CUSTOMER_ROWS = [
  { name: "Royal MICE", detail: "Kurumsal · Son rezervasyon 2 saat önce" },
  { name: "Lina Travel", detail: "VIP misafir · Teklif bekliyor" },
  { name: "Skyline Tour", detail: "Tahsilat tamamlandı" },
];

const CHART_BARS = [58, 78, 66, 88, 74, 96, 82];

export const LandingDashboardMockup = ({ compact = false, testIdPrefix = "landing-dashboard" }) => {
  const shellClassName = compact
    ? "w-full rounded-[24px] border border-white/70 bg-white/90 p-4 shadow-[0_24px_80px_rgba(37,99,235,0.12)] backdrop-blur-xl"
    : "w-full rounded-[32px] border border-white/70 bg-white/85 p-5 shadow-[0_34px_120px_rgba(37,99,235,0.16)] backdrop-blur-2xl";

  return (
    <div className={shellClassName} data-testid={`${testIdPrefix}-shell`}>
      <div className="flex flex-wrap items-start justify-between gap-3 rounded-[24px] border border-slate-100 bg-white px-4 py-3 shadow-[0_10px_30px_rgba(15,23,42,0.05)] md:flex-nowrap md:items-center" data-testid={`${testIdPrefix}-topbar`}>
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[linear-gradient(135deg,#2563EB,#0EA5E9)] text-white" data-testid={`${testIdPrefix}-brand-badge`}>
            <LayoutDashboard className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400 sm:tracking-[0.24em]" data-testid={`${testIdPrefix}-eyebrow`}>
              Syroce Dashboard
            </p>
            <p className="text-sm font-semibold leading-tight text-slate-900" data-testid={`${testIdPrefix}-title`}>
              Bugünün operasyon özeti
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2" data-testid={`${testIdPrefix}-status-cluster`}>
          <div className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700" data-testid={`${testIdPrefix}-status-online`}>
            Sistem aktif
          </div>
          <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600" data-testid={`${testIdPrefix}-status-response`}>
            7/24 bulut erişim
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3" data-testid={`${testIdPrefix}-kpis`}>
        {KPI_CARDS.map((card, index) => (
          <article key={card.label} className="rounded-[22px] border border-slate-100 bg-white px-4 py-4 shadow-[0_12px_34px_rgba(15,23,42,0.05)]" data-testid={`${testIdPrefix}-kpi-${index + 1}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-slate-500" data-testid={`${testIdPrefix}-kpi-label-${index + 1}`}>
                  {card.label}
                </p>
                <p className="mt-2 text-2xl font-extrabold tracking-tight text-slate-900" data-testid={`${testIdPrefix}-kpi-value-${index + 1}`}>
                  {card.value}
                </p>
              </div>
              <div className={`rounded-2xl border px-3 py-3 ${card.tone}`} data-testid={`${testIdPrefix}-kpi-icon-${index + 1}`}>
                <card.icon className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-3 text-xs font-semibold text-emerald-600" data-testid={`${testIdPrefix}-kpi-delta-${index + 1}`}>
              {card.delta} son 30 gün
            </p>
          </article>
        ))}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]" data-testid={`${testIdPrefix}-content-grid`}>
        <section className="rounded-[26px] border border-slate-100 bg-white px-4 py-4 shadow-[0_12px_34px_rgba(15,23,42,0.05)]" data-testid={`${testIdPrefix}-reservation-panel`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400" data-testid={`${testIdPrefix}-reservation-eyebrow`}>
                Rezervasyon paneli
              </p>
              <h3 className="mt-2 text-base font-semibold text-slate-900" data-testid={`${testIdPrefix}-reservation-title`}>
                Operasyon ekipleri aynı ekranda
              </h3>
            </div>
            <div className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700" data-testid={`${testIdPrefix}-reservation-filter`}>
              Bugün
            </div>
          </div>

          <div className="mt-4 space-y-3" data-testid={`${testIdPrefix}-reservation-list`}>
            {BOOKING_ROWS.map((row, index) => (
              <div key={row.id} className="grid gap-3 rounded-[20px] border border-slate-100 bg-slate-50/80 px-4 py-3 md:grid-cols-[0.9fr_1.2fr_0.9fr_0.7fr] md:items-center" data-testid={`${testIdPrefix}-reservation-row-${index + 1}`}>
                <div>
                  <p className="text-xs font-medium text-slate-500" data-testid={`${testIdPrefix}-reservation-id-label-${index + 1}`}>
                    Referans
                  </p>
                  <p className="text-sm font-semibold text-slate-900" data-testid={`${testIdPrefix}-reservation-id-${index + 1}`}>
                    {row.id}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-500" data-testid={`${testIdPrefix}-reservation-guest-label-${index + 1}`}>
                    Misafir / Acente
                  </p>
                  <p className="text-sm font-semibold text-slate-900" data-testid={`${testIdPrefix}-reservation-guest-${index + 1}`}>
                    {row.guest}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-500" data-testid={`${testIdPrefix}-reservation-status-label-${index + 1}`}>
                    Durum
                  </p>
                  <p className="inline-flex rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700 ring-1 ring-slate-200" data-testid={`${testIdPrefix}-reservation-status-${index + 1}`}>
                    {row.status}
                  </p>
                </div>
                <div className="md:text-right">
                  <p className="text-xs font-medium text-slate-500" data-testid={`${testIdPrefix}-reservation-amount-label-${index + 1}`}>
                    Tutar
                  </p>
                  <p className="text-sm font-semibold text-slate-900" data-testid={`${testIdPrefix}-reservation-amount-${index + 1}`}>
                    {row.amount}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <div className="grid gap-4" data-testid={`${testIdPrefix}-side-panels`}>
          <section className="rounded-[26px] border border-slate-100 bg-white px-4 py-4 shadow-[0_12px_34px_rgba(15,23,42,0.05)]" data-testid={`${testIdPrefix}-crm-panel`}>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400" data-testid={`${testIdPrefix}-crm-eyebrow`}>
              CRM müşteri görünümü
            </p>
            <div className="mt-4 space-y-3" data-testid={`${testIdPrefix}-crm-list`}>
              {CUSTOMER_ROWS.map((row, index) => (
                <div key={row.name} className="rounded-[18px] bg-slate-50 px-4 py-3" data-testid={`${testIdPrefix}-crm-row-${index + 1}`}>
                  <p className="text-sm font-semibold text-slate-900" data-testid={`${testIdPrefix}-crm-name-${index + 1}`}>
                    {row.name}
                  </p>
                  <p className="mt-1 text-xs text-slate-500" data-testid={`${testIdPrefix}-crm-detail-${index + 1}`}>
                    {row.detail}
                  </p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-[26px] border border-slate-100 bg-slate-950 px-4 py-4 text-white shadow-[0_20px_40px_rgba(15,23,42,0.28)]" data-testid={`${testIdPrefix}-finance-panel`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-200/80" data-testid={`${testIdPrefix}-finance-eyebrow`}>
                  Finans görünümü
                </p>
                <p className="mt-2 text-sm font-semibold" data-testid={`${testIdPrefix}-finance-title`}>
                  Tahsilat & komisyon takibi
                </p>
              </div>
              <BarChart3 className="h-5 w-5 text-sky-300" />
            </div>

            <div className="mt-4 grid grid-cols-7 items-end gap-2" data-testid={`${testIdPrefix}-finance-chart`}>
              {CHART_BARS.map((bar, index) => (
                <div key={`${bar}-${index}`} className="flex flex-col items-center gap-2" data-testid={`${testIdPrefix}-finance-bar-${index + 1}`}>
                  <div className="flex h-24 w-full items-end rounded-full bg-white/10">
                    <div className="w-full rounded-full bg-[linear-gradient(180deg,#38BDF8,#2563EB)]" style={{ height: `${bar}%` }} data-testid={`${testIdPrefix}-finance-bar-fill-${index + 1}`} />
                  </div>
                  <span className="text-[10px] uppercase tracking-[0.16em] text-white/50" data-testid={`${testIdPrefix}-finance-bar-label-${index + 1}`}>
                    {`0${index + 1}`.slice(-2)}
                  </span>
                </div>
              ))}
            </div>

            <div className="mt-4 rounded-[18px] bg-white/8 px-4 py-3" data-testid={`${testIdPrefix}-finance-summary`}>
              <p className="text-xs text-white/60" data-testid={`${testIdPrefix}-finance-summary-label`}>
                Bekleyen tahsilat
              </p>
              <p className="mt-1 text-lg font-semibold" data-testid={`${testIdPrefix}-finance-summary-value`}>
                ₺182.400
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};