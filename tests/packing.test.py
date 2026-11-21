"""Consistency checks for the published comparisons and generated diagrams."""
import hashlib, json, unittest, xml.etree.ElementTree as ET
from fractions import Fraction as F
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'packing/data/results.json').read_text())
class Links(HTMLParser):
    def __init__(self): super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        self.links += [v for k,v in attrs if k in ('href','src')]
class PackingTests(unittest.TestCase):
    def test_every_comparison_recalculates_from_exact_values(self):
        self.assertEqual(len(DATA['results']),142)
        for r in DATA['results']:
            own,ref=F(r['value_exact']),F(r['reference_exact'])
            gain=ref-own if r['kind']=='squares' else own-ref
            self.assertEqual(gain,F(r['gain_absolute_exact']),r['id'])
            self.assertAlmostEqual(float(gain/ref*100),r['gain_percent'],places=12)
            if r['status']=='improved':self.assertGreater(gain,0)
            if r['status']=='superseded':self.assertLess(gain,0)
            if r['kind']=='squares':self.assertEqual(ref,min(F(s['value_exact']) for s in r['sources_checked']))
    def test_coordinates_and_drawings_have_expected_identity_and_counts(self):
        for r in DATA['results']:
            raw=(ROOT/'packing'/r['geometry']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),r['sha256'])
            svg=ET.parse(ROOT/'packing/drawings'/f'{r["id"]}.svg')
            tag='polygon' if r['kind']=='squares' else 'circle'
            self.assertEqual(len(svg.findall('.//{http://www.w3.org/2000/svg}'+tag)),r['n'])
            if r['kind']=='squares':
                lines=[l for l in raw.decode().splitlines() if l.strip() and not l.startswith('#')]
                self.assertEqual(int(lines[0].split()[0]),r['n']);self.assertEqual(len(lines)-1,r['n'])
                self.assertEqual(F(lines[0].split()[1]),F(r['value_exact']))
            else:
                circles=json.loads(raw)['circles'];self.assertEqual(len(circles),r['n'])
                for c in circles:
                    radius=F(c['r']) if isinstance(c,dict) else F(c[2],json.loads(raw)['scale'])
                    self.assertEqual(radius,F(r['value_exact']))
    def test_internal_links_resolve(self):
        for page in (ROOT/'packing').glob('*.html'):
            p=Links();p.feed(page.read_text())
            for url in p.links:
                if url.startswith(('https:','http:','#')):continue
                target=(page.parent/url.split('?')[0].split('#')[0]).resolve()
                self.assertTrue(target.exists(),f'{page.name}: {url}')
    def test_featured_results_are_current_source_improvements(self):
        import sys
        sys.dont_write_bytecode = True
        sys.path.insert(0,str(ROOT/'scripts'))
        from build_packings import ranked_results, card, detail, checked_date
        updates=json.loads((ROOT/'packing/data/updates.json').read_text())
        rows=ranked_results(DATA['results'],updates)
        featured=rows[:6]
        index=(ROOT/'packing/index.html').read_text()
        self.assertEqual(index.count('class="packing-card"'),6)
        self.assertEqual([r['id'] in updates for r in rows],sorted(r['id'] in updates for r in rows))
        for r in featured:
            self.assertIn('drawings/'+r['id']+'.svg',index)
            self.assertEqual(r.get('standing'),'material lead')
            self.assertTrue(r['checked_at'].startswith('2026-11-21'))
            self.assertIn('larger radius' if r['kind']=='circles' else 'smaller container side',card(r))
            self.assertIn(r['source']['url'],card(r))
            self.assertIn('Comparison recorded '+checked_date(r),detail(r))
        self.assertNotIn('class="collection-note"',(ROOT/'packing/index.html').read_text())

    def test_display_precision_is_consistent(self):
        import sys
        sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'scripts'))
        from build_packings import value,percent
        self.assertEqual(value(18.6),'18.600000')
        self.assertEqual(value(.021930216134946),'0.021930216')
        self.assertEqual(percent(.106092593705),'0.106')
        self.assertEqual(percent(.0496153727),'0.0496')
        self.assertEqual(percent(.1),'0.100')
        self.assertEqual(value(1.23456509464e-5),'1.2345651e-05')

    def test_excluded_results_are_not_public(self):
        omitted=['squares-229','squares-458','squares-501','squares-546','squares-547','squares-549','squares-555','squares-653']
        for key in omitted:
            self.assertFalse((ROOT/'packing'/f'{key}.html').exists())
            self.assertFalse((ROOT/'packing/drawings'/f'{key}.svg').exists())
            self.assertFalse((ROOT/'packing/coordinates'/f'{key}.cert').exists())
        import csv
        self.assertEqual(len(list(csv.DictReader((ROOT/'packing/data/results.csv').read_text().splitlines()))),142)

if __name__=='__main__':unittest.main()
