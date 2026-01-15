import React, { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { api } from "../lib/api";

export default function B2BAuthGuard({ children }) {
  const location = useLocation();
  const [state, setState] = useState("loading"); // loading | ok | nope

  useEffect(() => {
    let isMounted = true;
    api
      .get("/b2b/me")
      .then(() => {
        if (isMounted) setState("ok");
      })
      .catch(() => {
        if (isMounted) setState("nope");
      });
    return () => {
      isMounted = false;
    };
  }, []);

  if (state === "loading") {
    return <div className="p-4 text-sm text-muted-foreground">Yükleniyor...</div>;
  }

  if (state === "nope") {
    const next = encodeURIComponent(location.pathname + location.search + location.hash);
    return <Navigate to={`/b2b/login?reason=session_expired&next=${next}`} replace />;
  }

  return children;
}
