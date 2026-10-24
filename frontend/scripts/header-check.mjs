// Regression: sichtbare Header-Elemente dürfen beim Seitenladen ihre Position
// nicht ändern, auch vor dem Start von JS und bei langsamen/fehlenden Schriften.
import { chromium, expect } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
const origin = (process.env.SITE_TEST_URL || 'http://127.0.0.1:4321').replace(/\/$/, '');
const output = new URL('../../.migration/qa/header-current/', import.meta.url);
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true, ignoreDefaultArgs: ['--hide-scrollbars'] });
const results = [];
const errors = [];
const recordFrames = () => {
  window.__headerFrames = [];
  const visible = el => el && el.getClientRects().length && getComputedStyle(el).visibility === 'visible';
  const box = el => {
    if (!visible(el)) return null;
    const r = el.getBoundingClientRect();
    return [r.x, r.width, r.height];
  };
  const sample = () => {
    const h = document.querySelector('[data-header]');
    if (h) {
      const positions = { header: box(h), logo: box(h.querySelector('[data-header-brand]')), contact: box(h.querySelector('[data-header-contact]')), burger: box(h.querySelector('[data-nav-toggle]')) };
      [...h.querySelectorAll('[data-header-list] > li > button, [data-header-list] > li > a')].forEach((el, i) => {
        if (!visible(el)) return;
        const range = document.createRange(); range.selectNodeContents(el);
        const r = range.getBoundingClientRect();
        positions['label-' + i] = [r.x, r.width, r.height];
      });
      window.__headerFrames.push({ t: performance.now(), ready: h.classList.contains('is-ready'), font: document.fonts.check('300 1em "Exo 2"'), positions });
    }
    if (performance.now() < 6000) requestAnimationFrame(sample);
  };
  requestAnimationFrame(sample);
};
const verify = async (page, label, baseline) => {
  await expect(page.locator('[data-header]')).toHaveClass(/is-ready/);
  await page.waitForTimeout(850);
  const frames = await page.evaluate(() => window.__headerFrames);
  const last = frames.at(-1);
  let maxShift = 0;
  const shifts = [];
  for (const frame of frames) for (const [key, coords] of Object.entries(frame.positions)) {
    if (!coords) continue;
    const end = last.positions[key];
    if (!end) { shifts.push({ t: frame.t, key, reason: 'vor JS sichtbar, danach verschwunden' }); continue; }
    const dx = Math.max(...coords.map((v, i) => Math.abs(v - end[i])));
    maxShift = Math.max(maxShift, dx);
    if (dx > 0.5) shifts.push({ t: frame.t, key, dx });
  }
  if (baseline) for (const [key, coords] of Object.entries(last.positions)) {
    if (!coords || !baseline[key]) continue;
    expect(Math.max(...coords.map((v, i) => Math.abs(v - baseline[key][i]))), `${label}: ${key} gegenüber vorheriger Seite`).toBeLessThanOrEqual(0.5);
  }
  results.push({ label, maxShift, shifts, frames: frames.length, beforeJS: frames.filter(f => !f.ready).length });
  expect(shifts, label).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), label + ': kein horizontaler Überlauf').toBe(true);
  return last.positions;
};
try {
  // Neuer und alter Umschaltbereich, schmale Geräte und Retina. Die Verzögerung
  // von Skripten erzwingt sichtbare Frames des anfänglichen CSS-Zustands.
  for (const dpr of [1, 2]) for (const width of [320, 390, 1170, 1177, 1235, 1247, 1248, 1250, 1440, 1664]) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: dpr });
    await context.addInitScript(recordFrames);
    await context.route('**/_astro/*.js', async route => { await new Promise(r => setTimeout(r, 350)); await route.continue(); });
    const page = await context.newPage();
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto(origin + '/landoak/', { waitUntil: 'load' });
    await verify(page, `cold ${width}@${dpr}`);
    await context.close();
  }
  for (const fontMode of ['slow', 'failed']) for (const width of [390, 1664]) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 2 });
    await context.addInitScript(recordFrames);
    const fontRequests = [];
    await context.route('**/assets/fonts/**', async route => {
      fontRequests.push(route.request().url());
      if (fontMode === 'failed') await route.abort();
      else { await new Promise(r => setTimeout(r, 2500)); await route.continue(); }
    });
    const page = await context.newPage();
    page.on('pageerror', e => errors.push(String(e)));
    let baseline;
    for (const path of ['/interior/', '/interior/wohnen/', '/formcultur/solveig/', '/landoak/']) {
      if (!baseline) await page.goto(origin + path, { waitUntil: 'load' });
      else {
        const isCompact = await page.locator('[data-header]').evaluate(h => h.classList.contains('is-compact'));
        if (isCompact) await page.locator('[data-nav-toggle]').click();
        const menu = path.startsWith('/interior/') ? 'submenu-0' : path.startsWith('/formcultur/') ? 'submenu-1' : 'submenu-2';
        await page.locator(`[aria-controls="${menu}"]`).click();
        await page.locator(`#${menu} a[href="${path}"]`).click();
        await page.waitForLoadState('load');
      }
      baseline = await verify(page, `${fontMode} ${width}@2 ${path}`, baseline);
    }
    await page.goBack({ waitUntil: 'load' }); await verify(page, `${fontMode} ${width}@2 back`, baseline);
    await page.goForward({ waitUntil: 'load' }); await verify(page, `${fontMode} ${width}@2 forward`, baseline);
    expect(fontRequests.some(u => u.includes('latin-300.woff2')), 'kritische Schrift ist eingebettet').toBe(false);
    await page.locator('[data-header]').screenshot({ path: new URL(`header-${width}-${fontMode}.png`, output).pathname });
    await context.close();
  }
  expect(errors).toEqual([]);
  console.log(`OK: ${results.length} Header-Prüfungen, keine Positionssprünge >0,5 px; Schriftfehler, langsames Netz, echte Links und Zurück/Vorwärts geprüft.`);
} finally {
  await writeFile(new URL('results.json', output), JSON.stringify({ origin, results, errors }, null, 2));
  await browser.close();
}
