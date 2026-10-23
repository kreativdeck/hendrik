export interface BlogPost { slug: string; title: string; date: string; description: string; content: string }
const files = import.meta.glob<BlogPost>('../content/blog/*.json', { eager: true, import: 'default' });
export const posts = Object.entries(files).map(([file, post]) => ({ ...post, slug: file.split('/').at(-1)!.replace(/\.json$/, '') })).sort((a, b) => a.date === b.date ? a.slug.localeCompare(b.slug) : b.date.localeCompare(a.date));
export const formatDate = (date: string) => date.split('-').reverse().join('.');
