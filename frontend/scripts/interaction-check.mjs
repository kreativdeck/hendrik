import { chromium, expect } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../', import.meta.url));
const fixture = JSON.parse(await readFile(root + 'tests/site-expectations.json', 'utf8'));
const url = process.env.SITE_TEST_URL || 'http://127.0.0.1:4321';
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless:true });
const checked=[];
const page=await browser.newPage({viewport:{width:1920,height:1000},reducedMotion:'reduce'});
const errors=[];page.on('pageerror',e=>errors.push(String(e)));
const ready=async(route)=>{await page.goto(url+route,{waitUntil:'networkidle'});await page.evaluate(()=>document.fonts.ready);};
try {
  await ready('/');
  await expect(page.locator('[data-header]')).not.toHaveClass(/is-compact/);
  const icons = page.locator('[data-submenu-toggle] svg');
  await expect(icons).toHaveCount(2);
  for (const icon of await icons.all()) await expect(icon).toHaveCSS('filter','grayscale(1)');
  await expect(page.locator('[data-header-contact]')).toHaveCSS('background-color','rgb(255, 255, 255)');
  const borderMatchesBody = await page.evaluate(() => getComputedStyle(document.querySelector('[data-header-contact]')).borderColor === getComputedStyle(document.body).color);
  expect(borderMatchesBody).toBe(true);
  const groups=page.locator('[data-submenu-toggle]');
  for(let i=0;i<await groups.count();i++){
    const group=groups.nth(i);await group.click();await expect(group).toHaveAttribute('aria-expanded','true');
    await expect(page.locator('#'+await group.getAttribute('aria-controls'))).toBeVisible();
    await page.keyboard.press('Escape');await expect(group).toHaveAttribute('aria-expanded','false');await expect(group).toBeFocused();
  }
  checked.push('Desktop: alle 5 Dropdowns, Escape und Fokusrückgabe');
  await page.setViewportSize({width:390,height:844});
  await expect(page.locator('[data-header]')).toHaveClass(/is-compact/);
  await page.getByRole('button',{name:'Menü öffnen',exact:true}).click();
  await expect(page.locator('[data-site-nav]')).toHaveClass(/is-open/);
  await expect(page.locator('body')).toHaveClass(/has-open-navigation/);
  for(let i=0;i<await groups.count();i++){
    await groups.nth(i).click();await expect(groups.nth(i)).toHaveAttribute('aria-expanded','true');
  }
  await page.keyboard.press('Escape');
  await page.keyboard.press('Escape');
  await expect(page.locator('[data-nav-toggle]')).toBeFocused();
  await expect(page.locator('[data-nav-toggle]')).toHaveAttribute('aria-expanded','false');
  await page.locator('[data-nav-toggle]').click();
  // The trap includes the brand, navigation, and close button.
  await page.locator('[data-nav-toggle]').focus();await page.keyboard.press('Tab');
  await expect(page.locator('[data-header-brand]')).toBeFocused();
  await page.keyboard.press('Shift+Tab');await expect(page.locator('[data-nav-toggle]')).toBeFocused();
  await page.getByRole('button',{name:'Interior',exact:true}).click();
  await page.getByRole('link',{name:'Wohnen',exact:true}).click();
  await expect(page).toHaveURL(url+'/interior/wohnen/');
  await expect(page.locator('[data-nav-toggle]')).toHaveAttribute('aria-expanded','false');
  await expect(page.locator('[data-site-nav] a[href="/interior/wohnen/"]')).toHaveAttribute('aria-current','page');
  await expect(page.locator('[data-site-nav] a[href="/interior/wohnen/"]')).toHaveCSS('color','rgb(210, 52, 58)');
  await expect(page.locator('[data-submenu-toggle][aria-controls="submenu-0"]')).toHaveCSS('color','rgb(210, 52, 58)');
  await expect(page.locator('#submenu-0 a').last()).toHaveText('Holzobjekte');
  await expect(page.locator('[data-submenu-toggle]')).toHaveText(['Interior','Formcultur','Landoak','Materials','About']);
  checked.push('Mobil: alle Dropdowns, Scrollsperre, Fokuskreislauf, Escape, Navigation und aktive URL');
  await page.locator('[data-nav-toggle]').click();await page.setViewportSize({width:1920,height:1000});
  await expect(page.locator('body')).not.toHaveClass(/has-open-navigation/);
  await expect(page.locator('[data-header]')).not.toHaveClass(/is-compact/);
  checked.push('Offenes Mobilmenü beim Wechsel zu Desktop geschlossen');
  await ready('/');await page.locator('#intro-heading').click();
  await page.evaluate(()=>window.scrollTo(0,600));
  await expect(page.locator('[data-header]')).toHaveClass(/is-hidden/);
  await page.evaluate(()=>window.scrollTo(0,550));
  await expect(page.locator('[data-header]')).not.toHaveClass(/is-hidden/);
  checked.push('Header blendet beim Abwärtsscrollen aus und beim Aufwärtsscrollen ein');
  for(const width of [1920,390]){
    await page.setViewportSize({width,height:900});
    for(const [key,data] of Object.entries(fixture.pages)){
      for(const [galleryKey,gallery] of Object.entries(data.galleries)){
        const route='/'+key+'/';await ready(route);
        const trigger=page.locator('[data-gallery-trigger]').first();
        await expect(trigger).toBeEnabled();await trigger.click();
        const dialog=page.locator('[data-gallery-dialog]');await expect(dialog).toBeVisible();
        const caption=page.locator('[data-gallery-caption]');
        await expect(caption).toHaveText('1 / '+gallery.images.length);
        await page.getByRole('button',{name:'Vorheriges Bild',exact:true}).click();
        await expect(caption).toHaveText(gallery.images.length+' / '+gallery.images.length);
        await page.keyboard.press('ArrowRight');await expect(caption).toHaveText('1 / '+gallery.images.length);
        if(gallery.images.length>1){
          await page.getByRole('button',{name:'Nächstes Bild',exact:true}).click();await expect(caption).toHaveText('2 / '+gallery.images.length);
          await page.keyboard.press('ArrowLeft');await expect(caption).toHaveText('1 / '+gallery.images.length);
        }
        await expect(page.locator('[data-gallery-image]')).toHaveAttribute('alt',gallery.images[0].alt);
        await page.locator('[data-gallery-image]').evaluate(im=>im.decode());
        await page.keyboard.press('Escape');await expect(dialog).not.toBeVisible();await expect(trigger).toBeFocused();
        await ready(route+'#'+galleryKey);await expect(dialog).toBeVisible();
        await page.getByRole('button',{name:'Schließen',exact:true}).click();
        await expect(dialog).not.toBeVisible();await expect(page).toHaveURL(url+route);
        checked.push(width+'px: '+key+' Galerie ('+gallery.images.length+' Bilder), Buttons/Pfeiltasten, Umlauf, Fokus, Hash-Direktlink');
      }
    }
  }
  await ready('/interior/wohnen/');await page.locator('[data-gallery-trigger]').first().click();
  await page.locator('[data-gallery-image]').evaluate(im=>im.src='/missing-test-image.jpg');
  await expect(page.locator('[data-gallery-error]')).toBeVisible();
  await page.keyboard.press('ArrowRight');await expect(page.locator('[data-gallery-error]')).not.toBeVisible();
  await page.getByRole('button',{name:'Schließen',exact:true}).click();
  checked.push('Lightbox: Bildladefehler und Wiederherstellung geprüft');
  await page.setViewportSize({width:1440,height:900});
  for(const key of Object.keys(fixture.pages)){
    if(['404','kontakt','leistungen','impressum','datenschutz','formcultur/solveig'].includes(key)||key.startsWith('blog/'))continue;
    await ready(key==='index'?'/':'/'+key+'/');
    const hero=page.locator('section[aria-labelledby="hero-heading"]');
    if(!await hero.count())continue;
    const h1=hero.locator('h1#hero-heading');
    await expect(h1).toHaveClass(/sr-only/);
    const box=await h1.boundingBox();expect(box.width<=1&&box.height<=1).toBe(true);
    const heroText=await hero.evaluate(el=>el.textContent.trim());
    expect(heroText).toBe((await h1.textContent()).trim());
    expect(await hero.locator('p').count()).toBe(0);
    checked.push('Hero ohne sichtbaren Text, H1 sr-only: '+key);
  }
  await page.setViewportSize({width:1920,height:1000});
  await page.goto(url+'/diese-seite-gibt-es-nicht/',{waitUntil:'networkidle'});
  await expect(page.getByRole('heading',{name:'Seite nicht gefunden',exact:true})).toBeVisible();
  checked.push('404 bei unbekannter URL');
  const touchContext = await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const touch = await touchContext.newPage();
  await touch.goto(url+'/',{waitUntil:'networkidle'});
  await touch.locator('[data-nav-toggle]').tap();
  const touchGroups = touch.locator('[data-submenu-toggle]');
  for(let i=0;i<await touchGroups.count();i++){
    await touchGroups.nth(i).tap();await expect(touchGroups.nth(i)).toHaveAttribute('aria-expanded','true');
  }
  await touch.locator('[data-nav-toggle]').tap();
  await expect(touch.locator('body')).not.toHaveClass(/has-open-navigation/);
  await touch.goto(url+'/about/lookbook/',{waitUntil:'networkidle'});
  await touch.locator('[data-gallery-trigger]').first().tap();
  await expect(touch.locator('[data-gallery-dialog]')).toBeVisible();
  await touch.locator('[data-gallery-next]').tap();
  await expect(touch.locator('[data-gallery-caption]')).toHaveText('2 / 29');
  await touch.locator('[data-gallery-close]').tap();
  await expect(touch.locator('[data-gallery-dialog]')).not.toBeVisible();
  await touchContext.close();
  checked.push('Touch-Emulation: alle Mobil-Dropdowns und Lightbox mit Tippen bedient');
  await page.setViewportSize({width:1920,height:1000});
  await ready('/kontakt/');
  await expect(page.locator('[data-header-contact]')).toHaveCSS('color','rgb(210, 52, 58)');
  await expect(page.locator('a[href="tel:+49177277814"]')).toHaveText('+49 177 277814');
  await ready('/formcultur/solveig/');
  await expect(page.getByRole('heading',{name:'Solveig',exact:true})).toBeVisible();await expect(page.getByText('Coming Soon',{exact:true})).toBeVisible();
  checked.push('Solveig-Coming-Soon-Seite sichtbar');
  checked.push('Graustufen-Symbole, Kontaktbutton, rote aktive Navigation und Mobilnummer geprüft');
  if(errors.length)throw new Error(errors.join('\n'));
  console.log(checked.join('\n'));
  await writeFile(root+'../.migration/qa/interaction-results.json',JSON.stringify({checked,errors},null,2));
} finally {await browser.close();}
