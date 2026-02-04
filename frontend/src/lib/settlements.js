import { api, apiErrorMessage } from "./api";

export async function fetchSettlementStatement(params) {
  const {
    month,
    perspective = "seller",
    statuses,
    counterpartyTenantId,
    limit = 50,
    cursor,
  } = params;

  const query = new URLSearchParams();
  if (month) query.set("month", month);
  if (perspective) query.set("perspective", perspective);
  if (Array.isArray(statuses) && statuses.length > 0) {
    query.set("status", statuses.join(","));
  }
  if (counterpartyTenantId) {
    query.set("counterparty_tenant_id", counterpartyTenantId);
  }
  if (limit) query.set("limit", String(limit));
  if (cursor) query.set("cursor", cursor);

  try {
    const res = await api.get(`/settlements/statement?${query.toString()}`);
    return res.data || {};
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}
