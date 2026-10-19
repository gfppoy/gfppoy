"""Audit a retained export against freshly fetched, pinned primary sources.
Usage: python3 scripts/audit_packings.py EXPORT.csv EXPORT.zip --cache .packing-work/sources/NEW-CHECK --output .packing-work/checks/NEW-CHECK
Use a new cache for a new check. Reusing a cache preserves its original timestamps.
This writes a private review candidate, never the public original comparisons.
"""
import argparse, concurrent.futures, csv, datetime, hashlib, json, re, ssl, urllib.request, zipfile
from fractions import Fraction as F
from pathlib import Path
from packing_snapshots import SourceSnapshot

ROOT = Path(__file__).resolve().parents[1]

def cert_header(data):
    lines = [s for s in data.decode().splitlines() if s.strip() and not s.startswith('#')]
    n, side = lines[0].split()
    assert len(lines) == int(n) + 1
    return int(n), F(side)

def audit(csv_path, zip_path, cache, output):
    output=Path(output).resolve()
    if output.is_relative_to((ROOT/'packing').resolve()):
        raise ValueError('Audit output must be outside the public packing directory')
    if output.exists():raise ValueError('Use a new output directory; retained checks are not overwritten')
    ctx = ssl.create_default_context(cafile='/etc/ssl/cert.pem')
    snapshot=SourceSnapshot(cache,ctx)
    fetch=snapshot.fetch
    checked=snapshot.metadata['started_at']
    # Resolve HEAD once; all certificate requests below use immutable commits.
    refs = {}
    for key, owner in [('repo', 'franciscouzo'), ('evan', 'evand')]:
        sha = json.loads(fetch(key+'.json', f'https://api.github.com/repos/{owner}/square-packing/commits/HEAD'))['sha']
        tree = json.loads(fetch(key+'-tree.json', f'https://api.github.com/repos/{owner}/square-packing/git/trees/{sha}?recursive=1'))
        assert not tree.get('truncated'), 'Incomplete source tree'
        refs[key] = (owner, sha, {x['path'] for x in tree['tree']})
    rows = list(csv.DictReader(open(csv_path)))
    needed = {int(r['n']) for r in rows if r['family'] == 'squares_in_square'}
    owner, sha, tree = refs['repo']
    paths = [p for p in tree if (m := re.fullmatch(r'certificates/(?:best/)?n(\d+)\.cert', p)) and int(m[1]) in needed]
    def download(p):
        url = f'https://raw.githubusercontent.com/{owner}/square-packing/{sha}/{p}'
        data = fetch('repo/'+p, url)
        n, side = cert_header(data)
        return n, side, url, hashlib.sha256(data).hexdigest()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        certificates = list(pool.map(download, paths))
    live = json.loads(fetch('evan-live-index.json', 'https://evand.github.io/square-packing/data/index.json'))['records']
    radius_url = 'https://packomania.com/csq/txt/radius.txt'
    radius_data = fetch('radius.txt', radius_url)
    radii = {int(a): b for a, b in re.findall(rb'(?m)^\s*(\d+)\s+([0-9.]+)\s*$', radius_data)}
    out = output
    for d in ['coordinates', 'data']:
        (out/d).mkdir(parents=True, exist_ok=True)
    (out/'data'/f'packomania-radius-{checked[:10]}.txt').write_bytes(radius_data)
    results = []
    with zipfile.ZipFile(zip_path) as z:
        for r in rows:
            n = int(r['n']); square = r['family'] == 'squares_in_square'
            kind = 'squares' if square else 'circles'; key = f'{kind}-{n}'
            blob = z.read(r['geometry'])
            digest = hashlib.sha256(blob).hexdigest()
            assert digest == r['sha256'], f'{key}: coordinate hash mismatch'
            own = F(r['objective_exact'])
            sources = []
            if square:
                gn, side = cert_header(blob)
                assert gn == n and side == own
                for cn, v, url, h in certificates:
                    if cn == n:
                        sources.append({'name': 'Francisco Couzo’s square-packing catalogue', 'value_exact': str(v), 'url': url, 'sha256': h, 'precision': 'exact rational certificate'})
                # The public viewer has additional data for small cases. Compare it too.
                ev = live.get(str(n), {})
                if ev.get('best_s'):
                    sources.append({'name': 'Evan Daniel’s public viewer', 'value_exact': str(F(ev['best_s'])), 'url': r['public_case_url'], 'precision': 'displayed decimal'})
                assert sources, f'{key}: no current source'
                source = min(sources, key=lambda x: F(x['value_exact']))
            else:
                geom = json.loads(blob)['circles']
                assert len(geom) == n and all(F(c['r']) == own for c in geom)
                value = radii[n].decode()
                coords = fetch('circles/'+str(n)+'.txt', r['public_coordinates_url'])
                listed = [s.split() for s in coords.decode().splitlines() if s.strip() and not s.startswith('#')]
                assert len(listed) == n and all(F(s[3]) == F(value) for s in listed)
                (out/'data'/f'packomania-{n}-{checked[:10]}.txt').write_bytes(coords)
                source = {'name': 'Packomania', 'value_exact': str(F(value)), 'url': radius_url, 'precision': 'printed radius (12 decimal places)', 'sha256': hashlib.sha256(radius_data).hexdigest(), 'coordinates_url': r['public_coordinates_url'], 'coordinates_sha256': hashlib.sha256(coords).hexdigest()}
                sources = [source]
            ref = F(source['value_exact'])
            gain = ref-own if square else own-ref
            # No positive record claim for already-attributed, rounding-scale differences.
            status = 'improved' if gain > 0 else ('superseded' if gain < 0 else 'equal')
            if square and 0 < gain < F('1e-8'): status = 'precision-scale'
            if not square and 0 < gain <= F('0.0000000000005'): status = 'precision-scale'
            prov_path = r['provenance'] if r['provenance'] in z.namelist() else r['provenance']+'/provenance.json'
            prov = json.loads(z.read(prov_path))
            if prov.get('record', {}).get('base_n'):
                r['dependent'] = 'True'
                r['method_credit'] = prov['record'].get('construction') or r['method_credit']
            if square:
                receipt_path = r['geometry'].rsplit('/', 1)[0]+'/certificate.json'
                receipt = json.loads(z.read(receipt_path)) if receipt_path in z.namelist() else prov.get('certificate', {})
                if receipt: assert receipt.get('valid') is not False, f'{key}: failed retained receipt'
            else:
                receipt = json.loads(z.read(r['provenance']+'/certificate.json'))
            ext = 'cert' if square else 'json'
            (out/'coordinates'/f'{key}.{ext}').write_bytes(blob)
            results.append({'id': key, 'kind': kind, 'n': n, 'value_exact': str(own), 'value': float(own), 'reference_exact': str(ref), 'reference': float(ref), 'gain_absolute_exact': str(gain), 'gain_percent': float(gain/ref*100), 'status': status, 'checked_at': checked, 'source': source, 'sources_checked': sources, 'geometry': f'coordinates/{key}.{ext}', 'sha256': digest, 'problem_url': r['problem_url'], 'viewer_url': r['public_case_url'], 'historical_reference_exact': r['reference_exact'], 'historical_comparison_date': r['reference_snapshot'], 'historical_source_url': r['reference_source_url'], 'method_credit': r['method_credit'], 'dependency': r['dependent'], 'classification': r['classification'], 'recognition': r['recognition'], 'parent_n': prov.get('parent_construction', {}).get('parent_n') or prov.get('record', {}).get('base_n'), 'retained_verification': r['verification'], 'verification_receipt': receipt})
    manifest = {'source_retrievals': snapshot.metadata, 'checked_at': checked, 'scope': 'Source-specific numerical comparisons; not worldwide priority or optimality. Square certificates from both certificates/ and certificates/best/ at the pinned HEAD, plus the public Evan Daniel viewer where it has a matching entry. Circle printed table and coordinate radii checked for all eight cases. Retained coordinate hashes and objective values checked; export verification receipts are historical, not a new exact feasibility replay.', 'square_commit': refs['repo'][1], 'evan_commit': refs['evan'][1], 'results': results}
    (out/'data/results.json').write_text(json.dumps(manifest, indent=2)+'\n')
    fields=['id','kind','n','value_exact','reference_exact','gain_percent','status','checked_at','geometry','sha256']
    with (out/'data/results.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r[k] for k in fields} for r in results)
    from collections import Counter
    print('Audited',len(results),dict(Counter(r['status'] for r in results)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('csv');p.add_argument('zip');p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();audit(a.csv,a.zip,a.cache,a.output)
