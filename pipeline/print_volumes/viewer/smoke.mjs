// Browser smoke test of the card workbench against a trial review server:
// the three decision forms, a pointer decision while a form is open followed
// by keys, "all right" on a card taller than its column, N on a slip, a second
// reviewer blind to the first, the server's status error, the skip link and
// the wording of the wiki drawer. Every assertion reads what the page shows.
//
// The run posts decisions under reviewer names of its own, so it must never
// meet the real decision log: start a trial server with its own log first,
//   python -m uv run --group print python pipeline/print_volumes/review_server.py --port 8773 --log <scratch>/decisions.jsonl
// then run
//   node pipeline/print_volumes/viewer/smoke.mjs [--port 8773] [--shots <dir>] [--only <step name part>]
// Playwright is not a project dependency; where `import "playwright"` fails,
// PLAYWRIGHT_DIR names a folder whose node_modules hold it. Exits 1 on a failure.
// Nothing here holds print text: the passages it selects are read from the page.

import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

const arg = (name, fallback) => {
  const at = process.argv.indexOf(name);
  return at > 0 ? process.argv[at + 1] : fallback;
};
const port = Number(arg("--port", "8773"));
const shots = arg("--shots", "");
const only = arg("--only", "");
// 8767 is the review server that records the real decisions.
if (port === 8767) {
  console.error("FEHLER port 8767 records the real review; start a trial server with --log");
  process.exit(2);
}
if (shots) mkdirSync(shots, { recursive: true });

async function playwright() {
  try {
    return await import("playwright");
  } catch {
    if (!process.env.PLAYWRIGHT_DIR) throw new Error("playwright not found; set PLAYWRIGHT_DIR to a folder that has it installed");
    return createRequire(join(process.env.PLAYWRIGHT_DIR, "package.json"))("playwright");
  }
}

const origin = `http://127.0.0.1:${port}`;
const base = `${origin}/viewer/cards.html`;
const run = Date.now().toString(36);
const reviewerA = `smoke-${run}-a`;
const reviewerB = `smoke-${run}-b`;

let failed = 0;
const expect = (ok, label) => {
  if (ok) console.log(`OK ${label}`);
  else {
    failed += 1;
    console.error(`FEHLER ${label}`);
  }
};

async function logOf(name) {
  const response = await fetch(`${origin}/review/decisions`);
  return (await response.json()).filter((d) => d.reviewer === name);
}

const { chromium } = await playwright();
const browser = await chromium.launch();
const errors = [];

async function open(name, { width = 1440, height = 900, hash = "#/?r=open", setup = null } = {}) {
  const context = await browser.newContext({ viewport: { width, height } });
  await context.addInitScript((n) => n && localStorage.setItem("print-reviewer", n), name);
  const page = await context.newPage();
  page.setDefaultTimeout(8000);
  page.on("pageerror", (e) => errors.push(e.message));
  if (setup) await setup(page);
  await page.goto(`${base}${hash}`);
  await page.waitForSelector("#inspector article.card", { timeout: 30000 });
  return page;
}

// One scenario: a thrown error counts as its failure, and the next one runs.
async function step(name, fn) {
  if (only && !name.includes(only)) return;
  const pages = [];
  const page = async (...args) => {
    const p = await open(...args);
    pages.push(p);
    return p;
  };
  try {
    await fn(page);
  } catch (e) {
    expect(false, `${name}: ${e.message.split("\n")[0]}`);
  } finally {
    for (const p of pages) await p.context().close();
  }
}

const message = (page) => page.textContent("#message");
const cardAddress = (page) => page.textContent("#inspector .card-address");
const nameIn = (address) => (address === "Unnumbered" ? "unnumbered object" : address);
const forms = (page) => page.locator("#inspector .decision-form").count();

// Waits for the status line to change after an action, and returns it.
async function after(page, action) {
  const before = await message(page);
  await action();
  await page.waitForFunction((b) => document.getElementById("message").textContent !== b, before);
  return message(page);
}

async function shot(page, name) {
  if (shots) await page.screenshot({ path: join(shots, `${name}.png`) });
}

const focusPick = (page) => page.focus("#inspector button.pick.is-current");
const activeIndex = (page) => page.evaluate(() => document.activeElement?.dataset?.index ?? null);
const submit = (page) => page.click("#inspector .decision-form button[type=submit]");

// Selects the characters of a mark in the entry text that is not the current value's.
async function selectPassage(page, selector = "#inspector .card-entry mark:not(.current)") {
  return page.evaluate((sel) => {
    const mark = document.querySelector(sel);
    if (!mark) return false;
    const range = document.createRange();
    range.selectNodeContents(mark);
    getSelection().removeAllRanges();
    getSelection().addRange(range);
    return true;
  }, selector);
}

await step("active marks", async (page) => {
  const p = await page(reviewerA);
  expect((await p.getAttribute("#inspector article.card", "aria-current")) === "true", "the active card carries aria-current");
  expect((await p.locator('.slip-open[aria-current="true"]').count()) === 1, "exactly one slip carries aria-current");
});

await step("boundary by key", async (page) => {
  const p = await page(reviewerA);
  const address = await cardAddress(p);
  await focusPick(p);
  await p.keyboard.press("b");
  expect((await forms(p)) === 1, "B opens the boundary form");
  expect(await p.evaluate(() => document.activeElement.tagName === "TEXTAREA"), "the boundary form takes the focus in its note");
  await p.keyboard.type("Invented smoke note: the object ends one line early.");
  const saved = await after(p, () => submit(p));
  expect(saved === `Saved on ${nameIn(address)}, boundary flagged.`, `the boundary message names its object (${saved})`);
  expect((await p.locator("#inspector .card-flagged").count()) === 1, "a flagged card says so in a word");
  await shot(p, "1440-boundary-flagged");
  expect((await p.getAttribute("#inspector tr.added button.withdraw", "aria-label")) === "Remove the boundary flag", "Remove names what it removes");
  const removed = await after(p, () => p.click("#inspector tr.added button.withdraw"));
  expect(removed === `Saved on ${nameIn(address)}, the boundary flag removed.`, `withdrawing names the object (${removed})`);
});

await step("boundary by button", async (page) => {
  const p = await page(reviewerA);
  await p.click('#inspector [data-card-act="boundary"]');
  expect((await forms(p)) === 1, "the Boundary button opens the form");
});

await step("Escape", async (page) => {
  const p = await page(reviewerA);
  await p.click('#inspector [data-card-act="missing"]');
  await p.focus("#q");
  await p.keyboard.press("Escape");
  expect((await forms(p)) === 1, "Escape in the search field does not cancel the form");
  await p.focus("#inspector .decision-form select");
  await p.keyboard.press("Escape");
  expect((await forms(p)) === 0, "Escape in the form cancels it");
});

await step("wrong", async (page) => {
  const p = await page(reviewerA);
  const address = await cardAddress(p);
  await focusPick(p);
  const index = await activeIndex(p);
  await p.keyboard.press("w");
  expect((await forms(p)) === 1, "W opens the correction form");
  if (await selectPassage(p)) {
    await p.waitForTimeout(100);
    expect(/found at characters \d+ to \d+/.test(await p.textContent("#inspector .decision-form .found")), "a selection in the entry text fills the passage");
  }
  // An inherited value comes with the box ticked and fixed.
  const box = p.locator('#inspector .decision-form input[type="checkbox"]');
  if (!(await box.isDisabled())) await box.check();
  const wrong = await after(p, () => submit(p));
  expect(wrong.startsWith(`Saved on ${nameIn(address)}, `) && wrong.endsWith(" wrong."), `the correction message names its object (${wrong})`);
  const label = await p.getAttribute(`#inspector button.pick[data-index="${index}"]`, "aria-label");
  expect(!/wrong|right|unsure/.test(label), "a decided value's name does not repeat its sign");
  expect((await p.textContent(`#inspector button.pick[data-index="${index}"] + .sign .visually-hidden`)) === "wrong", "the sign beside it says wrong");
  expect((await p.locator("#inspector .card-flagged").count()) === 1, "a card with a wrong value says flagged in a word");
});

await step("pointer decision with a form open", async (page) => {
  const p = await page(reviewerA);
  const address = await cardAddress(p);
  await focusPick(p);
  await p.keyboard.press("m");
  expect((await forms(p)) === 1, "M opens the missing-value form");
  const right = await after(p, () => p.click("#inspector button.act-confirm"));
  expect(right.startsWith(`Saved on ${nameIn(address)}, `), `Right by pointer saves with a form open (${right})`);
  expect((await p.locator(".decision-form").count()) === 0, "the form is gone after the card is rebuilt");
  const before = await activeIndex(p);
  await p.keyboard.press("j");
  expect((await activeIndex(p)) !== before, "J moves after a pointer decision taken with a form open");
  const byKey = await after(p, () => p.keyboard.press("r"));
  expect(byKey.startsWith(`Saved on ${nameIn(address)}, `), `R saves after a pointer decision taken with a form open (${byKey})`);
});

await step("missing", async (page) => {
  const p = await page(reviewerA);
  const address = await cardAddress(p);
  await focusPick(p);
  await p.keyboard.press("m");
  await p.selectOption("#inspector .decision-form select", "notes");
  expect(await selectPassage(p, "#inspector .card-entry .object mark"), "a passage inside the object can be selected");
  const added = await after(p, () => submit(p));
  expect(added === `Saved on ${nameIn(address)}, missing value added.`, `the missing-value message names its object (${added.startsWith("Saved") ? "saved" : "refused"})`);
  expect(((await p.getAttribute("#inspector tr.added button.withdraw", "aria-label")) ?? "").startsWith("Remove the added value Note"), "Remove names the added value");
});

await step("form layout and page chrome", async (page) => {
  const p = await page(reviewerA);
  // 11: the focus ring does not cover the label above the passage field.
  await p.click('#inspector [data-card-act="missing"]');
  const input = p.locator('#inspector .decision-form input[type="text"]');
  await input.focus();
  const gap = await p.evaluate(() => {
    const field = document.querySelector('#inspector .decision-form input[type="text"]');
    const range = document.createRange();
    range.selectNodeContents(field.closest("label").firstChild);
    const style = getComputedStyle(field);
    return field.getBoundingClientRect().top - parseFloat(style.outlineWidth) - parseFloat(style.outlineOffset) - range.getBoundingClientRect().bottom;
  });
  expect(gap >= 0, `the focus ring stays clear of the label "Passage" (${gap.toFixed(1)}px)`);
  await shot(p, "1440-missing-form");

  // 7: the foot repeats no PDF page the head already links.
  const pdf = await p.evaluate(() => {
    const foot = document.querySelector("#inspector .value-pdf");
    return { hidden: foot.hidden, foot: foot.href, head: document.querySelector("#inspector .card-id .pdf-link").href };
  });
  expect(pdf.hidden || pdf.foot !== pdf.head, "the foot links another PDF page than the head, or none");

  // The live region keeps its display; disabled buttons do not fade.
  const display = await p.evaluate(() => {
    const m = document.getElementById("message");
    const text = m.textContent;
    m.textContent = "Invented message";
    const full = getComputedStyle(m).display;
    m.textContent = "";
    const empty = getComputedStyle(m).display;
    m.textContent = text;
    return [full, empty];
  });
  expect(display[0] === display[1], `the live region keeps its display when empty (${display.join(" / ")})`);
  expect((await p.evaluate(() => getComputedStyle(document.getElementById("prev")).opacity)) === "1", "a disabled button is not faded");

  // The chain is data and stands on the card's white; the help names LLM proposals.
  await p.click('#inspector [data-card-act="chain"]');
  const ground = await p.evaluate(() => getComputedStyle(document.querySelector("#inspector .card-chain")).backgroundColor);
  expect(ground === "rgb(255, 255, 255)", `the provenance chain stands on white (${ground})`);
  expect((await p.textContent("#help-dialog")).includes("LLM proposal"), "the help does not claim every value was read by a rule");
});

await step("decision in flight while another card opens", async (page) => {
  // The server answers late, and the reviewer opens another slip meanwhile.
  const late = (p) => p.route("**/review/decisions", async (r) => (r.request().method() === "POST" ? setTimeout(() => r.continue(), 1500) : r.continue()));
  const p = await page(`smoke-${run}-f`, { setup: late });
  const address = await cardAddress(p);
  await focusPick(p);
  const slip = p.locator(".slip-col .slip-open").nth(2);
  const other = await slip.getAttribute("data-open");
  const said = await after(p, async () => {
    await p.keyboard.press("r");
    await slip.click();
  });
  await p.waitForTimeout(300);
  expect(said.startsWith(`Saved on ${nameIn(address)}, `), `the late message names the card it saved (${said})`);
  expect((await p.getAttribute("#inspector article.card", "data-card-id")) === other, "the card opened meanwhile stays on screen");
  expect(await p.evaluate((id) => document.activeElement?.dataset?.open === id, other), "the focus stays where the reviewer put it, not on the card that left");
});

await step("all right on a long card", async (page) => {
  const name = `smoke-${run}-c`;
  const p = await page(name, { height: 420 });
  const slips = await p.locator(".slip-col .slip-open").count();
  // A card nobody shown has decided, so that only the column hides its values.
  let tall = false;
  for (let i = 0; i < slips && !tall; i++) {
    await p.locator(".slip-col .slip-open").nth(i).click();
    await p.waitForSelector("#inspector article.card");
    tall = await p.evaluate(() => {
      const body = document.querySelector(".detail-col .col-body").getBoundingClientRect();
      const open = document.querySelector("#inspector .card-progress").textContent.startsWith("0/");
      return open && [...document.querySelectorAll("#inspector button.pick")].some((b) => b.getBoundingClientRect().bottom > Math.min(body.bottom, innerHeight));
    });
  }
  expect(tall, "an undecided sample card has values below its column at 1440 by 420");
  if (!tall) return;
  await focusPick(p);
  const refused = await after(p, () => p.keyboard.press("a"));
  expect(refused.startsWith(`Not saved on ${nameIn(await cardAddress(p))}, `) && refused.includes("not in view"), `A refuses while values lie below the column (${refused})`);
  expect((await logOf(name)).length === 0, "A posted nothing for the values out of view");
  await shot(p, "1440x420-all-right-refused");
  await p.setViewportSize({ width: 1440, height: 2600 });
  const fits = await p.evaluate(() => {
    const body = document.querySelector(".detail-col .col-body");
    return body.scrollHeight <= body.clientHeight;
  });
  if (!fits) {
    console.log("SKIP the card is taller than a 2600 pixel window; the positive case is not run");
    return;
  }
  await focusPick(p);
  const saved = await after(p, () => p.keyboard.press("a"));
  expect(saved.startsWith("Saved on") && (await logOf(name)).length > 0, `A confirms once every value is in view (${saved})`);
});

await step("N on a slip", async (page) => {
  const p = await page(`smoke-${run}-d`);
  const active = () => p.evaluate(() => new URLSearchParams(location.hash.split("?")[1]).get("o"));
  const was = await active();
  await p.locator(".slip-col .slip-open").nth(3).focus();
  await p.keyboard.press("n");
  await p.waitForFunction((a) => new URLSearchParams(location.hash.split("?")[1]).get("o") !== a, was).catch(() => null);
  expect((await active()) !== was, "N with the focus on a slip opens the next open card");
});

await step("second reviewer", async (page) => {
  // The first reviewer decides at least one value here, so that the step stands alone.
  const first = await page(reviewerA);
  await focusPick(first);
  await after(first, () => first.keyboard.press("r"));
  const object = (await logOf(reviewerA))[0]?.object;
  expect(Boolean(object), "the first reviewer has decisions on record");
  const hash = `#/?${new URLSearchParams({ r: "sample", o: object })}`;
  const blind = async (label, setup = null) => {
    const p = await page(reviewerB, { hash, setup });
    await p.waitForSelector(`#inspector article.card[data-card-id="${object}"]`);
    const state = await p.evaluate(() => ({
      signs: document.querySelectorAll("#inspector .sign").length,
      added: document.querySelectorAll("#inspector tr.added").length,
      progress: document.querySelector("#inspector .card-progress").textContent,
    }));
    expect(state.signs === 0 && state.added === 0 && state.progress.startsWith("0/"), `${label}: the second reviewer sees no decision of the first (${state.signs} signs, ${state.progress})`);
    await p.click('#inspector [data-card-act="chain"]');
    expect(!(await p.textContent("#inspector .card-chain")).includes("at the last export"), `${label}: the chain shows no exported review state`);
  };
  await blind("current server");
  await blind("server without the filter", (p) => p.route("**/review/decisions?*", (r) => r.fulfill({ status: 404, body: "{}" })));
  // A server that ignored the filter and sent the whole log.
  const whole = JSON.stringify(await (await fetch(`${origin}/review/decisions`)).json());
  await blind("server sending the whole log", (p) => p.route("**/review/decisions?*", (r) => r.fulfill({ status: 200, contentType: "application/json", body: whole })));
  // An export that carries another reviewer's state on every value (p12 writes reviewState from the whole log).
  const stated = (node) => {
    if (Array.isArray(node)) node.forEach(stated);
    else if (node && typeof node === "object") {
      if ([node.type].flat().includes("kp:Value")) node.reviewState = "confirmed";
      Object.values(node).forEach(stated);
    }
  };
  await blind("export carrying a review state", (p) =>
    p.route("**/jsonld/**", async (r) => {
      const doc = await (await r.fetch()).json();
      stated(doc);
      await r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(doc) });
    })
  );
  const own = await page(reviewerA, { hash });
  expect((await own.locator("#inspector .sign").count()) > 0, "the first reviewer still sees their own decisions");
});

for (const width of [1440, 390]) {
  await step(`${width}: status error`, async (page) => {
    const body = JSON.stringify({ recording: false, error: "invented smoke error, the log cannot be read" });
    const p = await page(reviewerA, { width, setup: (q) => q.route("**/review/status", (r) => r.fulfill({ status: 200, contentType: "application/json", body })) });
    expect((await p.isVisible("#review-error")) && (await p.textContent("#review-error")).includes("invented smoke error"), `${width}: the status error stands on the page`);
    expect((await p.locator("#inspector button.act").count()) === 0, `${width}: the cards are read only`);
    await shot(p, `${width}-status-error`);
  });
}

await step("skip link and tab order", async (page) => {
  const p = await page(reviewerA);
  const stops = await p.evaluate(() => {
    const card = document.querySelector("#inspector");
    const all = document.querySelectorAll("a[href], button, input, select, textarea, [tabindex]");
    return [...all].filter((n) => n.tabIndex >= 0 && !n.disabled && n.checkVisibility() && n.compareDocumentPosition(card) & Node.DOCUMENT_POSITION_FOLLOWING).length;
  });
  console.log(`INFO ${stops} tab stops lie before the card`);
  const stray = await p.evaluate(() => [...document.querySelectorAll(".slip:not(.is-active) .slip-move")].filter((b) => b.tabIndex >= 0).length);
  expect(stray === 0, `move buttons of inactive slips are no tab stops (${stray} are)`);
  // Focus at the start of the document, as after loading the page.
  await p.evaluate(() => {
    document.body.tabIndex = -1;
    document.body.focus();
    document.body.removeAttribute("tabindex");
  });
  await p.keyboard.press("Tab");
  expect((await p.evaluate(() => document.activeElement.id)) === "skip-card", "the first tab stop is the skip link");
  await shot(p, "1440-skip-link");
  await p.keyboard.press("Enter");
  expect(await p.evaluate(() => Boolean(document.activeElement.closest("#inspector article.card"))), "the skip link moves the focus into the card");
});

for (const width of [1440, 390]) {
  await step(`${width}: wiki drawer`, async (page) => {
    const p = await page(reviewerA, { width, hash: "#/?w=fields" });
    await p.click('#inspector [data-card-act="wiki"]');
    const drawer = await p.evaluate(() => {
      const d = document.querySelector("#inspector .wiki-drawer");
      return { text: d.textContent, title: d.querySelector(".cand-claim")?.title ?? "" };
    });
    expect(!/match/i.test(drawer.text) && !/claim:/.test(drawer.text), `${width}: the drawer text names no match and no claim id`);
    expect(drawer.title.includes("claim:"), `${width}: the claim ids stand in the title`);
    await shot(p, `${width}-wiki-drawer`);
  });
}

await step("390: boundary", async (page) => {
  const p = await page(`smoke-${run}-e`, { width: 390, height: 844 });
  await focusPick(p);
  await p.keyboard.press("b");
  expect((await forms(p)) === 1, "390: B opens the boundary form");
  await shot(p, "390-boundary-form");
  await p.keyboard.type("Invented smoke note at the narrow width.");
  await after(p, () => submit(p));
  await p.locator("#inspector .card-status").scrollIntoViewIfNeeded();
  await shot(p, "390-flagged");
});

expect(errors.length === 0, `no script error on the page${errors.length ? ` (${[...new Set(errors)].join("; ")})` : ""}`);
await browser.close();
console.log(failed ? `FEHLER ${failed} smoke check${failed > 1 ? "s" : ""} failed` : "OK smoke test");
process.exit(failed ? 1 : 0);
