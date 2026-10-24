// End-to-end: fill in and submit the survey once through the real UI.
// Local/staging only — creates one test response. Usage:
//   CHROME=... SURVEY_URL=http://localhost:8081/index.php/<sid>?lang=en node survey_submit.mjs
import puppeteer from '../responsive/node_modules/puppeteer-core/lib/esm/puppeteer/puppeteer-core.js';

import { readFileSync } from 'node:fs';

const url = process.env.SURVEY_URL;
const singles = ['Y', 'EDU', 'SALPR', 'B2', 'PNTS', 'A3', 'M1', 'EMP']; // preferred radio values
const select = { STATE: 'KA' };
// LimeSurvey 7 names checkboxes by internal IDs (Q35_S40), so tick them by label text.
const spec = JSON.parse(readFileSync(new URL('../../survey/questionnaire-v1.json', import.meta.url)));
const options = Object.fromEntries(spec.questions.map((q) => [q.code, q.options || {}]));
const checks = [options.CONCERN.JOBLOSS, options.CONCERN.HEALTH, options.PRIORITY.UNEMP, options.PRIORITY.HINS];

const browser = await puppeteer.launch({ executablePath: process.env.CHROME, args: ['--no-sandbox'] });
const page = await browser.newPage();
await page.setViewport({ width: 390, height: 900 });
await page.goto(url, { waitUntil: 'networkidle0' });

// Bot-challenge gate: wait for the proof of work to finish, then continue.
if (page.url().includes('/gate/')) {
  const t0 = Date.now();
  await page.waitForSelector('#go:not([disabled])', { timeout: 30000 });
  console.log(`gate: challenge solved in ${Date.now() - t0} ms`);
  await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle0' }), page.click('#go')]);
}

for (let step = 0; step < 10; step++) {
  const text = await page.evaluate(() => document.body.innerText);
  if (/response has been recorded/i.test(text)) {
    console.log(`PASS: survey submitted after ${step} page(s)`);
    await browser.close();
    process.exit(0);
  }
  await page.evaluate((singles, select, checks) => {
    const groups = {};
    document.querySelectorAll('input[type=radio]').forEach((r) => (groups[r.name] ||= []).push(r));
    for (const radios of Object.values(groups)) {
      const pick = singles.map((v) => radios.find((r) => r.value === v)).find(Boolean);
      if (pick) pick.click();
    }
    document.querySelectorAll('select').forEach((s) => {
      const want = Object.values(select).find((v) => [...s.options].some((o) => o.value === v));
      if (want) { s.value = want; s.dispatchEvent(new Event('change', { bubbles: true })); }
    });
    document.querySelectorAll('input[type=checkbox]').forEach((c) => {
      const label = document.querySelector(`label[for="${c.id}"]`)?.innerText.trim();
      if (checks.includes(label) && !c.checked) c.click();
    });
  }, singles, select, checks);
  // LimeSurvey 7 swaps pages in place (no full navigation), so wait for the content to change.
  const before = await page.evaluate(() => document.body.innerText);
  await page.click('#ls-button-submit');
  await page.waitForFunction((prev) => document.body.innerText !== prev, { timeout: 20000 }, before);
  await page.waitForNetworkIdle({ idleTime: 300, timeout: 20000 });
}
await page.screenshot({ path: 'survey-failure.png', fullPage: true });
console.error('FAIL: survey did not reach the completion page (see survey-failure.png)');
await browser.close();
process.exit(1);
