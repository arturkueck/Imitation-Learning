# Research Atlas

Private interactive view of eight reviewed imitation-learning papers, 48 citation-linked keynotes, and imported open-access research.

## 3D research graph and imports

- Perspective-projected 3D canvas: drag to rotate, wheel to zoom, arrow keys to rotate, plus/minus to zoom. Accessible node/edge list is also available.
- Blue directed edges mean citation; amber dashed edges mean inferred topic similarity. Initial citation evidence is recorded in `public/graph.json` with PDF page and custom line references. Topic links expose their shared labels and do not claim agreement.
- Bibliographic discovery uses OpenAlex. Citation metadata can be incomplete; the PDF bibliography fallback checks at most 20 entries and accepts a match only when the normalized candidate title occurs in the extracted reference text. Existing verified edges remain available even without the external provider.
- Search for a title, explore a paper's cited references, then download and index available PDFs. The optional checkbox also imports up to five available references, one hop only. Failures are shown individually; no paywall bypass or automatic recursive crawl.
- PDFs and page text persist privately in the Site's R2 binding. Repeated exact-ID imports reuse the stored file. Metadata-only references appear separately from indexed documents. Different published/preprint work IDs can still represent variants of the same work.
- Imports are limited to 16 MB and 100 pages, with a two-million-character extraction cap. Scans without a text layer are stored but marked `no-text`; OCR is not implemented. Full-text search scans up to 100 indexed documents and returns up to 12 page excerpts.
- Source files now live in `public/`; Vinext serves the API from `app/api/research/route.ts`. `/` redirects to the retained research interface. D1 is unused; R2 is declared as `BUCKET`.

Validation: production build passed; local import/index of DAgger (9 pages) and DDPM (25 pages) passed; full-text search returned page matches; UMI reference lookup exercised the PDF-reference fallback. Local preview storage is separate from production storage.

## Contents

- Paper library, theme/search filters and comparison table.
- Paper detail and precise source references (PDF page, custom line range, column and section).
- Browser-local notebook, saved evidence and Markdown export.
- Conversational source finder with bilingual keyword expansion and paper scoping.

## Chat status

The current conversation panel is explicitly a source finder, not an LLM. It retrieves existing notes and does not synthesize answers. AI chat is pending the OpenAI Developers connection and approved secret provisioning. No API key is embedded or requested in browser code. Copy-context supports continuing the discussion in the current Codex chat.

## Data and preview

Run `prepare_data.py` from this directory to refresh `dist/research.json` from the existing research table and keynote register. No local filesystem paths are published. PDF links lead to the frozen source URLs recorded in the manifest. Notes and history live in browser localStorage, not on a shared backend.

Serve `dist` with a static HTTP server for preview. Deployment uses the Sites helper and `.openai/hosting.json`. New Site access is owner-private.
