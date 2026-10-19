"""Stage only public website assets for GitHub Pages. No network dependencies."""
from pathlib import Path
import shutil
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '_site'
FILES = ['.nojekyll', 'CNAME', 'index.html', 'style.css', 'favicon.svg',
         'cv.pdf', 'reveal.js', 'contact-config.js', 'contact.js',
         'growth-physics.js', 'animation.js']
FOLDERS = ['for-fun', 'writing', 'packing']
EXTENSIONS = {'.html', '.css', '.svg', '.json', '.csv', '.txt', '.cert'}

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
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
    for page in OUT.rglob('*.html'):
        parser = Links()
        parser.feed(page.read_text())
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
    print(f'Staged {sum(p.is_file() for p in OUT.rglob("*"))} public files; local links verified.')

if __name__ == '__main__':
    build()
