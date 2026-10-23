import { readdir, mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import sharp from 'sharp';

const widths = [150, 960, 1920];
const raster = new Set(['.jpg', '.jpeg', '.png', '.webp']);
const encodePath = (value) => value.split('/').map(encodeURIComponent).join('/');

/** Retains original public image URLs and responsive variants within Astro's lifecycle. */
export default function imagePipeline() {
  const images = {};
  const variants = new Map();
  const pending = new Map();
  const transform = (url) => {
    if (!pending.has(url)) {
      const item = variants.get(url);
      pending.set(url, sharp(item.file).rotate().resize({ width: item.width, withoutEnlargement: true })
        .toFormat(item.format, { quality: item.format === 'avif' ? 55 : 82 }).toBuffer()
        .catch((error) => { pending.delete(url); throw error; }));
    }
    return pending.get(url);
  };
  return {
    name: 'hendrik-image-pipeline',
    hooks: {
      'astro:config:setup': async ({ config, updateConfig, command, logger }) => {
        const sourceRoot = fileURLToPath(new URL('assets/images/', config.publicDir));
        async function walk(dir) {
          for (const entry of await readdir(dir, { withFileTypes: true })) {
            const file = path.join(dir, entry.name);
            if (entry.isDirectory()) { await walk(file); continue; }
            if (entry.name.startsWith('.')) continue;
            const relative = path.relative(sourceRoot, file).split(path.sep).join('/');
            const url = '/assets/images/' + relative;
            const image = { url, width: null, height: null, variants: { avif: {}, webp: {} } };
            if (raster.has(path.extname(file).toLowerCase())) {
              const metadata = await sharp(file).metadata();
              const rotated = metadata.orientation >= 5 && metadata.orientation <= 8;
              image.width = rotated ? metadata.height : metadata.width;
              image.height = rotated ? metadata.width : metadata.height;
              for (const width of widths.filter((w) => w <= image.width)) {
                for (const format of ['avif', 'webp']) {
                  const variantUrl = url.slice(0, -path.extname(file).length) + '-' + width + '.' + format;
                  if (variants.has(variantUrl)) throw new Error('Doppeltes Bildziel: ' + variantUrl);
                  variants.set(variantUrl, { file, width, format });
                  image.variants[format][width] = encodePath(variantUrl);
                }
              }
            }
            images[relative] = image;
          }
        }
        await walk(sourceRoot);
        updateConfig({ vite: { plugins: [{
          name: 'hendrik-image-manifest',
          resolveId(id) { if (id === 'virtual:hendrik-images') return '\0' + id; },
          load(id) { if (id === '\0virtual:hendrik-images') return 'export default ' + JSON.stringify(images); },
          configureServer(server) {
            server.middlewares.use(async (req, res, next) => {
              let url;
              try { url = decodeURIComponent((req.url || '').split('?')[0]); } catch { return next(); }
              if (!variants.has(url)) return next();
              try {
                res.setHeader('Content-Type', 'image/' + variants.get(url).format);
                res.setHeader('Cache-Control', 'public, max-age=3600');
                res.end(await transform(url));
              } catch (error) { next(error); }
            });
          },
        }] } });
        if (command === 'build') logger.info(Object.keys(images).length + ' Bildquellen, ' + variants.size + ' AVIF-/WebP-Varianten.');
      },
      'astro:build:done': async ({ dir, logger }) => {
        const output = fileURLToPath(dir);
        const queue = [...variants.keys()];
        let done = 0;
        await Promise.all(Array.from({ length: 3 }, async () => {
          while (queue.length) {
            const url = queue.shift();
            const target = path.join(output, url.slice(1));
            await mkdir(path.dirname(target), { recursive: true });
            await writeFile(target, await transform(url));
            pending.delete(url);
            done++;
          }
        }));
        logger.info(done + ' responsive Bildvarianten erzeugt.');
      },
    },
  };
}
