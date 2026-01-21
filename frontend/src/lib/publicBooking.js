import { api, apiErrorMessage } from "./api";

export async function searchPublic(params = {}) {
  try {
    const res = await api.get("/public/search", { params });
    return res.data;
  } catch (e) {
    const status = e?.response?.status ?? null;
    const data = e?.response?.data || {};
    const code = data.code || data.error || data.detail || data?.error?.code || null;
    const message = apiErrorMessage(e);
    const normalized = { status, code, message, raw: e };
    throw normalized;
  }
}

export async function searchPublicTours(params = {}) {
  try {
    const res = await api.get("/public/tours/search", { params });
    return res.data;
  } catch (e) {
    const status = e?.response?.status ?? null;
    const data = e?.response?.data || {};
    const code = data.code || data.error || data.detail || data?.error?.code || null;
    const message = apiErrorMessage(e);
    const normalized = { status, code, message, raw: e };
    throw normalized;
  }
}

export async function createPublicQuote(body) {
  try {
    const res = await api.post("/public/quote", body);
    return res.data;
  } catch (e) {
    const status = e?.response?.status ?? null;
    const data = e?.response?.data || {};
    const code = data.code || data.error || data.detail || data?.error?.code || null;
    const message = apiErrorMessage(e);
    throw { status, code, message, raw: e };
  }
}

export async function createPublicCheckout(body) {
  try {
    const { coupon, ...rest } = body || {};
    const params = {};
    if (coupon && typeof coupon === "string" && coupon.trim()) {
      params.coupon = coupon.trim().toUpperCase();
    }
    const res = await api.post("/public/checkout", rest, { params });
    return res.data;
  } catch (e) {
    const status = e?.response?.status ?? null;
    const data = e?.response?.data || {};
    const code = data.code || data.error || data.detail || data?.error?.code || null;
    const message = apiErrorMessage(e);
    throw { status, code, message, raw: e };
  }
}

export async function getPublicBookingSummary({ org, booking_code }) {
  const res = await api.get(`/public/bookings/by-code/${booking_code}`, { params: { org } });
  return res.data;
}

export async function requestMyBookingLink(body) {
  // Backend expects snake_case fields: booking_code, email
  const res = await api.post("/public/my-booking/request-link", body);
  return res.data;
}

export async function createMyBookingToken(body) {
  const res = await api.post("/public/my-booking/create-token", body);
  return res.data;
}

export { apiErrorMessage };
