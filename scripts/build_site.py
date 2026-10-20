"""Stage only public website assets for GitHub Pages. No network dependencies."""
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '_site'
FILES = ['.nojekyll', 'CNAME', 'index.html', 'style.css', 'favicon.svg',
         'cv.pdf', 'reveal.js', 'contact-config.js', 'contact.js',
         'growth-physics.js', 'animation.js', 'robots.txt']
FOLDERS = ['for-fun', 'writing', 'packing', 'assets']
EXTENSIONS = {'.html', '.css', '.svg', '.json', '.csv', '.txt', '.cert', '.png'}

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.canonical = None
        self.noindex = False
    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'link' and attributes.get('rel') == 'canonical':
            self.canonical = attributes.get('href')
        if tag == 'meta' and attributes.get('name') == 'robots':
            self.noindex = 'noindex' in attributes.get('content', '').lower()
        self.links.extend(value for key, value in attrs
                          if key in ('href', 'src') and value)

def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for name in FILES:
        shutil.copy2(ROOT / name, OUT / name)
    for folder in FOLDERS:
        for source in sorted((ROOT / folder).rglob('*')):
            if source.is_symlink():
                raise ValueError(f'Symlink is not a site asset: {source}')
            if not source.is_file() or source.suffix not in EXTENSIONS:
                continue
            if any(part.startswith('.') for part in source.relative_to(ROOT).parts):
                continue
            target = OUT / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    missing = []
    canonical_urls = []
    for page in OUT.rglob('*.html'):
        parser = Links()
        parser.feed(page.read_text())
        if not parser.noindex:
            if not parser.canonical or not parser.canonical.startswith('https://dariusmuglich.com/'):
                raise ValueError(f'Missing production canonical URL: {page}')
            canonical_urls.append(parser.canonical)
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme or url.netloc or not url.path:
                continue
            target = (OUT / unquote(url.path).lstrip('/') if url.path.startswith('/')
                      else page.parent / unquote(url.path)).resolve()
            if not target.is_relative_to(OUT.resolve()) or not target.exists():
                missing.append(f'{page.relative_to(OUT)}: {link}')
    if missing:
        raise ValueError('Missing site assets:\n' + '\n'.join(missing))
    canonical_urls.append('https://dariusmuglich.com/cv.pdf')
    if len(canonical_urls) != len(set(canonical_urls)):
        raise ValueError('Duplicate canonical URLs in sitemap')
    namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    ET.register_namespace('', namespace)
    sitemap = ET.Element(f'{{{namespace}}}urlset')
    for url in sorted(canonical_urls):
        ET.SubElement(ET.SubElement(sitemap, f'{{{namespace}}}url'), f'{{{namespace}}}loc').text = url
    ET.indent(sitemap)
    ET.ElementTree(sitemap).write(OUT / 'sitemap.xml', encoding='utf-8', xml_declaration=True)
    print(f'Sitemap contains {len(canonical_urls)} canonical pages and documents.')
    print(f'Staged {sum(p.is_file() for p in OUT.rglob("*"))} public files; local links verified.')

if __name__ == '__main__':
    build()
