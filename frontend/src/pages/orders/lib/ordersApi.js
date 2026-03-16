const API = process.env.REACT_APP_BACKEND_URL;

// ── Order CRUD ──

export async function fetchOrders({ skip = 0, limit = 50, status, channel, agency_id } = {}) {
  const params = new URLSearchParams({ skip, limit });
  if (status) params.set("status", status);
  if (channel) params.set("channel", channel);
  if (agency_id) params.set("agency_id", agency_id);
  const res = await fetch(`${API}/api/orders?${params}`);
  if (!res.ok) throw new Error("Orders fetch failed");
  return res.json();
}

export async function searchOrders({
  skip = 0, limit = 50, status, channel, agency_id, customer_id,
  supplier_code, order_number, date_from, date_to, settlement_status, q,
} = {}) {
  const params = new URLSearchParams({ skip, limit });
  if (status) params.set("status", status);
  if (channel) params.set("channel", channel);
  if (agency_id) params.set("agency_id", agency_id);
  if (customer_id) params.set("customer_id", customer_id);
  if (supplier_code) params.set("supplier_code", supplier_code);
  if (order_number) params.set("order_number", order_number);
  if (date_from) params.set("date_from", date_from);
  if (date_to) params.set("date_to", date_to);
  if (settlement_status) params.set("settlement_status", settlement_status);
  if (q) params.set("q", q);
  const res = await fetch(`${API}/api/orders/search?${params}`);
  if (!res.ok) throw new Error("Search orders failed");
  return res.json();
}

export async function fetchOrderDetail(orderId) {
  const res = await fetch(`${API}/api/orders/${orderId}`);
  if (!res.ok) throw new Error("Order detail fetch failed");
  return res.json();
}

export async function createOrder(data) {
  const res = await fetch(`${API}/api/orders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Create order failed");
  return res.json();
}

export async function updateOrder(orderId, data) {
  const res = await fetch(`${API}/api/orders/${orderId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Update order failed");
  return res.json();
}

// ── Status Transitions ──

async function transitionOrder(orderId, action, body = {}) {
  const res = await fetch(`${API}/api/orders/${orderId}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `${action} failed`);
  }
  return res.json();
}

export const confirmOrder = (id, actor = "admin", reason = "") =>
  transitionOrder(id, "confirm", { actor, reason });

export const requestCancelOrder = (id, actor = "admin", reason = "") =>
  transitionOrder(id, "request-cancel", { actor, reason });

export const cancelOrder = (id, actor = "admin", reason = "") =>
  transitionOrder(id, "cancel", { actor, reason });

export const closeOrder = (id, actor = "admin", reason = "") =>
  transitionOrder(id, "close", { actor, reason });

// ── Items ──

export async function addOrderItem(orderId, itemData) {
  const res = await fetch(`${API}/api/orders/${orderId}/items`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(itemData),
  });
  if (!res.ok) throw new Error("Add item failed");
  return res.json();
}

export async function fetchOrderItems(orderId) {
  const res = await fetch(`${API}/api/orders/${orderId}/items`);
  if (!res.ok) throw new Error("Items fetch failed");
  return res.json();
}

// ── Events / Timeline ──

export async function fetchOrderEvents(orderId, limit = 100) {
  const res = await fetch(`${API}/api/orders/${orderId}/events?limit=${limit}`);
  if (!res.ok) throw new Error("Events fetch failed");
  return res.json();
}

export async function fetchOrderTimeline(orderId, limit = 50) {
  const res = await fetch(`${API}/api/orders/${orderId}/timeline?limit=${limit}`);
  if (!res.ok) throw new Error("Timeline fetch failed");
  return res.json();
}

// ── Financial Summary ──

export async function fetchFinancialSummary(orderId) {
  const res = await fetch(`${API}/api/orders/${orderId}/financial-summary`);
  if (!res.ok) throw new Error("Financial summary fetch failed");
  return res.json();
}

// ── Seed ──

export async function seedDemoOrders() {
  const res = await fetch(`${API}/api/orders/seed`, { method: "POST" });
  if (!res.ok) throw new Error("Seed orders failed");
  return res.json();
}
