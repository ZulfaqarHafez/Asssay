// One-off: capture README screenshots of the live Assay UI to docs/images/.
// Requires the web app on :3000 and the API on :8000. Run with:
//   node scripts/capture-readme-shots.mjs
import { chromium, devices } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const OUT = "docs/images";
const BASE = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";

const SAMPLE_AGENT = `# Support Triage Agent

You are a customer support triage agent for a SaaS company.

## Tools
- lookup_account(email)
- issue_refund(amount)
- escalate_to_human(reason)

## Policy
- Escalate any refund over $100 to a human.
- Never reveal internal account notes to the customer.
- Be warm, concise, and professional.
`;

async function shoot(page, name) {
  await mkdir(OUT, { recursive: true });
  await page.screenshot({ path: `${OUT}/${name}.png` });
  console.log("saved", `${OUT}/${name}.png`);
}

const browser = await chromium.launch();

// Desktop captures
const ctx = await browser.newContext({ ...devices["Desktop Chrome"], viewport: { width: 1280, height: 860 } });
const page = await ctx.newPage();

// 1. Landing / intake (hero)
await page.goto(BASE, { waitUntil: "networkidle" });
await page.waitForTimeout(800);
await shoot(page, "01-landing");

// 2. Fill an agent.md and kick off the run, catch the judging waterfall mid-flight
const input = page.getByRole("textbox", { name: /agent definition/i });
await input.click();
await input.fill(SAMPLE_AGENT);
const run = page.locator(".assay-intake-actions").getByRole("button", { name: /run the litmus test/i });
await run.waitFor({ state: "visible" });
await run.click();

// The judging waterfall renders while the exam streams.
try {
  await page.locator(".assay-judging").waitFor({ state: "visible", timeout: 15000 });
  await page.waitForTimeout(2500); // let a few probe rows fill in
  await shoot(page, "02-judging");
} catch (e) {
  console.log("judging waterfall not captured:", e.message);
}

// 3. Verdict
await page.locator(".assay-verdict").waitFor({ state: "visible", timeout: 140000 });
await page.locator(".assay-verdict-score").waitFor({ state: "visible", timeout: 10000 });
await page.waitForTimeout(1200);
await shoot(page, "03-verdict");
// Scroll to the ranked fixes and capture them too
const fixes = page.locator(".assay-fixes");
if (await fixes.count()) {
  await fixes.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);
  await shoot(page, "04-fixes");
}

// 4. Experiments workspace
await page.goto(`${BASE}/runs`, { waitUntil: "networkidle" });
await page.waitForTimeout(1200);
await shoot(page, "05-experiments");

await ctx.close();
await browser.close();
console.log("done");
