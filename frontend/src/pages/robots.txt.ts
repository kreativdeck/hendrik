import type { APIRoute } from 'astro';
import { site } from '../config/site';
export const GET: APIRoute = () => new Response(`User-agent: *
Allow: /
Disallow: /api/

# Aggressive SEO-Scraper
User-agent: MJ12bot
Disallow: /

User-agent: DotBot
Disallow: /

Sitemap: ${site.url}/sitemap.xml
`, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
