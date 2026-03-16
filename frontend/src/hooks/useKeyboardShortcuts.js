import { useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";

const IGNORED_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT"]);

function isEditableTarget(e) {
  if (IGNORED_TAGS.has(e.target.tagName)) return true;
  if (e.target.isContentEditable) return true;
  return false;
}

/**
 * Enterprise keyboard shortcuts system.
 *
 * Shortcuts:
 *   Cmd/Ctrl+K  → open command palette
 *   /           → open command palette (when not in input)
 *   G then D    → go to dashboard
 *   G then R    → go to reservations
 *   G then C    → go to customers
 *   G then F    → go to finance
 *   G then S    → go to settings
 */
export function useKeyboardShortcuts({ onOpenPalette }) {
  const navigate = useNavigate();
  const pendingG = useRef(false);
  const gTimer = useRef(null);

  const clearG = useCallback(() => {
    pendingG.current = false;
    if (gTimer.current) {
      clearTimeout(gTimer.current);
      gTimer.current = null;
    }
  }, []);

  useEffect(() => {
    function handler(e) {
      // Cmd/Ctrl+K → command palette
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        onOpenPalette?.();
        clearG();
        return;
      }

      // Don't handle single-key shortcuts when typing in inputs
      if (isEditableTarget(e)) return;

      // "/" → open command palette
      if (e.key === "/" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault();
        onOpenPalette?.();
        clearG();
        return;
      }

      // "G" prefix shortcuts — press G then another key within 800ms
      if (e.key === "g" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        if (!pendingG.current) {
          pendingG.current = true;
          gTimer.current = setTimeout(clearG, 800);
          return;
        }
      }

      if (pendingG.current) {
        clearG();
        const key = e.key.toLowerCase();
        const goMap = {
          d: "/app",
          r: "/app/reservations",
          c: "/app/crm/customers",
          f: "/app/admin/finance/settlements",
          s: "/app/settings",
        };
        if (goMap[key]) {
          e.preventDefault();
          navigate(goMap[key]);
          return;
        }
      }
    }

    window.addEventListener("keydown", handler);
    return () => {
      window.removeEventListener("keydown", handler);
      clearG();
    };
  }, [onOpenPalette, navigate, clearG]);
}
