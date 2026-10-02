"""Verify the downloaded release payload without loading pickle files."""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = ROOT / 'MANIFEST.sha256'
if not manifest.is_file():
    raise SystemExit('Missing MANIFEST.sha256')
errors = []
count = 0
for line in manifest.read_text().splitlines():
    expected, rel = line.split('  ', 1)
    p = ROOT / rel
    if not p.is_file():
        errors.append('missing: ' + rel)
        continue
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    if h.hexdigest() != expected:
        errors.append('digest: ' + rel)
    count += 1
print('Checked {} files; {} errors.'.format(count, len(errors)))
for e in errors:
    print(e)
sys.exit(1 if errors else 0)
