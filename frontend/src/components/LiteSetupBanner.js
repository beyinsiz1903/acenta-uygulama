import React from "react";
import { Button } from "@/components/ui/button";

export default function LiteSetupBanner({ title, desc, actionLabel, onAction }) {
  return (
    <div className="mb-4 rounded-2xl border bg-white p-4">
      <div className="text-sm font-semibold text-gray-900">{title}</div>
      <div className="mt-1 text-sm text-gray-600">{desc}</div>
      {actionLabel ? (
        <div className="mt-3">
          <Button size="sm" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
