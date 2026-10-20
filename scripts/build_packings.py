"""Build the static gallery from audited data and untouched coordinate files.
Run: python3 scripts/build_packings.py
No network requests, optimizer or external dependencies.
"""
import csv, html, json
from datetime import datetime
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]/'packing'
# Highest-gain distinct constructions: 548 is a border extension of 503.
FEATURED = ['squares-328','squares-503','squares-757','circles-577','circles-503','circles-531']
E = html.escape

def external(url, label):
    return f'<a href="{E(url, quote=True)}" target="_blank" rel="noopener">{E(label)}</a>'

def title(r): return f'{r["n"]} unit squares in a square' if r["kind"] == "squares" else f'{r["n"]} circles in a unit square'
# Dimensions use eight significant figures; percentage improvements use three.
# Keep trailing zeroes: they communicate the same precision in every context.
def value(v): return format(v, '#.8g')
def percent(v): return format(abs(v), '#.3g')
def comparison(r):
    if r['status']=='improved':
        return f'{percent(r["gain_percent"])}% {"smaller container side" if r["kind"]=="squares" else "larger radius"}'
    if r['status']=='superseded': return 'Public source has a better value'
    if r['status']=='precision-scale': return 'Rounding-scale difference; no improvement claimed'
    return 'Matches the reference value'

def checked_date(r):
    return datetime.fromisoformat(r['checked_at']).strftime('%d %B %Y').lstrip('0')

def source_label(r):
    return 'Francisco Couzo’s catalogue' if r['kind']=='squares' else 'Packomania'

def comparison_link(r):
    link=external(r['source']['url'], source_label(r))
    if r['status']=='improved':
        return f'{comparison(r)} than the value listed {"in" if r["kind"]=="squares" else "on"} {link} on {checked_date(r)}.'
    if r['status']=='superseded': return f'{link} lists a better value.'
    if r['status']=='precision-scale': return f'Rounding-scale difference from {link}; no improvement claimed.'
    return f'Matches the value listed by {link}.'

def draw(r):
    raw=(ROOT/r['geometry']).read_text();parts=[]
    if r['kind']=='squares':
        lines=[l for l in raw.splitlines() if l.strip() and not l.startswith('#')]
        n,side=lines[0].split();side=float(F(side));assert int(n)==r['n']
        for line in lines[1:]:
            x,y,t=map(F,line.split());u=(1-t*t)/(1+t*t);v=2*t/(1+t*t)
            corners=[(float(x+(a*u-b*v)/2)/side*1000,1000-float(y+(a*v+b*u)/2)/side*1000) for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]]
            assert all(-1e-7<=p<=1000+1e-7 for xy in corners for p in xy), r['id']
            points=' '.join(f'{x:.8f},{y:.8f}' for x,y in corners)
            parts.append(f'<polygon points="{points}"/>')
        fill,stroke='#d4ddd0','#637d69'
    else:
        circles=json.loads(raw)['circles'];assert len(circles)==r['n']
        for c in circles:
            x,y,rad=[float(F(c[k]))*1000 for k in ['x','y','r']]
            assert min(x-rad,y-rad)>=-1e-7 and max(x+rad,y+rad)<=1000+1e-7
            parts.append(f'<circle cx="{x:.8f}" cy="{1000-y:.8f}" r="{rad:.8f}"/>')
        fill,stroke='#d3dce0','#657f8a'
    assert len(parts)==r['n']
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-8 -8 1016 1016" role="img" aria-labelledby="title desc">
<title id="title">{E(title(r))}</title><desc id="desc">Arrangement drawn from the retained coordinates. {E(comparison(r))}, against the cited source checked on {r['checked_at'][:10]}. Rendering is rounded; the coordinate download preserves exact values.</desc>
<rect x="0" y="0" width="1000" height="1000" fill="#f7f7f2" stroke="#818a7c" stroke-width="1.8"/>
<g fill="{fill}" stroke="{stroke}" stroke-width="0.85" stroke-linejoin="round">{''.join(parts)}</g></svg>'''
    (ROOT/'drawings'/f'{r["id"]}.svg').write_text(svg)

def shell(name, body, description, page='index.html'):
    url = 'https://dariusmuglich.com/packing/' + ('' if page == 'index.html' else page)
    social = f'''<meta property="og:type" content="website"><meta property="og:site_name" content="Darius Muglich"><meta property="og:title" content="{E(name,quote=True)} — Darius Muglich"><meta property="og:description" content="{E(description,quote=True)}"><meta property="og:url" content="{url}"><meta property="og:image" content="https://dariusmuglich.com/assets/packing-preview.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Packing problems by Darius Muglich: 328 unit squares in a square"><meta name="twitter:card" content="summary_large_image">'''
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light"><meta name="theme-color" content="#f7f7f2"><meta name="description" content="{E(description,quote=True)}"><title>{E(name)} — Darius Muglich</title><link rel="icon" href="../favicon.svg?v=dm-1" type="image/svg+xml"><link rel="canonical" href="https://dariusmuglich.com/packing/{'' if page=='index.html' else page}"><link rel="stylesheet" href="../style.css?v=helvetica-2"><link rel="stylesheet" href="packing.css?v=helvetica-2">{social}</head>
<body class="packing-page"><a class="skip-link" href="#main">Skip to content</a><div class="page"><header class="site-header"><a class="wordmark" href="../">Darius Muglich</a><nav class="header-links" aria-label="Page navigation"><a href="{'../for-fun/' if page=='index.html' else './'}"><span aria-hidden="true">←</span> {'For fun' if page=='index.html' else 'All packings'}</a></nav></header><main id="main">{body}</main><footer class="site-footer"><span>Packing experiments · October 2026</span><a href="../">← Home</a></footer></div></body></html>'''

def update_note(r, update, compact=False):
    if not update:
        return ''
    date=checked_date(update)
    if compact:
        return f'<p class="packing-update-label"><a href="{r["id"]}.html#later-update">Later surpassed</a></p>'
    link=external(update['source']['url'], update['source']['name'])
    return f'<aside class="packing-update" id="later-update" aria-label="Later comparison"><p class="eyebrow">Later update · {date}</p><p>A better public packing was listed by {date}: {value(update["reference"])} ({"container side" if r["kind"]=="squares" else "radius"}). {link}</p></aside>'

def card(r, update=None):
    objective='Container side' if r['kind']=='squares' else 'Radius'
    priority = 'high' if r['id'] == FEATURED[0] else 'auto'
    return f'''<article class="packing-card"><a class="drawing-link" href="{r['id']}.html" aria-label="View {E(title(r))} and comparison details"><img src="drawings/{r['id']}.svg" width="1016" height="1016" loading="eager" fetchpriority="{priority}" alt="{E(title(r))}"/></a><h2><a href="{r['id']}.html">{E(title(r))}</a></h2><p class="packing-value">{objective} <span>≈ {value(r['value'])}</span></p><p class="packing-comparison">{comparison_link(r)}</p>{update_note(r, update, compact=True)}</article>'''

def detail(r, update=None):
    square=r['kind']=='squares';label='Container side' if square else 'Common radius'
    brief='Unit squares; smaller container side is better.' if square else 'Equal circles in a unit square; larger radius is better.'
    date=checked_date(r)
    notice='Compared with the exact certificate linked below.' if square else 'Compared with Packomania’s printed radius, which is rounded to 12 decimal places. The published coordinate file reports the same radius; its centres use a translated unit-square frame.'
    if r['status']=='precision-scale':notice+=' This case was already publicly attributed to Evan Daniel; no new result is claimed.'
    credit = ''
    if square:
        credit = 'Built using ' + external('https://github.com/franciscouzo/square-packing', 'Francisco Couzo’s square-packing solver') + '.'
    if r['parent_n']:
        credit += f' Derived from a packing of {r["parent_n"]} squares.'
    credit = f'<p class="packing-date packing-credit">{credit}</p>' if credit else ''
    body=f'''<div class="packing-intro"><p class="eyebrow">Packing problems</p><h1>{E(title(r))}</h1><p>{brief}</p></div>
<div class="packing-detail"><a class="drawing-link" href="drawings/{r['id']}.svg" aria-label="Open full-size diagram"><img src="drawings/{r['id']}.svg" width="1016" height="1016" fetchpriority="high" alt="{E(title(r))}"/></a><div class="packing-facts"><p class="eyebrow">This arrangement</p><p class="detail-value">{value(r['value'])}</p><p class="packing-date">{label} · 8 significant figures</p><p class="detail-comparison">{comparison_link(r)}</p><table class="original-comparison"><caption>Comparison recorded {date}</caption><thead><tr><th scope="col">Arrangement</th><th scope="col">{label}</th></tr></thead><tbody><tr><th scope="row">This arrangement</th><td>{value(r['value'])}</td></tr><tr><th scope="row">{external(r['source']['url'], source_label(r))}</th><td>{value(r['reference'])}</td></tr></tbody></table><p class="packing-date">Difference: {value(abs(float(F(r['gain_absolute_exact']))))} {'smaller side' if square else 'larger radius'}.</p><p class="packing-date">{notice}</p>{update_note(r, update)}<div class="packing-links">{external(r['source']['url'],'Comparison source')}{external(r['problem_url'],'Problem catalogue')}<a href="{r['geometry']}" download>Coordinates</a></div>{credit}</div></div>'''
    return shell(title(r),body,f'{title(r)} by Darius Muglich. Diagram, exact coordinates and a dated comparison with {source_label(r)}.',r['id']+'.html')

def build():
    manifest=json.loads((ROOT/'data/results.json').read_text());rows=manifest['results'];byid={r['id']:r for r in rows}
    updates=json.loads((ROOT/'data/updates.json').read_text())
    assert all(r['status']=='improved' for r in rows), 'Public collection requires an original improvement comparison'
    square_count=sum(r['kind']=='squares' for r in rows); circle_count=len(rows)-square_count
    (ROOT/'drawings').mkdir(exist_ok=True)
    for r in rows:
        draw(r);(ROOT/(r['id']+'.html')).write_text(detail(r, updates.get(r['id'])))
    assert all(byid[k]['status']=='improved' for k in FEATURED), 'Recurate featured results after a source update'
    groups=[]
    for kind, heading in [('squares','Unit squares in a square'), ('circles','Circles in a unit square')]:
        chosen=sorted([byid[k] for k in FEATURED if byid[k]['kind']==kind], key=lambda r:r['gain_percent'], reverse=True)
        cards=''.join(card(r, updates.get(r['id'])) for r in chosen)
        groups.append(f'<section class="packing-group" aria-labelledby="{kind}-heading"><h2 class="packing-group-title" id="{kind}-heading">{heading}</h2><div class="packing-gallery">{cards}</div></section>')
    gallery=''.join(groups)
    table=''
    for r in rows:
        status=comparison(r)
        later=f'<br><a class="packing-update-label" href="{r["id"]}.html#later-update">Later surpassed</a>' if r['id'] in updates else ''
        table+=f'<tr><th scope="row"><a href="{r["id"]}.html">{r["n"]} {r["kind"]}</a></th><td>{value(r["value"])}</td><td>{E(status)}<span class="packing-date reference-date">{checked_date(r)}</span>{later}</td></tr>'
    date=manifest['checked_at'][:10]
    body=f'''<div class="packing-intro"><h1>Packing problems</h1><p>Fitting shapes into as little space as possible. A hobby and a testbed for mixed discrete–continuous optimization. Each packing below improves on the best value listed in its linked public catalogue on 19 October 2026.</p><p class="packing-date">Squares: minimize the container side. Circles: maximize the radius in a unit square.</p></div>{gallery}
<details class="packing-catalogue" id="catalogue"><summary>All {len(rows)} arrangements <span>{square_count} square packings · {circle_count} circle packings</span></summary><div class="table-scroll" tabindex="0" role="region" aria-label="All packing results"><table><thead><tr><th scope="col">Arrangement</th><th scope="col">Side / radius</th><th scope="col">Original comparison</th></tr></thead><tbody>{table}</tbody></table></div><p><a href="data/results.csv" download>Download results CSV</a></p></details>'''
    fields=['id','kind','n','value_exact','reference_exact','gain_percent','checked_at','geometry','sha256']
    with (ROOT/'data/results.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");writer.writeheader();writer.writerows({k:r[k] for k in fields} for r in rows)
    (ROOT/'index.html').write_text(shell('Packing problems',body,'Packing problems I enjoy: square and circle arrangements, with diagrams, exact coordinates and dated source comparisons.'))
    print(f'Built {len(rows)} diagrams and detail pages; {len(FEATURED)} featured.')

if __name__=='__main__': build()
