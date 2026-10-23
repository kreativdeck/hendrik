#!/usr/bin/env python3
"""Verify the current site against the PHP baseline plus approved content updates."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json, os, re, sys, hashlib, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
DEFAULT_ORIGIN='https://www.deinedomain.de'

def site_origin():
    """SITE_URL wie in src/config/site.ts: Umgebung vor .env-Dateien, sonst Original-Basis."""
    value=''
    for name in ['.env','.env.local','.env.production','.env.production.local']:
        file=ROOT/name
        if not file.is_file():continue
        for line in file.read_text(encoding='utf-8').splitlines():
            m=re.match(r'\s*(?:export\s+)?SITE_URL\s*=\s*(.*?)\s*$',line)
            if m:value=m.group(1).strip('"\'') or value
    return (os.environ.get('SITE_URL') or value or DEFAULT_ORIGIN).rstrip('/')

def localize(value,origin):
    """Ersetzt nur den Origin-Anfang von URL-Werten im Erwartungsobjekt; Texte bleiben unberührt."""
    if isinstance(value,dict):return {k:localize(v,origin) for k,v in value.items()}
    if isinstance(value,list):return [localize(v,origin) for v in value]
    if isinstance(value,str) and value.startswith(DEFAULT_ORIGIN) and value[len(DEFAULT_ORIGIN):len(DEFAULT_ORIGIN)+1] in ('','/','?','#'):
        return origin+value[len(DEFAULT_ORIGIN):]
    return value

class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.main=False;self.skip=0;self.tags=[];self.text=[];self.links=[];self.assets=[];self.images=[];self.galleries={};self.raw='';self.script=None;self.meta={};self.title='';self.in_title=False
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        a={k: ('' if v is None else v) for k,v in attrs}
        if tag=='main':self.main=True
        if tag=='title':self.in_title=True
        if tag=='meta':self.meta[a.get('name','')]=a.get('content','')
        if tag=='a' and a.get('href'): self.links.append(a['href'])
        if tag=='link' and a.get('href') and a.get('rel')!='preload':self.assets.append(a['href'])
        if tag in ['img','script'] and a.get('src'):self.assets.append(a['src'])
        if tag=='source' and a.get('srcset'):
            self.assets.extend(p.strip().split(' ')[0] for p in a['srcset'].split(','))
        if tag=='script':self.script=a;self.raw=''
        if self.main and tag=='img' and 'data-gallery-image' not in a:self.images.append({k:a[k] for k in ['src','alt','width','height','class'] if k in a})
        if self.main and tag not in ['script','source','picture','img','dialog'] and tag not in ['svg','path','title']:
            if not self.skip:self.tags.append(tag)
        if tag in ['script','svg','dialog']:self.skip+=1
    def handle_endtag(self,tag):
        if tag=='script' and self.script is not None:
            if self.script.get('type')=='application/ld+json':self.schema=json.loads(self.raw)
            if self.script.get('id')=='gallery-data':self.galleries=json.loads(self.raw)
            self.script=None
        if tag in ['script','svg','dialog']:self.skip-=1
        if tag=='main':self.main=False
        if tag=='title':self.in_title=False
    def handle_data(self,data):
        if self.script is not None:self.raw+=data
        if self.in_title and not self.skip:self.title+=data
        if self.main and not self.skip:self.text.append(data)
    def semantic(self):
        return {'title':self.title,'description':self.meta.get('description'),'robots':self.meta.get('robots'), 'text':re.sub(r'\s+',' ',' '.join(self.text)).strip(),'links':self.links,'images':self.images,'galleries':{k:{'label':v['label'],'images':[{kk:im[kk] for kk in ['src','alt','width','height']} for im in v['images']]} for k,v in self.galleries.items()},'schema':getattr(self,'schema',None)}

def target(key):return DIST/('404.html' if key=='404' else 'index.html' if key=='index' else key.removesuffix('/index')+'/index.html')

def verify():
    origin=site_origin()
    expected=localize(json.loads((ROOT/'tests/site-expectations.json').read_text(encoding='utf-8')),origin)
    failures=[];known_missing=set(expected['knownMissingLinks']);references=0
    for key,fixture in expected['pages'].items():
        file=target(key)
        if not file.exists():failures.append(f'{key}: Seite fehlt');continue
        page=Page(file.read_text(encoding='utf-8'));actual=page.semantic()
        for field,value in fixture.items():
            if actual[field]!=value:failures.append(f'{key}: Abweichung in {field}')
        for url in page.assets+page.links:
            parsed=urlsplit(url)
            if parsed.scheme or parsed.netloc or not parsed.path.startswith('/'):continue
            path=unquote(parsed.path);references+=1
            if path in known_missing:continue
            asset=DIST/path.lstrip('/')
            if path.endswith('/'):asset=asset/'index.html'
            if not asset.is_file():failures.append(f'{key}: Ziel fehlt: {path}')
    sitemap=ET.fromstring((DIST/'sitemap.xml').read_text(encoding='utf-8'))
    locs=[el.text for el in sitemap.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    paths=[urlsplit(loc).path for loc in locs]
    for loc in locs:
        if not loc.startswith(origin+'/'):failures.append(f'Sitemap: Origin weicht von {origin} ab: {loc}')
    robots=(DIST/'robots.txt').read_text(encoding='utf-8').splitlines()
    if f'Sitemap: {origin}/sitemap.xml' not in robots:failures.append(f'robots.txt: Sitemap-Zeile fehlt oder Origin weicht von {origin} ab')
    if sorted(paths)!=sorted(expected['sitemapPaths']):failures.append('Sitemap: URL-Menge weicht ab')
    for asset,sha in expected['originalAssets'].items():
        file=DIST/asset
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=sha:failures.append(f'Originaldatei verändert/fehlt: {asset}')
    api=DIST/'api/contact.php'
    if hashlib.sha256(api.read_bytes()).hexdigest()!=expected['apiSha256']:failures.append('Kontakt-API verändert')
    if failures:
        print('\n'.join(failures));sys.exit(1)
    print(f'Origin: {origin}'+(' (Original-Basis)' if origin==DEFAULT_ORIGIN else ''))
    print(f'OK: {len(expected["pages"])} Seiten, Inhalte, SEO/JSON-LD, Navigation, Galeriedaten und {references} lokale Referenzen.')
    print(f'OK: {len(paths)} Sitemap-URLs, {len(expected["originalAssets"])} unveränderte Original-Assets, Kontakt-API.')
    print('Bekannte Quelllücken: '+', '.join(sorted(known_missing)))
if __name__=='__main__':verify()
