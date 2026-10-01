"""Keep the HTML entry point tied to its exact CSS, application and data files."""
import hashlib
from pathlib import Path
import re

ENTRY_ASSETS = ('styles.css', 'assets/story-data.js', 'app.js')


def stamp_assets(site: Path):
    entry = site / 'index.html'
    html = entry.read_text(encoding='utf-8')
    for name in ENTRY_ASSETS:
        version = hashlib.sha256((site / name).read_bytes()).hexdigest()[:16]
        pattern = r'((?:href|src)=")' + re.escape(name) + r'(?:\?[^"\s]*)?(")'
        html, count = re.subn(pattern, lambda m: f'{m[1]}{name}?v={version}{m[2]}', html)
        if count != 1:
            raise ValueError(f'Expected one HTML reference to {name}, found {count}')
    entry.write_text(html, encoding='utf-8')


if __name__ == '__main__':
    from .paths import ROOT
    stamp_assets(ROOT / 'site')
