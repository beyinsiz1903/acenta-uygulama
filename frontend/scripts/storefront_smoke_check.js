// Lightweight non-Jest smoke check for storefront routes/components
// Goal: ensure components exist and basic shape is intact without spinning up test runner.

/* eslint-disable no-console */

try {
  // Dynamic requires to avoid bundler issues
  // eslint-disable-next-line global-require, import/no-dynamic-require
  // CRA + JSX cannot be required directly from Node without a transformer.
  // Instead of importing, we just ensure the files are present on disk.
  const fs = require("fs");
  const path = require("path");

  const base = path.join(__dirname, "../src/pages/storefront");
  const files = [
    "StorefrontSearchPage.jsx",
    "StorefrontOfferPage.jsx",
    "StorefrontCheckoutPage.jsx",
  ];

  for (const f of files) {
    const full = path.join(base, f);
    if (!fs.existsSync(full)) {
      throw new Error(`Missing storefront page file: ${f}`);
    }
  }

  // Basic route presence check in App.js
  const appJs = fs.readFileSync(path.join(__dirname, "../src/App.js"), "utf8");
  if (!appJs.includes("/s/:tenantKey")) {
    throw new Error("Route '/s/:tenantKey' not found in App.js");
  }
  if (!appJs.includes("/s/:tenantKey/search")) {
    throw new Error("Route '/s/:tenantKey/search' not found in App.js");
  }

  console.log("storefront_smoke_check: OK (files + routes present)");
  process.exit(0);
} catch (err) {
  console.error("storefront_smoke_check: FAILED", err && err.message ? err.message : err);
  process.exit(1);
}
