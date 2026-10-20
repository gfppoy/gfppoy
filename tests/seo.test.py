"""Verify the deployed search metadata and sitemap, after build_site.py."""
import json, struct, unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / '_site'
BASE = 'https://dariusmuglich.com'

class Head(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.meta, self.canonicals, self.title, self.schemas = {}, [], '', []
        self.in_title = self.in_schema = False
        self.feed(path.read_text())
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta': self.meta[a.get('name', a.get('property'))] = a.get('content')
        if tag == 'link' and a.get('rel') == 'canonical': self.canonicals.append(a['href'])
        if tag == 'title': self.in_title = True
        if tag == 'script' and a.get('type') == 'application/ld+json': self.in_schema = True
    def handle_endtag(self, tag):
        if tag == 'title': self.in_title = False
        if tag == 'script': self.in_schema = False
    def handle_data(self, data):
        if self.in_title: self.title += data
        if self.in_schema and data.strip(): self.schemas.append(json.loads(data))

class SEOTests(unittest.TestCase):
    def test_unique_metadata_and_valid_share_images(self):
        titles, descriptions = set(), set()
        for page in ROOT.rglob('*.html'):
            h = Head(page)
            self.assertEqual(len(h.canonicals), 1, page)
            self.assertTrue(h.canonicals[0].startswith(BASE+'/'))
            self.assertTrue(h.title and h.meta.get('description'), page)
            self.assertNotIn(h.title, titles); titles.add(h.title)
            self.assertNotIn(h.meta['description'], descriptions); descriptions.add(h.meta['description'])
            if 'noindex' in h.meta.get('robots', ''): continue
            self.assertEqual(h.meta['og:url'], h.canonicals[0])
            self.assertEqual(h.meta['og:title'], h.title)
            image = ROOT / urlsplit(h.meta['og:image']).path.lstrip('/')
            data = image.read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('>II', data[16:24]), (1200,630))
    def test_sitemap_matches_indexable_pages(self):
        urls = [e.text for e in ET.parse(ROOT/'sitemap.xml').findall('.//{*}loc')]
        expected = {BASE+'/cv.pdf'}
        for page in ROOT.rglob('*.html'):
            h = Head(page)
            if 'noindex' not in h.meta.get('robots',''): expected.add(h.canonicals[0])
        self.assertEqual(set(urls), expected)
        self.assertEqual(len(urls), len(expected))
        self.assertNotIn(BASE+'/writing/', urls)
        for url in urls:
            path = ROOT / urlsplit(url).path.lstrip('/')
            if path.is_dir(): path /= 'index.html'
            self.assertTrue(path.is_file(), url)
        self.assertIn('Sitemap: '+BASE+'/sitemap.xml', (ROOT/'robots.txt').read_text())
    def test_profile_is_consistent_and_does_not_expose_email(self):
        graph = Head(ROOT/'index.html').schemas[0]['@graph']
        site, profile = graph
        self.assertEqual(site['@type'], 'WebSite')
        self.assertEqual(profile['@type'], 'ProfilePage')
        person = profile['mainEntity']
        self.assertEqual(person['name'], 'Darius Muglich')
        self.assertEqual(person['affiliation']['name'], 'University of Oxford')
        self.assertNotIn('email', person)

if __name__ == '__main__': unittest.main()
