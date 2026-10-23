/// <reference types="astro/client" />
declare module 'virtual:hendrik-images' {
  interface SiteImage {
    url: string;
    width: number | null;
    height: number | null;
    variants: { avif: Record<string, string>; webp: Record<string, string> };
  }
  const images: Record<string, SiteImage>;
  export default images;
}
