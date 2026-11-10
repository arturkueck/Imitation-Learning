from pathlib import Path
import json, hashlib, re
from urllib.parse import unquote
from collections import Counter
from claims_data import CLAIMS, SOURCES

root=Path(__file__).resolve().parents[1]
workspace=root.parent
errors=[]
required=['INDEX.md','CLAIMS.md','BIBLIOGRAPHY.md','GAPS_AND_QUESTIONS.md',
 'methods/dagger.md','methods/dart.md','methods/stable_bc.md','methods/act.md','methods/diffusion_policy.md',
 'comparisons/method_comparison.md','comparisons/relation_to_our_results.md']
for f in required:
 if not (root/f).exists(): errors.append('Missing '+f)
ids=[x[0] for x in CLAIMS]
if len(ids)!=50 or len(set(ids))!=50: errors.append('Claim count/duplicate ID')
counts=Counter(x.split('-')[0] for x in ids)
register=(root/'CLAIMS.md').read_text(encoding='utf-8')
quote_checks=[]
for key,(name,slug,version,url) in SOURCES.items():
 pages=json.loads((root/'_research'/f'{slug}.pages.json').read_text(encoding='utf-8'))
 body=(root/'methods'/f'{slug}.md').read_text(encoding='utf-8')
 sections=re.findall(r'^## (\d+)\.',body,re.M)
 if sections!=[str(n) for n in range(1,15)]: errors.append(f'{slug}: expected 14 fields')
 if len(re.findall(r'^### '+key+r'-\d\d — PDF S\.',body,re.M))!=10: errors.append(f'{slug}: excerpts !=10')
 quotes=[]
 for id,topic,page,section,evidence,claim,para,use,quote in CLAIMS:
  if id.split('-')[0]!=key: continue
  if not 1<=page<=len(pages): errors.append(f'{id}: page invalid')
  if register.count(f'### {id}\n')!=1: errors.append(f'{id}: canonical count')
  if quote:
   normalize=lambda s:re.sub(r'\s+','',s).casefold()
   found=normalize(quote) in normalize(pages[page-1])
   quote_checks.append({'id':id,'page':page,'quote':quote,'verified_in_page_text':found})
   if not found: errors.append(f'{id}: quotation not on page')
   quotes += quote.split()
 if len(quotes)>25: errors.append(f'{slug}: quotes exceed 25 words')
 if key=='SBC' and any(not x[4].startswith('P-') for x in CLAIMS if x[0].startswith('SBC-')): errors.append('Unmarked Stable-BC preprint')
manifest=json.loads((root/'_research/manifest.json').read_text(encoding='utf-8'))
for slug,record in manifest.items():
 digest=hashlib.sha256((root/'_research'/f'{slug}.pdf').read_bytes()).hexdigest()
 if digest!=record['sha256']: errors.append('PDF hash mismatch '+slug)
local_v1=(root/'_research/stable_bc.pdf').read_bytes()
remote_v1=(root/'_research/stable_bc_arxiv_v1.pdf').read_bytes()
if local_v1!=remote_v1: errors.append('Stable-BC is not byte-identical to arXiv v1')
for f in required:
 body=(root/f).read_text(encoding='utf-8')
 for target in re.findall(r'\]\(([^)]+)\)',body):
  target=target.strip().split('#')[0]
  if not target or re.match(r'^(https?|codex):',target): continue
  if not ((root/f).parent/unquote(target)).exists(): errors.append(f'{f}: missing target {target}')
 if re.search(r'\bturn\d+(search|view|fetch)\d+\b',body): errors.append(f'{f}: tool citation leaked')

project_files=['next_research_direction.md','Projektarbeit Themenvorschlag -- Artur.md','README.md',
 'latex/plan_a/OVERVIEW_AND_LITERATURE.md','latex/plan_b/OVERVIEW_AND_LITERATURE.md','latex/plan_a/COMPARATIVE_REVIEW.md',
 'experiments/stack_diagnostics/stack_replication_20261001/ERGEBNISSE.md','experiments/stack_diagnostics/stack_replication_20261001/protocol.json',
 'experiments/stack_diagnostics/stack_replication_20261001/diffusion_failure_analysis.md',
 'experiments/stack_diagnostics/stack_followup_20261001/scripts/direct_common.py','experiments/stack_diagnostics/stack_followup_20261001/scripts/balance_common.py',
 'praxis/src/task_extensions/stack_expert.py','praxis/src/robomimic_ext/contraction_bc.py',
 'praxis/src/task_extensions/environments.py',
 'experiments/stack_diagnostics/stack_replication_20261001/direct/seed_2/config.json',
 'experiments/stack_diagnostics/stack_replication_20261001/diffusion/seed_2/config.json',
 'experiments/stack_diagnostics/stack_followup_20261001/scripts/evaluate_replication.py']
project_manifest={f:{'sha256':hashlib.sha256((workspace/f).read_bytes()).hexdigest(),
 'note':'Project source, not peer-reviewed; hash at final validation'} for f in project_files}
(root/'_research/project_manifest.json').write_text(json.dumps(project_manifest,ensure_ascii=False,indent=2),encoding='utf-8')
report={'verified_date':'2026-10-01','required_markdown_files':len(required),'canonical_claims':len(ids),
 'claims_by_paper':dict(counts),'topics':sorted(set(x[1] for x in CLAIMS)),
 'quotation_checks':quote_checks,'stable_bc_local_equals_arxiv_v1':local_v1==remote_v1,
 'scope':'Structural checks, quotation/page lookup and frozen-file hashes; scientific paraphrases manually checked against source pages.',
 'errors':errors}
(root/'_research/validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
