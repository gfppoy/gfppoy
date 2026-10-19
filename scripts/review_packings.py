"""Review a new audit; publish only explicitly selected later-surpassed notices.
python3 scripts/review_packings.py .packing-work/checks/NEW-CHECK/data/results.json
python3 scripts/review_packings.py CHECK.json --publish squares-328 circles-577
Then run build_packings.py. Neither command alters the original comparisons.
All observations stay in private check directories; the site holds one latest notice.
"""
import argparse,json
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def review(original,candidate,updates):
    incoming={r['id']:r for r in candidate['results']};report=[];proposed={}
    for old in original['results']:
        key=old['id'];new=incoming.get(key)
        if not new:
            report.append({'id':key,'change':'missing from check; existing comparison retained'});continue
        if new['sha256']!=old['sha256'] or F(new['value_exact'])!=F(old['value_exact']):
            raise ValueError('Arrangement identity changed: '+key)
        if new['checked_at']<=old['checked_at']:continue
        prior=updates.get(key,old)
        if new['checked_at']<=prior['checked_at']:continue
        if F(new['reference_exact'])==F(prior['reference_exact']):continue
        square=old['kind']=='squares';threshold=F('1e-8') if square else F('0.0000000000005')
        gap=F(new['reference_exact'])-F(old['value_exact']) if square else F(old['value_exact'])-F(new['reference_exact'])
        surpassed=gap < -threshold
        report.append({'id':key,'change':'later surpassed' if surpassed else 'source value changed; original comparison retained','old_reference':prior['reference_exact'],'new_reference':new['reference_exact'],'observed_at':new['checked_at']})
        if surpassed:
            proposed[key]={k:new[k] for k in ['checked_at','reference_exact','source']}
            proposed[key]['reference']=float(F(new['reference_exact']))
    return report,proposed

def main():
    p=argparse.ArgumentParser();p.add_argument('check',type=Path);p.add_argument('--publish',nargs='+',default=[]);a=p.parse_args()
    original=json.loads((ROOT/'packing/data/results.json').read_text());path=ROOT/'packing/data/updates.json';updates=json.loads(path.read_text())
    report,proposed=review(original,json.loads(a.check.read_text()),updates)
    print(json.dumps({'changes':report,'available_updates':list(proposed)},indent=2))
    if a.publish:
        if any(k not in proposed for k in a.publish):raise ValueError('Only reviewed, newly superseding observations can be published')
        archive=ROOT/'.packing-work/published-updates';archive.mkdir(parents=True,exist_ok=True)
        import hashlib
        before=path.read_bytes();backup=archive/(hashlib.sha256(before).hexdigest()+'.json')
        if not backup.exists():backup.write_bytes(before)
        updates.update({k:proposed[k] for k in a.publish})
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(updates,indent=2)+'\n');temp.replace(path)
        print('Selected later updates saved. Run python3 scripts/build_packings.py to rebuild.')
if __name__=='__main__':main()
