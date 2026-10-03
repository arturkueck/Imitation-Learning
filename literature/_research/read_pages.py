import json, sys
from pathlib import Path
pages = json.loads((Path(__file__).parent / f'{sys.argv[1]}.pages.json').read_text(encoding='utf-8'))
sys.stdout.reconfigure(encoding='utf-8')
for item in sys.argv[2:]:
 start, _, end = item.partition('-')
 for p in range(int(start), int(end or start)+1):
  print(f'===== PDF PAGE {p} =====\n{pages[p-1]}')
