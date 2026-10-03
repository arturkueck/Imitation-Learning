from pathlib import Path
import pypdfium2 as pdfium
p = Path(__file__).parent
for key, nums in {'stable_bc':[4,5], 'act':[6,8], 'diffusion_policy':[6,15], 'dart':[8]}.items():
 doc = pdfium.PdfDocument(p / f'{key}.pdf')
 for num in nums:
  doc[num-1].render(scale=1.5).to_pil().save(p / f'{key}_p{num}.png')
print('Rendered 7 pages for equation/table verification.')
