import React from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutGrid,
  CalendarDays,
  Ticket,
  Users,
  Layers,
  FileText,
  Building2,
  Settings,
  BarChart3,
  LogOut,
} from "lucide-react";

import { Button } from "./ui/button";
import ThemeToggle from "./ThemeToggle";
import { cn } from "../lib/utils";
import { clearToken, getUser } from "../lib/api";

const nav = [
  { to: "/app", label: "Dashboard", icon: LayoutGrid, roles: ["admin", "sales", "ops", "accounting", "b2b_agent"] },
  { to: "/app/products", label: "Ürünler", icon: Layers, roles: ["admin", "sales", "ops"] },
  { to: "/app/inventory", label: "Müsaitlik", icon: CalendarDays, roles: ["admin", "sales", "ops"] },
  { to: "/app/reservations", label: "Rezervasyonlar", icon: Ticket, roles: ["admin", "sales", "ops", "accounting", "b2b_agent"] },
  { to: "/app/customers", label: "Müşteriler", icon: Users, roles: ["admin", "sales", "ops"] },
  { to: "/app/crm", label: "CRM", icon: FileText, roles: ["admin", "sales"] },
  { to: "/app/b2b", label: "B2B / Acenteler", icon: Building2, roles: ["admin"] },
  { to: "/app/b2b-book", label: "B2B Rezervasyon", icon: Ticket, roles: ["b2b_agent"] },
  { to: "/app/reports", label: "Raporlar", icon: BarChart3, roles: ["admin", "sales", "accounting"] },
  { to: "/app/settings", label: "Ayarlar", icon: Settings, roles: ["admin"] },
];

function userHasRole(user, allowed) {
  const roles = user?.roles || [];
  return allowed.some((r) => roles.includes(r));
}

export default function AppShell() {
  const user = getUser();
  const location = useLocation();

  const visibleNav = nav.filter((n) => userHasRole(user, n.roles));

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="sticky top-0 z-40 border-b bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-slate-900 text-white grid place-items-center font-semibold">
              A
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-900">Acenta Master</div>
              <div className="text-xs text-slate-500">Operasyon & Rezervasyon Yönetimi</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />
            <div className="hidden sm:block text-right">
              <div className="text-sm font-medium text-foreground">{user?.name || user?.email}</div>
              <div className="text-xs text-muted-foreground">{(user?.roles || []).join(", ")}</div>
            </div>
            <Button
              variant="outline"
              size="sm"
              data-testid="logout-btn"
              onClick={() => {
                clearToken();
                window.location.href = "/login";
              }}
              className="gap-2"
            >
              <LogOut className="h-4 w-4" />
              Çıkış
            </Button>
          </div>
        </div>
      </div>

      <div className="mx-auto grid max-w-7xl grid-cols-12 gap-4 px-4 py-6">
        <aside className="col-span-12 md:col-span-3 lg:col-span-2">
          <nav className="rounded-2xl border bg-white p-2 shadow-sm">
            {visibleNav.map((item) => {
              const Icon = item.icon;
              const active = location.pathname === item.to;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/app"}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition",
                      isActive
                        ? "bg-slate-900 text-white"
                        : "text-slate-700 hover:bg-slate-100"
                    )
                  }
                  data-testid={`nav-${item.label}`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              );
            })}
          </nav>

          <div className="mt-4 rounded-2xl border bg-white p-4 shadow-sm">
            <div className="text-xs font-semibold text-slate-900">Hızlı İpuçları</div>
            <div className="mt-2 text-xs text-slate-600">
              Müsaitlik ekranında kapasite ve fiyatı güncelleyip rezervasyon akışını
              hızlıca test edebilirsin.
            </div>
          </div>
        </aside>

        <main className="col-span-12 md:col-span-9 lg:col-span-10">
          <Outlet />
        </main>
      </div>

      <footer className="border-t bg-white">
        <div className="mx-auto max-w-7xl px-4 py-4 text-xs text-slate-500">
          © {new Date().getFullYear()} Acenta Master — v1
        </div>
      </footer>
    </div>
  );
}
