import { chromium } from '@playwright/test';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const fixture = JSON.parse(await readFile(path.join(root, 'tests/site-expectations.json'), 'utf8'));
const output = path.resolve(root, '../.migration/qa/current');
await mkdir(output, { recursive: true });
const base = process.env.SITE_TEST_URL || 'http://127.0.0.1:4321';
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const errors = [], results = [];
const screenshots = new Set(['index', 'interior', 'interior/holzobjekte', 'formcultur', 'formcultur/lovseth', 'about/lookbook', 'kontakt']);
const routeFor = key => key === '404' ? '/404.html' : key === 'index' ? '/' : '/' + key.replace(/\/index$/, '') + '/';
try {
  for (const width of (process.env.TEST_WIDTHS || '1440,768,390,320').split(',').map(Number)) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 1, reducedMotion: 'reduce' });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push({width, url:page.url(), error:String(error)}));
    for (const key of Object.keys(fixture.pages).sort()) {
      await page.goto(base + routeFor(key), {waitUntil:'networkidle'});
      await page.evaluate(async () => {
        await document.fonts.ready;
        await Promise.all([...document.images].filter(im=>im.getAttribute('src')).map(im=>im.decode().catch(()=>{})));
        await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
      });
      const metrics = await page.evaluate(() => ({
        overflow:document.documentElement.scrollWidth > innerWidth + 1,
        broken:[...document.images].filter(im=>im.getAttribute('src') && (!im.complete || !im.naturalWidth)).map(im=>im.src),
        compact:document.querySelector('[data-header]').classList.contains('is-compact'),
        heroTextVisible:(h=>{
          if(!h)return false;
          // Skript-/Stylesheet-Inhalt wird nicht als Text gerendert.
          const copy=h.cloneNode(true);copy.querySelectorAll('script,style').forEach(node=>node.remove());
          return [...h.querySelectorAll('p,h2,h3,a,button')].length>0||copy.textContent.trim()!==h.querySelector('h1').textContent.trim()||h.querySelector('h1').getBoundingClientRect().width>1;
        })(document.querySelector('section[aria-labelledby="hero-heading"]')),
        heroHeight:Math.round(document.querySelector('section[aria-labelledby="hero-heading"]')?.getBoundingClientRect().height ?? 0),
      }));
      if (metrics.overflow || metrics.broken.length || metrics.heroTextVisible) errors.push({key,width,...metrics});
      results.push({key,width,...metrics});
      if (screenshots.has(key)) await page.screenshot({path:path.join(output,key.replaceAll('/','_')+'-'+width+'.png'),fullPage:true,animations:'disabled'});
    }
    await context.close();
    console.log(`${Object.keys(fixture.pages).length} Seiten bei ${width}px geprüft.`);
  }
} finally { await browser.close(); }
await writeFile(path.join(output,'responsive-results.json'),JSON.stringify({errors,results},null,2));
console.log(JSON.stringify({views:results.length,errors},null,2));
if(errors.length)process.exitCode=1;
