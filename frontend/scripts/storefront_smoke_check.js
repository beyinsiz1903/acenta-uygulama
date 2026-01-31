// Lightweight non-Jest smoke check for storefront routes/components
// Goal: ensure components exist and basic shape is intact without spinning up test runner.

/* eslint-disable no-console */

try {
  // Dynamic requires to avoid bundler issues
  // eslint-disable-next-line global-require, import/no-dynamic-require
  const StorefrontSearchPage = require("../src/pages/storefront/StorefrontSearchPage.jsx");
  const StorefrontOfferPage = require("../src/pages/storefront/StorefrontOfferPage.jsx");
  const StorefrontCheckoutPage = require("../src/pages/storefront/StorefrontCheckoutPage.jsx");

  if (!StorefrontSearchPage || (!StorefrontSearchPage.default && typeof StorefrontSearchPage !== "function")) {
    throw new Error("StorefrontSearchPage component missing default export");
  }
  if (!StorefrontOfferPage || (!StorefrontOfferPage.default && typeof StorefrontOfferPage !== "function")) {
    throw new Error("StorefrontOfferPage component missing default export");
  }
  if (!StorefrontCheckoutPage || (!StorefrontCheckoutPage.default && typeof StorefrontCheckoutPage !== "function")) {
    throw new Error("StorefrontCheckoutPage component missing default export");
  }

  console.log("storefront_smoke_check: OK");
  process.exit(0);
} catch (err) {
  console.error("storefront_smoke_check: FAILED", err && err.message ? err.message : err);
  process.exit(1);
}
