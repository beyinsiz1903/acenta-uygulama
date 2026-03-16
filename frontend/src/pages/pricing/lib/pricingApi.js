import { api as axiosApi } from "../../../lib/api";

export async function pricingApi(path, opts = {}) {
  try {
    const method = opts.method?.toLowerCase() || "get";
    const body = opts.body ? JSON.parse(opts.body) : undefined;
    const res = await axiosApi.request({
      method,
      url: `/pricing-engine${path}`,
      data: body,
    });
    return res.data;
  } catch (err) {
    console.error(`API error on ${path}:`, err?.response?.status, err?.response?.data || err.message);
    throw err;
  }
}
