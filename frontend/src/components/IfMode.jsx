import React from "react";
import { useProductMode } from "../contexts/ProductModeContext";

/**
 * Conditionally render children based on product mode.
 *
 * Usage:
 *   <IfMode atLeast="pro">...</IfMode>       // pro or enterprise
 *   <IfMode exact="lite">...</IfMode>         // only lite
 *   <IfMode not="lite">...</IfMode>           // not lite (pro or enterprise)
 *
 * Props:
 *   atLeast  - minimum mode required (inclusive)
 *   exact    - exact mode match
 *   not      - exclude this mode
 *   fallback - optional element to render when condition is false
 */
export default function IfMode({ atLeast, exact, not: notMode, fallback = null, children }) {
  const { isAtLeast, isMode, mode } = useProductMode();

  let show = true;

  if (atLeast) {
    show = isAtLeast(atLeast);
  }

  if (exact) {
    show = isMode(exact);
  }

  if (notMode) {
    show = mode !== notMode;
  }

  return show ? <>{children}</> : <>{fallback}</>;
}
