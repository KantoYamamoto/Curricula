import sys
from pathlib import Path
from serve import ROOT

export = Path(sys.argv[1])
files = sorted(export.glob('*.json'))
assert len(files) == 5
for candidate in files:
    assert candidate.read_bytes() == (ROOT / 'data/releases' / candidate.name).read_bytes(), candidate.name
print('All five schema 0.2.0 snapshots reproduce exactly.')
