// Lightweight smoke check for marketplace frontend routes/components
/* eslint-disable no-console */

const fs = require("fs");
const path = require("path");

try {
  const base = path.join(__dirname, "../src/pages/marketplace");
  const files = [
    "AdminMarketplaceListingsPage.jsx",
    "B2BMarketplaceCatalogPage.jsx",
  ];

  for (const f of files) {
    const full = path.join(base, f);
    if (!fs.existsSync(full)) {
      throw new Error(`Missing marketplace page file: ${f}`);
    }
  }

  const appJs = fs.readFileSync(path.join(__dirname, "../src/App.js"), "utf8");
  if (!appJs.includes("/app/admin/marketplace/listings")) {
    throw new Error("Route '/app/admin/marketplace/listings' not found in App.js");
  }
  if (!appJs.includes("/app/b2b/marketplace")) {
    throw new Error("Route '/app/b2b/marketplace' not found in App.js");
  }

  console.log("marketplace_smoke_check: OK (files + routes present)");
  process.exit(0);
} catch (err) {
  console.error("marketplace_smoke_check: FAILED", err && err.message ? err.message : err);
  process.exit(1);
}
