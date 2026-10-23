// Responsive check (claude.md §4A): every public page at every supported width
// must have no horizontal scroll, no tap target under 24x24px and no visible
// text under 12px. Usage:
//   CHROME=/path/to/chrome BASE_URL=http://localhost:8080 node check.mjs
import puppeteer from 'puppeteer-core';

const base = (process.env.BASE_URL || 'http://localhost:8080').replace(/\/$/, '');
const pages = ['/', '/mission/', '/participate/', '/job-loss-protection/', '/health-financial-protection/',
  '/public-spending/', '/research/', '/survey-methodology/', '/statistics/', '/faq/', '/contact/',
  '/privacy-policy/', '/terms/', '/accessibility/'];
const widths = [320, 375, 414, 768, 1024, 1366, 1920];
const MIN_TARGET = 24;
const MIN_FONT = 12;

const browser = await puppeteer.launch({ executablePath: process.env.CHROME, args: ['--no-sandbox'] });
const page = await browser.newPage();
const failures = [];

for (const width of widths) {
  await page.setViewport({ width, height: 900 });
  for (const path of pages) {
    await page.goto(base + path, { waitUntil: 'networkidle0' });
    const r = await page.evaluate((minTarget, minFont) => {
      const vw = document.documentElement.clientWidth;
      const visible = (e) => { const b = e.getBoundingClientRect(); return b.width > 2 && b.height > 2 && e.checkVisibility(); };
      const overflow = [...document.querySelectorAll('body *')]
        .filter((e) => visible(e) && !e.closest('.itv-table-wrap') && getComputedStyle(e).position !== 'fixed')
        .filter((e) => { const b = e.getBoundingClientRect(); return b.right > vw + 1 || b.left < -1; })
        .slice(0, 3).map((e) => e.tagName.toLowerCase() + (e.className ? '.' + String(e.className).split(' ')[0] : ''));
      const tinyTargets = [...document.querySelectorAll('a, button, input, select')]
        .filter((e) => visible(e) && !e.classList.contains('skip-link') && !e.closest('p, li, td, small'))
        .filter((e) => { const b = e.getBoundingClientRect(); return b.width < minTarget || b.height < minTarget; })
        .map((e) => e.textContent.trim().slice(0, 20));
      const tinyText = [...document.querySelectorAll('body *')]
        .filter((e) => visible(e) && [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()))
        .filter((e) => parseFloat(getComputedStyle(e).fontSize) < minFont)
        .map((e) => e.textContent.trim().slice(0, 20));
      return { hscroll: document.documentElement.scrollWidth - vw, overflow, tinyTargets, tinyText };
    }, MIN_TARGET, MIN_FONT);
    const issues = [];
    if (r.hscroll > 0) issues.push(`horizontal scroll ${r.hscroll}px (${r.overflow.join(', ')})`);
    if (r.tinyTargets.length) issues.push(`targets < ${MIN_TARGET}px: ${r.tinyTargets.join(' | ')}`);
    if (r.tinyText.length) issues.push(`text < ${MIN_FONT}px: ${r.tinyText.slice(0, 3).join(' | ')}`);
    if (issues.length) failures.push(`${width}px ${path}: ${issues.join('; ')}`);
  }
}

// The survey CTA must be reachable from the mobile menu.
await page.setViewport({ width: 375, height: 800 });
await page.goto(base + '/', { waitUntil: 'networkidle0' });
await page.click('.wp-block-navigation__responsive-container-open');
await page.waitForSelector('.is-menu-open .itv-nav-cta a', { visible: true, timeout: 3000 })
  .catch(() => failures.push('375px /: "Take the survey" not visible in the mobile menu'));

await browser.close();
const checked = widths.length * pages.length;
if (failures.length) {
  console.error(`FAIL: ${failures.length} of ${checked} page/width combinations\n` + failures.join('\n'));
  process.exit(1);
}
console.log(`PASS: ${pages.length} pages x ${widths.length} widths (${checked} combinations), mobile menu CTA visible`);
