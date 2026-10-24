// Regressionstest für den <picture>-Rückfall (src/scripts/image-fallback.js).
// Voraussetzung: `npm run build`; nutzt macOS-Chrome wie die übrigen Browser-Prüfungen.
// Ergebnisse: ../.migration/qa/picture-fallback-r2/ (nicht Teil der Veröffentlichung).
import { chromium } from '@playwright/test';
import { createServer } from 'node:http';
import { readFile, writeFile, mkdir, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const dist = path.join(root, 'dist');
const output = path.resolve(root, '../.migration/qa/picture-fallback-r2');
await mkdir(output, { recursive: true });
const mime = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.avif': 'image/avif', '.svg': 'image/svg+xml', '.woff2': 'font/woff2' };

const pageHtml = await readFile(path.join(dist, 'landoak/index.html'), 'utf8');
const handler = pageHtml.match(/<script type="module">([^<]*data-fallback-tried[^<]*)<\/script>/)?.[1];
if (!handler) throw new Error('Rückfall-Skript nicht in dist/landoak/index.html gefunden – zuerst `npm run build`.');
const avifCover = '/assets/images/Landoak/Accessories/landoak-accessories-12-960.avif';
const original = '/assets/images/Landoak/Accessories/landoak-accessories-12.jpg';
// Gleiches Markup wie SiteImage.astro, aber loading=lazy weit unterhalb des Viewports (im Bestand gibt es kein lazy-Bild).
const lazyFixture = `<!doctype html><meta charset=utf-8><body style="margin:0"><div style="height:4000px"></div>
<picture><source type="image/avif" srcset="${avifCover} 960w" sizes="100vw"><source type="image/webp" srcset="${avifCover.replace('.avif', '.webp')} 960w" sizes="100vw"><img id="lazy" src="${original}" alt="" width="1280" height="853" loading="lazy" style="width:300px;height:auto"></picture>
<script type="module">${handler}</script>`;

const server = createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x');
  if (url.pathname === '/__lazy__/') { res.writeHead(200, { 'content-type': mime['.html'] }); return res.end(lazyFixture); }
  let file = path.join(dist, decodeURIComponent(url.pathname));
  try { if ((await stat(file)).isDirectory()) file = path.join(file, 'index.html'); } catch { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': mime[path.extname(file)] || 'application/octet-stream' });
  res.end(await readFile(file));
}).listen(0, '127.0.0.1');
await new Promise((resolve) => server.once('listening', resolve));
const base = `http://127.0.0.1:${server.address().port}`;

const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const viewports = [
  { name: 'desktop-dpr1', viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 },
  { name: 'desktop-dpr2', viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 },
  { name: 'mobile-dpr2', viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
];
const modes = {
  normal: async () => {},
  'avif-blockiert': (context) => context.route(/\.avif$/, (route) => route.abort('failed')),
  'avif-200-html': (context) => context.route(/\.avif$/, (route) => route.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><title>x</title>' })),
  'original-auch-defekt': async (context) => { await context.route(/\.avif$/, (route) => route.abort('failed')); await context.route(/landoak-accessories-12\.jpg$/, (route) => route.abort('failed')); },
};
const state = (page, selector) => page.evaluate((sel) => {
  const img = document.querySelector(sel);
  return { currentSrc: new URL(img.currentSrc || 'about:blank', location.href).pathname, complete: img.complete, width: img.naturalWidth, tried: img.hasAttribute('data-fallback-tried'), sources: img.parentElement.querySelectorAll('source').length };
}, selector);
const settle = (page, selector) => page.waitForFunction((sel) => { const i = document.querySelector(sel); return i.complete; }, selector).then(() => page.waitForTimeout(600));
const results = [], failures = [];
const expect = (ok, name, detail) => { results.push({ name, ok, detail }); if (!ok) failures.push({ name, detail }); console.log(`${ok ? 'OK  ' : 'FAIL'} ${name}`); };
const cover = `img[src="${original}"]`;

try {
  for (const vp of viewports) {
    const { name, ...options } = vp;
    for (const [mode, setup] of Object.entries(modes)) {
      const context = await browser.newContext({ ...options, reducedMotion: 'reduce' });
      await setup(context);
      const page = await context.newPage();
      const requests = [];
      page.on('request', (r) => requests.push(new URL(r.url()).pathname));
      await page.goto(base + '/landoak/', { waitUntil: 'load' });
      await settle(page, cover);
      const s = await state(page, cover);
      const tag = `${name} ${mode}`;
      const originalRequests = requests.filter((u) => u === original).length;
      if (mode === 'normal') {
        expect(s.currentSrc.endsWith('.avif') && s.width > 0 && !s.tried && originalRequests === 0, `${tag}: AVIF wird normal gewählt und decodiert, kein Rückfall, Original nicht geladen`, { s, originalRequests });
      } else if (mode === 'original-auch-defekt') {
        expect(s.tried && s.width === 0 && originalRequests === 1, `${tag}: genau 1 Rückfallversuch, danach keine Schleife`, { s, originalRequests });
        await page.waitForTimeout(1500);
        expect(requests.filter((u) => u === original).length === 1, `${tag}: nach 1,5 s weiterhin genau 1 Anfrage ans Original`, {});
      } else {
        expect(s.currentSrc === original && s.width === 1280 && s.tried && s.sources === 0 && originalRequests === 1, `${tag}: Wechsel auf Original-JPG, Bild decodiert (naturalWidth 1280)`, { s, originalRequests });
        if (vp.name === 'desktop-dpr1' || vp.name === 'mobile-dpr2') await page.locator(cover).screenshot({ path: path.join(output, `${name}-${mode}.png`) });
      }
      await context.close();
    }

    // Fehler, bevor der Handler existiert: Seite ohne Rückfall-Skript laden, Fehlschlag abwarten, Skript dann nachladen.
    {
      const context = await browser.newContext({ ...options, reducedMotion: 'reduce' });
      await context.route(/\.avif$/, (route) => route.abort('failed'));
      await context.route(base + '/landoak/', async (route) => route.fulfill({ status: 200, contentType: mime['.html'], body: pageHtml.replace(`<script type="module">${handler}</script>`, '') }));
      const page = await context.newPage();
      await page.goto(base + '/landoak/', { waitUntil: 'load' });
      await settle(page, cover);
      const before = await state(page, cover);
      expect(before.width === 0 && !before.tried, `${name} fehler-vor-handler: Ausgangslage defekt (Handler fehlt)`, before);
      await page.addScriptTag({ type: 'module', content: handler });
      await page.waitForTimeout(800);
      const after = await state(page, cover);
      expect(after.currentSrc === original && after.width === 1280 && after.tried, `${name} fehler-vor-handler: Initial-Scan stellt Original wieder her`, after);
      await context.close();
    }

    // Lazy-Bild: AVIF scheitert erst nach dem Skript, wenn das Bild in den Viewport scrollt.
    {
      const context = await browser.newContext({ ...options, reducedMotion: 'reduce' });
      await context.route(/\.avif$/, (route) => route.abort('failed'));
      const page = await context.newPage();
      const requests = [];
      page.on('request', (r) => requests.push(new URL(r.url()).pathname));
      await page.goto(base + '/__lazy__/', { waitUntil: 'load' });
      await page.waitForTimeout(500);
      expect(requests.every((u) => !u.includes('landoak-accessories-12')), `${name} lazy: vor dem Scrollen keine Bildanfrage`, requests);
      await page.locator('#lazy').scrollIntoViewIfNeeded();
      await settle(page, '#lazy');
      const s = await state(page, '#lazy');
      expect(s.currentSrc === original && s.width === 1280 && s.tried, `${name} lazy: Fehler nach JS-Start -> Original decodiert`, s);
      await context.close();
    }
  }
} finally { await browser.close(); server.close(); }
await writeFile(path.join(output, 'results.json'), JSON.stringify({ results, failures }, null, 2));
console.log(failures.length ? `${failures.length} von ${results.length} Prüfungen fehlgeschlagen.` : `Alle ${results.length} Prüfungen bestanden.`);
if (failures.length) process.exitCode = 1;
