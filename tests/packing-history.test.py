import copy,io,json,sys,tempfile,unittest
from pathlib import Path
from fractions import Fraction as F
from unittest.mock import patch
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from packing_snapshots import SourceSnapshot
from review_packings import review
from build_packings import card,detail
DATA=json.loads((ROOT/'packing/data/results.json').read_text())
class HistoryTests(unittest.TestCase):
    def test_cached_sources_never_gain_new_retrieval_dates(self):
        with tempfile.TemporaryDirectory() as d:
            with patch('urllib.request.urlopen',return_value=io.BytesIO(b'source evidence')) as fetch:
                a=SourceSnapshot(d);a.fetch('source.txt','https://example.org/source');before=copy.deepcopy(a.metadata)
                b=SourceSnapshot(d);b.fetch('source.txt','https://example.org/source')
                self.assertEqual(before,b.metadata);self.assertEqual(fetch.call_count,1)
    def test_untracked_cache_cannot_be_relabelled(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'old.txt').write_text('old evidence')
            with self.assertRaises(ValueError):SourceSnapshot(d)
    def test_unchanged_checks_do_not_create_updates(self):
        candidate=copy.deepcopy(DATA)
        for r in candidate['results']:r['checked_at']='2026-10-20T12:00:00+00:00'
        self.assertEqual(review(DATA,candidate,{}),([],{}))
    def test_new_better_reference_retains_original_caption(self):
        candidate=copy.deepcopy(DATA);before=copy.deepcopy(DATA);r=candidate['results'][0];old=DATA['results'][0]
        r['checked_at']='2026-11-04T12:00:00+00:00';r['reference_exact']=str(F(r['value_exact'])-F('0.01'))
        report,updates=review(DATA,candidate,{})
        self.assertEqual(report[0]['change'],'later surpassed');self.assertEqual(DATA,before)
        self.assertIn('19 October 2026',card(old,updates[old['id']]))
        page=detail(old,updates[old['id']]);self.assertIn('Comparison recorded 19 October 2026',page);self.assertIn('Later update · 4 November 2026',page)
        self.assertEqual(page.count('Later update ·'),1)
        self.assertEqual(review(DATA,candidate,updates),([],{}))
    def test_missing_entries_do_not_refresh_or_publish(self):
        report,updates=review(DATA,{'results':[]},{})
        self.assertFalse(updates);self.assertEqual(len(report),108)
    def test_changed_geometry_is_rejected(self):
        candidate=copy.deepcopy(DATA);candidate['results'][0]['sha256']='different'
        with self.assertRaises(ValueError):review(DATA,candidate,{})
if __name__=='__main__':unittest.main()
