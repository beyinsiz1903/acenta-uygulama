import React from "react";
import { Outlet } from "react-router-dom";

export default function HotelSettlementsLayout() {
  return (
    <div className="space-y-6">
      <Outlet />
    </div>
  );
}
