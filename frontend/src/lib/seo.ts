import organization from '../content/settings/organization.json';
import siteContent from '../content/settings/site.json';
import { site } from '../config/site';
import type { SectionData } from './sections';
import type { BlogPost } from './blog';
export interface SchemaPage {
  urlPath: string; name: string; description: string; datePublished?: string;
  breadcrumbs?: { name: string; urlPath: string }[];
  faqs?: { question: string; answer: string }[];
}
export interface PageMeta { title: string; description: string; noindex: boolean; schema: object | null }
const absolute = (path: string) => site.url + '/' + path.replace(/^\//, '');
const ref = (type: string) => ({ '@id': site.url + '/#' + type });
/** Native equivalent of the original PHP schema builders. */
export function buildSchema(types: string[], page: SchemaPage) {
  const url = absolute(page.urlPath);
  const id = url.replace(/\/$/, '') + '/#';
  const details = { ...(page.description.trim() && { description: page.description }), inLanguage: siteContent.language };
  const graph: object[] = [];
  for (const type of types) {
    if (type === 'Organization') graph.push({
      '@type': type, '@id': site.url + '/#organization', name: organization.name, url: site.url + '/',
      ...(organization.alternateName && { alternateName: organization.alternateName }),
      ...(organization.logo && { logo: absolute(organization.logo) }),
      ...(organization.email && { email: organization.email }),
      ...(organization.telephone && { telephone: organization.telephone }),
      address: { '@type': 'PostalAddress', ...organization.address },
      ...(organization.sameAs.length && { sameAs: organization.sameAs }),
    });
    if (type === 'WebSite') graph.push({ '@type': type, '@id': site.url + '/#website', url: site.url + '/', name: siteContent.name, publisher: ref('organization'), inLanguage: siteContent.language });
    if (type === 'WebPage') graph.push({ '@type': type, '@id': id + 'webpage', url, name: page.name, isPartOf: ref('website'), ...details });
    if (type === 'Blog') graph.push({ '@type': type, '@id': id + 'blog', url, name: page.name, publisher: ref('organization'), isPartOf: ref('website'), ...details });
    if (type === 'BlogPosting') graph.push({ '@type': type, '@id': id + 'blogposting', url, headline: page.name, mainEntityOfPage: url, publisher: ref('organization'), isPartOf: ref('website'), ...(page.datePublished && { datePublished: page.datePublished }), ...details });
    if (type === 'BreadcrumbList' && page.breadcrumbs && page.breadcrumbs.length >= 2) graph.push({ '@type': type, '@id': id + 'breadcrumb', itemListElement: page.breadcrumbs.map((item, i) => ({ '@type': 'ListItem', position: i + 1, name: item.name, item: absolute(item.urlPath) })) });
    if (type === 'FAQPage' && page.faqs?.length) graph.push({ '@type': type, '@id': id + 'faq', mainEntity: page.faqs.filter(faq => faq.question.trim() && faq.answer.trim()).map(faq => ({ '@type': 'Question', name: faq.question, acceptedAnswer: { '@type': 'Answer', text: faq.answer } })) });
  }
  return graph.length ? { '@context': 'https://schema.org', '@graph': graph } : null;
}
export function sectionMeta(data: SectionData, areaKey?: string): PageMeta {
  const { section } = data;
  const area = areaKey ? data.categories[areaKey]! : null;
  const title = area ? area.label + ' | Hendrik Lampe' : section.title!;
  const description = area ? area.lead : section.description!;
  const path = '/' + section.key + '/' + (area && !section.single ? areaKey + '/' : '');
  const breadcrumbs = area ? [
    { name: 'Start', urlPath: '/' },
    ...(!section.single && section.crumb !== false ? [{ name: section.label, urlPath: '/' + section.key + '/' }] : []),
    { name: area.label, urlPath: path },
  ] : undefined;
  return { title, description, noindex: false, schema: buildSchema(['Organization', 'WebSite', 'WebPage', ...(area ? ['BreadcrumbList'] : [])], { urlPath: path, name: title, description, breadcrumbs }) };
}
export function blogMeta(post: BlogPost): PageMeta {
  const urlPath = '/blog/' + post.slug + '/';
  return { title: post.title + ' | Meine Website', description: post.description, noindex: false, schema: buildSchema(['WebSite', 'BlogPosting', 'BreadcrumbList'], { urlPath, name: post.title, description: post.description, datePublished: post.date, breadcrumbs: [{ name: 'Start', urlPath: '/' }, { name: 'Blog', urlPath: '/blog/' }, { name: post.title, urlPath }] }) };
}
