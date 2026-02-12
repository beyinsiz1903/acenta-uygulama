import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import AiAssistant from "../components/AiAssistant";

export default function B2BLayout() {
  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      <aside className="w-full md:w-56 border-b md:border-b-0 md:border-r bg-muted/40 p-4 space-y-4">
        <div className="font-semibold text-lg">B2B Portal</div>
        <nav className="flex flex-col gap-2 text-sm">
          <NavLink
            to="/b2b/bookings"
            className={({ isActive }) =>
              `px-2 py-1 rounded-md ${isActive ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`
            }
          >
            Rezervasyonlarım
          </NavLink>
          <NavLink
            to="/b2b/account"
            className={({ isActive }) =>
              `px-2 py-1 rounded-md ${isActive ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`
            }
          >
            Cari Hesap
          </NavLink>
        </nav>
      </aside>
      <main className="flex-1 p-4">
        <Outlet />
      </main>
      <AiAssistant />
    </div>
  );
}
