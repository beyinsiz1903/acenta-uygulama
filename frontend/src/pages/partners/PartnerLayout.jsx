import React from "react";
import { Outlet } from "react-router-dom";
import PartnerSubNav from "./components/PartnerSubNav";

export default function PartnerLayout() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-base font-semibold">İş Ortakları</h1>
        <p className="text-xs text-muted-foreground">
          Partner davetleri, ilişkiler ve mutabakatları buradan yönetin.
        </p>
      </div>

      <PartnerSubNav />

      <div className="pt-2">
        <Outlet />
      </div>
    </div>
  );
}
