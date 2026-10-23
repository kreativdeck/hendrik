import pages from '../content/pages.json';
import { posts } from './blog';
export const publicPath = (key: string) => key === 'index' ? '/' : key.endsWith('/index') ? '/' + key.slice(0, -6) + '/' : '/' + key + '/';
export const sitemapPaths = [...new Set([...Object.entries(pages).filter(([key, page]) => key !== '404' && !page.noindex && !(key.startsWith('blog/') && key !== 'blog/index')).map(([key]) => publicPath(key)), ...posts.map(post => '/blog/' + post.slug + '/')])].sort((a, b) => a === '/' ? -1 : b === '/' ? 1 : a.localeCompare(b));
