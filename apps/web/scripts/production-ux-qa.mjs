#!/usr/bin/env node

import { chromium, expect } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const DEFAULT_BASE_URL = "https://fpw-web-production.up.railway.app";
const NAV_ITEMS = [
  { href: "/", label: "Project" },
  { href: "/datasets", label: "Dataset" },
  { href: "/report", label: "Report" },
  { href: "/traces", label: "Trace" },
  { href: "/evals", label: "Evaluations" },
];
const ROUTES = NAV_ITEMS.map((item) => item.href);
const CHAT_EMPTY_STATE = "Ask about project status, the selected Perturb-PBMC dataset, or a trace-backed result.";
const CHAT_SUBMIT_ATTEMPTS = 3;
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "tablet", width: 834, height: 1112 },
  { name: "mobile", width: 390, height: 844 },
  { name: "narrow-mobile", width: 320, height: 740 },
];
const BANNED_TEXT = [
  /\bundefined\b/i,
  /\bNaN\b/,
  /TypeError/i,
  /ReferenceError/i,
  /Unhandled Runtime Error/i,
  /mock\/openrouter-kimi-structural/i,
  /TODO/i,
  /lorem ipsum/i,
];

const baseUrl = normalizeBaseUrl(process.env.FPW_UX_QA_BASE_URL ?? DEFAULT_BASE_URL);
const artifactRoot = path.resolve(process.env.FPW_UX_QA_ARTIFACT_DIR ?? ".fpw_ux_qa");
const runId = new Date().toISOString().replaceAll(":", "-").replaceAll(".", "-");
const artifactDir = path.join(artifactRoot, runId);
const headless = process.env.FPW_UX_QA_HEADED === "1" ? false : true;
const slowMo = Number(process.env.FPW_UX_QA_SLOWMO_MS ?? 0);

await mkdir(artifactDir, { recursive: true });

const browser = await chromium.launch({ headless, slowMo });
const failures = [];
const screenshots = [];
const consoleMessages = [];
const pageErrors = [];

try {
  await runStep("direct route loads", checkDirectRouteLoads);
  await runStep("desktop navigation", () => checkNavigation("desktop", { width: 1440, height: 1000 }));
  await runStep("mobile navigation", () => checkNavigation("mobile", { width: 390, height: 844 }));
  await runStep("chat success states", checkChatSuccess);
  await runStep("chat failure state", checkChatFailure);
  await runStep("trace detail expand/collapse", checkTraceDetails);
  await runStep("responsive surfaces", checkResponsiveSurfaces);
} finally {
  await browser.close();
}

const summary = {
  baseUrl,
  artifactDir,
  routes: ROUTES,
  viewports: VIEWPORTS.map(({ name, width, height }) => ({ name, width, height })),
  screenshots,
  consoleMessages,
  pageErrors,
  failures,
};

await writeFile(path.join(artifactDir, "summary.json"), `${JSON.stringify(summary, null, 2)}\n`);

if (failures.length > 0) {
  console.error(`Production UX QA failed with ${failures.length} failure(s).`);
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  console.error(`Artifacts: ${artifactDir}`);
  process.exit(1);
}

console.log("Production UX QA passed.");
console.log(`Artifacts: ${artifactDir}`);

async function checkDirectRouteLoads() {
  for (const viewport of VIEWPORTS) {
    for (const route of ROUTES) {
      const page = await newPage(viewport);
      try {
        await gotoRoute(page, route);
        await expectHeading(page);
        await assertCleanUxText(page, `${viewport.name} ${route}`);
        await assertNoHorizontalOverflow(page, `${viewport.name} ${route}`);
        await saveScreenshot(page, `${viewport.name}-${slugRoute(route)}-direct`);
      } finally {
        await page.close();
      }
    }
  }
}

async function checkNavigation(name, viewport) {
  const page = await newPage({ name, ...viewport });
  try {
    await gotoRoute(page, "/");
    const nav = visibleWorkspaceNav(page, name);
    await expect(nav).toBeVisible();
    for (const item of NAV_ITEMS) {
      const link = navLink(nav, item);
      await expect(link).toBeVisible();
      await link.click();
      await page.waitForLoadState("networkidle");
      await expect(page).toHaveURL(new RegExp(`${escapeRegExp(item.href === "/" ? "/" : item.href)}(?:$|[?#])`));
      await expect(navLink(nav, item)).toHaveAttribute("aria-current", "page");
      await expectHeading(page);
      await assertCleanUxText(page, `${name} navigation ${item.label}`);
      await assertNoHorizontalOverflow(page, `${name} navigation ${item.label}`);
      await saveScreenshot(page, `${name}-nav-${slug(item.label)}`);
    }
  } finally {
    await page.close();
  }
}

async function checkChatSuccess() {
  const page = await newPage({
    name: "desktop",
    width: 1440,
    height: 1000,
    allowTransientChatFailure: true,
  });
  try {
    await gotoRoute(page, "/");
    const input = chatInput(page);
    const send = page.getByRole("button", { name: "Send message" });

    await expectText(page, CHAT_EMPTY_STATE);
    await assertDisabled(send, "empty chat send button");
    await input.fill("   ");
    await assertDisabled(send, "whitespace chat send button");

    await submitChatMessage(page, input, send, "Project status", "enter", "chat Enter submit");
    await expectText(page, "assistant");
    await expectTraceCount(page);
    await assertCleanUxText(page, "chat enter success");
    await assertNoHorizontalOverflow(page, "chat enter success");
    await saveScreenshot(page, "chat-enter-success");

    await submitChatMessage(page, input, send, "Show the latest trace summary", "button", "chat button submit");
    await expectText(page, "assistant");
    await expectTraceCount(page);
    await assertCleanUxText(page, "chat button repeated success");
    await saveScreenshot(page, "chat-button-repeated-success");
  } finally {
    await page.close();
  }
}

async function checkChatFailure() {
  const page = await newPage({
    name: "desktop-chat-failure",
    width: 1440,
    height: 1000,
    allowSyntheticChatFailure: true,
  });
  try {
    await page.route("**/api/fpw/chat", async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: { message: "Synthetic QA chat outage", code: "qa_synthetic_outage" } }),
      });
    });
    await gotoRoute(page, "/");
    await chatInput(page).fill("Trigger failure state");
    await page.getByRole("button", { name: "Send message" }).click();
    await expectText(page, "Synthetic QA chat outage");
    await assertCleanUxText(page, "chat failure state");
    await saveScreenshot(page, "chat-failure-state");
  } finally {
    await page.close();
  }
}

async function checkTraceDetails() {
  const page = await newPage({ name: "desktop", width: 1440, height: 1000 });
  try {
    await gotoRoute(page, "/traces");
    const firstSummary = page.locator("details summary").first();
    await firstSummary.click();
    await expectText(page, "Input");
    await expectText(page, "Output");
    await firstSummary.click();
    await assertCleanUxText(page, "trace detail expand collapse");
    await assertNoHorizontalOverflow(page, "trace detail expand collapse");
    await saveScreenshot(page, "trace-detail-expand-collapse");
  } finally {
    await page.close();
  }
}

async function checkResponsiveSurfaces() {
  for (const viewport of VIEWPORTS) {
    const page = await newPage(viewport);
    try {
      await gotoRoute(page, "/");
      await assertNoHorizontalOverflow(page, `${viewport.name} responsive project`);
      await saveScreenshot(page, `${viewport.name}-responsive-project`);
    } finally {
      await page.close();
    }
  }
}

async function newPage(viewport) {
  const page = await browser.newPage({
    viewport: { width: viewport.width, height: viewport.height },
  });
  page.setDefaultTimeout(Number(process.env.FPW_UX_QA_TIMEOUT_MS ?? 20000));
  page.on("console", (message) => {
    const type = message.type();
    const text = message.text();
    consoleMessages.push({ viewport: viewport.name, type, text });
    if (["error", "warning"].includes(type) && !isAllowedConsoleMessage(text, viewport)) {
      failures.push(`${viewport.name} console ${type}: ${text}`);
    }
  });
  page.on("pageerror", (error) => {
    pageErrors.push({ viewport: viewport.name, message: error.message });
    failures.push(`${viewport.name} page error: ${error.message}`);
  });
  return page;
}

async function runStep(name, step) {
  try {
    await step();
  } catch (error) {
    failures.push(`${name} threw ${formatError(error)}`);
  }
}

async function gotoRoute(page, route) {
  const response = await page.goto(`${baseUrl}${route}`, { waitUntil: "networkidle" });
  if (!response || !response.ok()) {
    failures.push(`${route} returned ${response?.status() ?? "no response"}`);
    return;
  }
  await page.locator("main").waitFor();
}

async function expectHeading(page) {
  const headingCount = await page.getByRole("heading", { level: 1 }).count();
  if (headingCount < 1) {
    failures.push(`${page.url()} rendered without an h1`);
  }
}

async function expectText(page, text) {
  try {
    await page.getByText(text, { exact: false }).first().waitFor();
  } catch {
    failures.push(`${page.url()} did not render expected text: ${text}`);
  }
}

async function assertDisabled(locator, label) {
  if (!(await locator.isDisabled())) {
    failures.push(`${label} was enabled`);
  }
}

async function waitForDisabled(locator, label) {
  try {
    await expect(locator).toBeDisabled({ timeout: 5000 });
  } catch {
    failures.push(`${label} was not observed`);
  }
}

async function waitForResponse(responsePromise, label) {
  try {
    return await responsePromise;
  } catch (error) {
    failures.push(`${label} did not receive a chat response: ${formatError(error)}`);
    return null;
  }
}

async function submitChatMessage(
  page,
  input,
  send,
  message,
  method,
  label,
  maxAttempts = CHAT_SUBMIT_ATTEMPTS,
) {
  let lastFailure = null;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    await input.fill(message);
    const responsePromise = page.waitForResponse(isChatPostResponse);
    if (method === "enter") {
      await input.press("Enter");
    } else {
      await send.click();
    }
    await waitForDisabled(send, `${label} loading state${attemptLabel(attempt)}`);
    const response = await waitForResponse(responsePromise, `${label}${attemptLabel(attempt)}`);
    if (!response) {
      return "failed";
    }
    if (response.ok()) {
      return "ok";
    }

    const body = await response.text().catch(() => "");
    lastFailure = `${label} returned HTTP ${response.status()}${body ? `: ${body.slice(0, 240)}` : ""}`;
    if (attempt < maxAttempts && isRetryableChatFailure(response.status(), body)) {
      await page.waitForTimeout(1000 * attempt);
      continue;
    }
    failures.push(lastFailure);
    return "failed";
  }

  if (lastFailure) {
    failures.push(lastFailure);
  }
  return "failed";
}

function isChatPostResponse(response) {
  return response.url().includes("/api/fpw/chat") && response.request().method() === "POST";
}

function formatError(error) {
  if (error instanceof Error) {
    return error.message.split("\n")[0];
  }
  return String(error);
}

function isRetryableChatFailure(status, body) {
  if (status < 500 || status >= 600) {
    return false;
  }
  return /provider|upstream|temporarily|timeout|invalid response/i.test(body);
}

function attemptLabel(attempt) {
  return attempt === 1 ? "" : ` attempt ${attempt}`;
}

async function expectTraceCount(page) {
  const tracePanel = page.getByText("Tool traces").first();
  await tracePanel.waitFor();
  const countText = await page.locator("text=/^[1-9][0-9]*$/").first().textContent().catch(() => null);
  if (!countText) {
    failures.push("chat trace panel did not show a non-zero trace count");
  }
}

async function assertCleanUxText(page, context) {
  const text = await page.locator("body").innerText();
  for (const pattern of BANNED_TEXT) {
    if (pattern.test(text)) {
      failures.push(`${context} rendered banned text pattern ${pattern}`);
    }
  }
}

async function assertNoHorizontalOverflow(page, context) {
  const overflow = await page.evaluate(() => {
    const documentOverflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
    const bodyOverflow = document.body.scrollWidth - document.body.clientWidth;
    return Math.max(documentOverflow, bodyOverflow);
  });
  if (overflow > 1) {
    failures.push(`${context} has ${overflow}px document-level horizontal overflow`);
  }
}

async function saveScreenshot(page, name) {
  const file = path.join(artifactDir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  screenshots.push(file);
}

function visibleWorkspaceNav(page, viewportName) {
  const navName = viewportName === "desktop" ? "Workspace" : "Mobile workspace";
  return page.getByRole("navigation", { name: navName });
}

function navLink(nav, item) {
  return nav.locator(`a[href="${item.href}"]`).filter({ hasText: item.label });
}

function chatInput(page) {
  return page.getByRole("textbox", { name: "Message" });
}

function slugRoute(route) {
  return route === "/" ? "root" : slug(route.replace(/^\//, ""));
}

function slug(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function normalizeBaseUrl(value) {
  return value.replace(/\/+$/, "");
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function isAllowedConsoleMessage(text, viewport) {
  if (viewport.allowSyntheticChatFailure && /503 \(Service Unavailable\)/i.test(text)) {
    return true;
  }
  if (viewport.allowTransientChatFailure && /status of 5\d\d/i.test(text)) {
    return true;
  }
  return /Download the React DevTools/i.test(text);
}
