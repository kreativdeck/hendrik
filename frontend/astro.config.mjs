// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import imagePipeline from './integrations/image-pipeline.mjs';

export default defineConfig({
  output: 'static',
  trailingSlash: 'always',
  compressHTML: true,
  integrations: [imagePipeline()],
  vite: { plugins: [tailwindcss()] },
});
