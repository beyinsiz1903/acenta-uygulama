import { api, apiErrorMessage } from "./api";

export async function createClickToPayLink(bookingId) {
  const res = await api.post("/ops/payments/click-to-pay/", { booking_id: bookingId });
  return res.data;
}

export { apiErrorMessage };
