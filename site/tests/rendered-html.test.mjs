import assert from "node:assert/strict";
import test from "node:test";

async function render(path = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request(`http://localhost${path}`, { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the Best Gift Search showcase", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<title>Best Gift Search/);
  assert.match(html, /MULTI-AGENT GIFT CONCIERGE/);
  assert.match(html, /Find the gift that feels/);
  assert.match(html, /Travel Coffee Ritual Kit/);
  assert.match(html, /AUTOMATED QUALITY RUBRIC/);
  assert.match(html, /EXPLAINABLE BY DESIGN/);
  assert.match(html, /github\.com\/Irenezhangtt\/BestGiftSearch-AI-Agent/);
  assert.doesNotMatch(html, /Your site is taking shape|Building your site/);
});

test("renders semantic result and agent-flow sections", async () => {
  const html = await (await render()).text();
  assert.equal((html.match(/<article>/g) ?? []).length, 4);
  assert.match(html, /Understand/);
  assert.match(html, /Explore/);
  assert.match(html, /Compare/);
  assert.match(html, /Reflect/);
  assert.match(html, /Interactive showcase/);
  assert.match(html, /repository includes the live FastAPI \+ WebSocket application/);
});
