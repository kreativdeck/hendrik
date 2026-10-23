import imageManifest from 'virtual:hendrik-images';
export interface Category {
  label: string;
  lead: string;
  folder: string;
  cover: string;
  /** Optional anderes Bild für die Kachel in der Bereichsübersicht; die Detailseite behält `cover`. */
  overviewCover?: string;
  text?: string;
  tint?: string;
  introTitle?: string;
  intro?: string | string[];
  masonry?: boolean;
  fit?: string;
  item?: string;
  exclude?: string[];
}
export interface SectionData {
  section: { key: string; label: string; title?: string; description?: string; lead?: string; single?: boolean; crumb?: boolean };
  categories: Record<string, Category>;
  descriptions: Record<string, string>;
}
// PHP natsort compares numeric runs; keep leading-zero variants in their original order.
const naturalCompare = (a: string, b: string) => {
  const aa = a.match(/\d+|\D+/g) ?? [];
  const bb = b.match(/\d+|\D+/g) ?? [];
  for (let i = 0; i < Math.min(aa.length, bb.length); i++) {
    const x = aa[i]!; const y = bb[i]!;
    if (x === y) continue;
    if (/^\d/.test(x) && /^\d/.test(y)) {
      // PHP compares runs starting with zero lexically.
      if (x.startsWith('0') || y.startsWith('0')) return x < y ? -1 : 1;
      const diff = Number(x) - Number(y);
      if (diff) return diff;
    } else return x < y ? -1 : 1;
  }
  return aa.length - bb.length;
};
export function galleryFor(data: SectionData, key: string) {
  const category = data.categories[key];
  if (!category) throw new Error(`Kategorie fehlt: ${key}`);
  const images = Object.keys(imageManifest)
    .filter((source) => source.startsWith(category.folder + '/') && source.toLowerCase().endsWith('.jpg'))
    .filter((source) => !category.exclude?.includes(source.split('/').at(-1)!))
    .sort(naturalCompare)
    .map((source) => {
      const image = imageManifest[source]!;
      const alt = data.descriptions[source.split('/').at(-1)!];
      if (!alt) throw new Error(`Bildbeschreibung fehlt: ${source}`);
      return { source, src: image.url, width: image.width, height: image.height, alt };
    });
  if (!images.length) throw new Error(`Galerie ist leer: ${key}`);
  return { label: category.label, images };
}
export type Gallery = ReturnType<typeof galleryFor>;
