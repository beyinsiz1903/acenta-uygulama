// frontend/src/lib/inbox.js
import { api, apiErrorMessage } from "./api";

export async function listInboxThreads(params = {}) {
  try {
    const res = await api.get("/inbox/threads", {
      params: {
        status: params.status || undefined,
        channel: params.channel || undefined,
        customer_id: params.customerId || undefined,
        q: params.q || undefined,
        page: params.page || 1,
        page_size: params.pageSize || 50,
      },
    });
    return res.data;
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function createInboxThread(body) {
  try {
    const res = await api.post("/inbox/threads", body);
    return res.data;
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function listInboxMessages(threadId, params = {}) {
  try {
    const res = await api.get(`/inbox/threads/${threadId}/messages`, {
      params: {
        page: params.page || 1,
        page_size: params.pageSize || 50,
      },
    });
    return res.data;
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function createInboxMessage(threadId, body) {
  try {
    const res = await api.post(`/inbox/threads/${threadId}/messages`, body);
    return res.data;
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function updateInboxThreadStatus(threadId, status) {
  try {
    const res = await api.patch(`/inbox/threads/${threadId}/status`, { status });
    return res.data;
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}
