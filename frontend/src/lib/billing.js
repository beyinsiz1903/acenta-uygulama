import { api, apiErrorMessage } from "./api";

export async function createCheckoutSession(body) {
  try {
    const res = await api.post("/billing/create-checkout", body);
    return res.data;
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function getCheckoutStatus(sessionId) {
  try {
    const res = await api.get(`/billing/checkout-status/${sessionId}`);
    return res.data;
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}