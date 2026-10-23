import type { APIRoute } from 'astro';
import { sitemapPaths } from '../lib/routes';
import { site } from '../config/site';
const xmlEscape = (value: string) => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&apos;');
export const GET: APIRoute = () => new Response('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + sitemapPaths.map((path) => `  <url>\n    <loc>${xmlEscape(site.url + path)}</loc>\n  </url>`).join('\n') + '\n</urlset>\n', { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
