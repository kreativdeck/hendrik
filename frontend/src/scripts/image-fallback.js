// Fällt bei fehlgeschlagenen responsiven <picture>-Quellen (AVIF/WebP) genau
// einmal auf das originale <img src> zurück. Derselbe Bildinhalt, keine
// Ersatzbilder. Ein Browser wechselt nach einer gescheiterten <source> nicht
// selbst auf <img src>.
const FLAG = 'data-fallback-tried';

const failed = (img) => img.complete && Boolean(img.currentSrc) && img.naturalWidth === 0;

function fallback(img) {
  const picture = img.parentElement;
  if (!picture || picture.localName !== 'picture') return;
  if (img.hasAttribute(FLAG)) return;
  const sources = picture.querySelectorAll('source');
  if (!sources.length) return;
  img.setAttribute(FLAG, '');
  sources.forEach((source) => source.remove());
  // src neu setzen: Chrome übernimmt sonst die Pixeldichte der entfernten Quelle (naturalWidth falsch).
  const src = img.getAttribute('src');
  if (!src) return;
  img.removeAttribute('src');
  img.setAttribute('src', src);
}

document.addEventListener('error', (event) => {
  if (event.target instanceof HTMLImageElement) fallback(event.target);
}, true);

// Bilder, die vor der Ausführung dieses Skripts bereits gescheitert sind.
document.querySelectorAll('picture > img').forEach((img) => {
  if (failed(img)) fallback(img);
});
