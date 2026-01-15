import { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";

const STORAGE_KEY = "theme_v1_default";
const TTL_MS = 5 * 60 * 1000; // 5 dakika

function applyTheme(theme) {
  if (!theme || typeof document === "undefined") return;
  const { colors = {}, typography = {}, brand = {} } = theme;

  const root = document.documentElement;
  const setVar = (key, val) => {
    if (!val) return;
    root.style.setProperty(key, val);
  };

  setVar("--color-primary", colors.primary || "#2563eb");
  setVar("--color-primary-foreground", colors.primary_foreground || "#ffffff");
  setVar("--color-background", colors.background || "#ffffff");
  setVar("--color-foreground", colors.foreground || "#0f172a");
  setVar("--color-muted", colors.muted || "#f1f5f9");
  setVar("--color-muted-foreground", colors.muted_foreground || "#475569");
  setVar("--color-border", colors.border || "#e2e8f0");

  if (typography.font_family) {
    root.style.fontFamily = typography.font_family;
  }

  if (brand.company_name) {
    document.title = brand.company_name;
  }

  if (brand.favicon_url) {
    let link = document.querySelector("link[rel='icon']");
    if (!link) {
      link = document.createElement("link");
      link.rel = "icon";
      document.head.appendChild(link);
    }
    link.href = brand.favicon_url;
  }
}

export function useTheme() {
  const [theme, setTheme] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const cachedRaw = window.localStorage.getItem(STORAGE_KEY);
        if (cachedRaw) {
          try {
            const cached = JSON.parse(cachedRaw);
            if (cached && cached.expires_at && Date.now() < cached.expires_at) {
              if (!cancelled) {
                setTheme(cached.theme);
                applyTheme(cached.theme);
              }
            }
          } catch {
            // ignore cache parse issues
          }
        }

        const res = await api.get("/public/theme");
        if (!cancelled) {
          setTheme(res.data);
          applyTheme(res.data);
        }

        try {
          const payload = {
            theme: res.data,
            expires_at: Date.now() + TTL_MS,
          };
          window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
        } catch {
          // ignore storage errors
        }
      } catch (e) {
        if (!cancelled) {
          setError(apiErrorMessage(e));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    if (typeof window !== "undefined") {
      void load();
    }

    return () => {
      cancelled = true;
    };
  }, []);

  return { theme, loading, error };
}
