from pathlib import Path
from urllib.request import urlopen
import json, re
p = Path(__file__).parent
for key, doi in [('stable_bc', '10.1109/LRA.2025.3526439'), ('diffusion_policy_ijrr', '10.1177/02783649241273668')]:
 data = json.load(urlopen('https://api.crossref.org/works/' + doi, timeout=30))
 (p / f'{key}.crossref.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
 print(key, json.dumps({k:data['message'].get(k) for k in ['title','author','volume','issue','page','published','published-online','link']}, indent=2))
h = urlopen('https://collab.me.vt.edu/Stable-BC/', timeout=30).read().decode()
print('stable links:', re.findall(r'href=[\"\x27]([^\"\x27]+)', h))
