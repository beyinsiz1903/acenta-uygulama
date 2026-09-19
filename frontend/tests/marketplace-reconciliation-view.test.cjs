// Render the actual page with isolated query/state doubles; not a browser test.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const { transformSync } = require("@babel/core");

const source = fs.readFileSync(path.join(__dirname, "../src/pages/syroce/MarketplaceReservationsPage.jsx"), "utf8");
const code = transformSync(source, {
  configFile: false, babelrc: false,
  plugins: [[require.resolve("@babel/plugin-transform-react-jsx"), { runtime: "classic" }], require.resolve("@babel/plugin-transform-modules-commonjs")],
}).code;

function render({ record = {}, listFailed = false, openDetail = false } = {}) {
  let stateIndex = 0;
  const queries = [];
  const local = { id: "local-1", external_reference: "REF1", ...record };
  const exports = {};
  const modules = {
    react: { ...React, useState: (initial) => [stateIndex++ === 1 && openDetail ? "local-1" : initial, () => {}] },
    "@tanstack/react-query": {
      useQuery: (config) => {
        queries.push(config);
        return config.queryKey[0] === "marketplace-reservations"
          ? { data: { items: listFailed ? [] : [local] }, isLoading: false, isError: listFailed }
          : { data: openDetail ? { local, pms: {} } : undefined, isLoading: false, isError: false };
      },
      useMutation: () => ({}), useQueryClient: () => ({ invalidateQueries() {} }),
    },
    "../../lib/api": { api: {}, apiErrorMessage: () => "error" },
    "lucide-react": new Proxy({}, { get: () => () => null }),
  };
  vm.runInNewContext(code, { exports, require: (name) => {
    assert.ok(name in modules, `Unexpected dependency: ${name}`);
    return modules[name];
  } });
  return { html: renderToStaticMarkup(React.createElement(exports.default)), queries };
}

test("pending record explains automatic checks and prevents cancellation", () => {
  const { html } = render({ record: { status: "pending", syroce_reservation_id: "pms-1", reconciliation_outcome: "unresolved" }, openDetail: true });
  assert.match(html, /otomatik kontrol edilir/);
  assert.match(html, /yeni PNR ile tekrar göndermeyin/);
  assert.match(html, /reddedildiği anlamına gelmez/);
  assert.doesNotMatch(html, /title="İptal Et"/);
});

test("uncertain confirmed and missing-PMS-ID records cannot cancel", () => {
  for (const record of [
    { status: "confirmed", reconciliation_required: true, syroce_reservation_id: "pms-1" },
    { status: "confirmed" },
    { status: "cancelled", syroce_reservation_id: "pms-1" },
  ]) assert.doesNotMatch(render({ record }).html, /title="İptal Et"/);
});

test("confirmed record with PMS ID retains cancellation", () => {
  const { html } = render({ record: { status: "confirmed", syroce_reservation_id: "pms-1" } });
  assert.match(html, /Onaylı/);
  assert.match(html, /title="İptal Et"/);
});

test("refresh is read-only, visible-page only, detail polling stops on resolution", () => {
  const { queries } = render();
  assert.equal(queries[0].refetchInterval, 30000);
  assert.equal(queries[0].refetchIntervalInBackground, false);
  assert.equal(queries[1].enabled, false);
  assert.equal(queries[1].refetchIntervalInBackground, false);
  for (const status of ["pending", "confirmed", "cancelled"]) {
    assert.equal(queries[1].refetchInterval({ state: { data: { local: { status } } } }), status === "pending" ? 30000 : false);
  }
});

test("list failure is not presented as an empty reservation list", () => {
  const { html } = render({ listFailed: true });
  assert.match(html, /Liste yenilenemedi/);
  assert.doesNotMatch(html, /Henüz rezervasyon yok/);
});

test("failed lookup and invalid timestamps render without claiming success", () => {
  const { html } = render({ openDetail: true, record: {
    status: "pending", reconciliation_outcome: "lookup_failed", reconciliation_checked_at: "bad-date",
  } });
  assert.match(html, /Son sorgu tamamlanamadı/);
  assert.match(html, /Bilinmiyor/);
  assert.match(html, /Henüz yok/);
});
