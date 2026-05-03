import { lazy } from "react";
import { Route } from "react-router-dom";

// ─── Lazy imports: Public pages ───
const PublicHomePage = lazy(() => import("../pages/PublicHomePage"));
const StorefrontSearchPage = lazy(() => import("../pages/storefront/StorefrontSearchPage"));
const StorefrontOfferPage = lazy(() => import("../pages/storefront/StorefrontOfferPage"));
const StorefrontCheckoutPage = lazy(() => import("../pages/storefront/StorefrontCheckoutPage"));
const PublicMyBookingRequestPage = lazy(() => import("../pages/PublicMyBookingRequestPage"));
const PublicMyBookingDetailPage = lazy(() => import("../pages/PublicMyBookingDetailPage"));
const PublicClickToPayPage = lazy(() => import("../pages/public/PublicClickToPayPage"));
const BookSearchPage = lazy(() => import("../pages/public/BookSearchPage"));
const BookProductPage = lazy(() => import("../pages/public/BookProductPage"));
const BookCheckoutPage = lazy(() => import("../pages/public/BookCheckoutPage"));
const BookCompletePage = lazy(() => import("../pages/public/BookCompletePage"));
const BookTourProductPage = lazy(() => import("../pages/public/BookTourProductPage"));
const BookTourCheckoutPage = lazy(() => import("../pages/public/BookTourCheckoutPage"));
const PublicCMSPage = lazy(() => import("../pages/public/PublicCMSPage"));
const PublicCampaignPage = lazy(() => import("../pages/public/PublicCampaignPage"));
const PublicPartnerApplyPage = lazy(() => import("../pages/public/PublicPartnerApplyPage"));
const SignupPage = lazy(() => import("../pages/public/SignupPage"));
const PricingPage = lazy(() => import("../pages/public/PricingPage"));
const DemoPage = lazy(() => import("../pages/public/DemoPage"));
const BillingSuccessPage = lazy(() => import("../pages/public/BillingSuccessPage"));
const WebBookingPage = lazy(() => import("../pages/WebBookingPage"));
// Test/QA-only pages — gated to non-production builds via DEV/import.meta.env.
// In production these import shells exist but the routes below are not mounted,
// so the lazy chunks are never fetched.
const IS_DEV =
  (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.DEV) ||
  (typeof process !== "undefined" && process.env && process.env.NODE_ENV !== "production");
const AgencyBookingTestPage = lazy(() => import("../pages/AgencyBookingTestPage"));
const SimpleBookingTest = lazy(() => import("../pages/SimpleBookingTest"));
const PrivacyPolicyPage = lazy(() => import("../pages/PrivacyPolicyPage"));
const TermsOfServicePage = lazy(() => import("../pages/TermsOfServicePage"));
const ErrorContextPage = lazy(() => import("../pages/ErrorContextPage"));
const ResetPasswordPage = lazy(() => import("../pages/ResetPasswordPage"));

export const publicRoutes = (
  <>
    <Route path="/" element={<PublicHomePage />} />
    <Route path="/s/:tenantKey" element={<StorefrontSearchPage />} />
    <Route path="/s/:tenantKey/search" element={<StorefrontSearchPage />} />
    <Route path="/s/:tenantKey/offers/:offerId" element={<StorefrontOfferPage />} />
    <Route path="/s/:tenantKey/checkout" element={<StorefrontCheckoutPage />} />
    <Route path="/privacy" element={<PrivacyPolicyPage />} />
    <Route path="/terms" element={<TermsOfServicePage />} />
    {IS_DEV && <Route path="/test/booking" element={<AgencyBookingTestPage />} />}
    {IS_DEV && <Route path="/test/simple" element={<SimpleBookingTest />} />}
    <Route path="/booking" element={<WebBookingPage />} />
    <Route path="/pay/:token" element={<PublicClickToPayPage />} />
    <Route path="/book" element={<BookSearchPage />} />
    <Route path="/book/:productId" element={<BookProductPage />} />
    <Route path="/book/:productId/checkout" element={<BookCheckoutPage />} />
    <Route path="/book/complete" element={<BookCompletePage />} />
    <Route path="/book/tour/:tourId" element={<BookTourProductPage />} />
    <Route path="/book/tour/:tourId/checkout" element={<BookTourCheckoutPage />} />
    <Route path="/p/:slug" element={<PublicCMSPage />} />
    <Route path="/campaigns/:slug" element={<PublicCampaignPage />} />
    <Route path="/partners/apply" element={<PublicPartnerApplyPage />} />
    <Route path="/signup" element={<SignupPage />} />
    <Route path="/pricing" element={<PricingPage />} />
    <Route path="/demo" element={<DemoPage />} />
    <Route path="/billing/success" element={<BillingSuccessPage />} />
    <Route path="/payment-success" element={<BillingSuccessPage />} />
    <Route path="/my-booking" element={<PublicMyBookingRequestPage />} />
    <Route path="/my-booking/:token" element={<PublicMyBookingDetailPage />} />
    <Route path="/app/reset-password" element={<ResetPasswordPage />} />
    <Route path="/error-context" element={<ErrorContextPage />} />
  </>
);
