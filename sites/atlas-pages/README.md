# atlas-pages · public project site

Static, dependency-free site (HTML/CSS/JS, no build step) for the proposal
*Beyond the Demonstrated Task*. Live at https://arturkueck.github.io/Imitation-Learning/

| Page | Folder | Content |
|---|---|---|
| Overview | `index.html` | Question, why it is hard, approach and hypothesis, current status, links to all pages |
| Watch | `watch/` | Replays of real three-cube episodes, side-by-side videos, early recordings |
| Experiments | `experiments/` | Timeline of experiment families, five preliminary results with charts |
| Vision | `vision/` | Perception track (work package 5): accuracy, uncertainty, refinement, active camera, videos |
| Plan | `plan/` | Gantt chart and milestones with status |
| Journal | `journal/` | Hypothesis journal as a filterable table |
| Literature | `literature/` | The five proposal references |

Short links (tiny pages that forward immediately): `proposal/` → `files/proposal.pdf`,
`schedule/` → `files/schedule.pdf`, `status/` → status section, `repo/` → GitHub repository.
`404.html` is GitHub's "not found" page; it uses absolute `/Imitation-Learning/` paths.

The header and previous/next links come from `assets/nav.js` (edit the `PAGES` list there to add a page).
Every page sets `<body data-page="…" data-base="../">` so shared scripts find `media/`, `img/` and `data/`.
The PDFs in `files/` are copies of `output/pdf/Imitation_Learning_{Proposal,Gantt}_v2.pdf`; replace them
when the proposal changes.

`sites/research-atlas-source/` stays the internal research atlas (paper library, training
monitor). This folder is the outward-facing, proposal-centred view and contains only
condensed numbers, two plots and no model weights or raw data.

## Open locally

Double-click `index.html` - it works from `file://` because the data is loaded as a script
(`data/site-data.js`), not via `fetch`.

## Videos and replays

- `data/replays.js`: four real three-cube test episodes (scene 84002, 84004, 84047, 84001) from
  `experiments/self_imitation/stack_phased_8h_20261023/final_test/seed1_test3_traces/`, replayed
  on a canvas by `assets/replay.js`. Regenerate with `python sites/atlas-pages/tools/build_replays.py`;
  edit the `EPISODES` list there to show other scenes.
- `media/`: copies of existing recordings, captioned in `assets/media.js`. Sources:
  `experiments/stack_diagnostics/stack_direct_20261001` and `stack_placement_20261001` (side-by-side pairs),
  `output/meeting_2026-10-12/media` (stack success/failure, Lift animation),
  `experiments/baselines/{workday,diffusion}_20261001/videos` (BASE-001/002),
  `sites/research-atlas-source/public/{vision-evidence,training-assets/vision-active-v3-run1}` (vision GIFs,
  re-encoded to MP4) and `output/vision_videoauswahl_20261108` (VIS-001).
- `img/vision-*.jpg`: figures from `sites/research-atlas-source/public/vision-evidence`.
- The project timeline in section 4 is a hand-maintained list in `assets/gallery.js` (one entry per dated
  experiment folder); add new folders there.

## Update the data

```powershell
python sites/atlas-pages/tools/build_data.py
# optional: link journal evidence to your GitHub repo
python sites/atlas-pages/tools/build_data.py --repo-url https://github.com/<user>/<repo>
```

The script reads `experiments/HYPOTHESENJOURNAL.md` and
`sites/research-atlas-source/public/curriculum-evidence/{conclusion,results}.json`.
Narrative text and the status track (section 5) and Gantt status (section 6) are written in
`assets/app.js` - update those by hand when a milestone changes.
The critic plots in `img/` are copies of `output/three-cube-plots-2026-11-19/`.

## Host it for free on GitHub Pages

GitHub Pages is free for **public** repositories (private repos need GitHub Pro/Team).
The main project repo is large (multi-GB archives, checkpoints) and probably should stay
private, so publish this folder as its own small public repo:

1. Create an empty **public** repository on github.com, e.g. `imitation-learning-site`
   (no README, no license).
2. Commit this folder in the main project repo as usual, then push *only this folder*
   to the new repo with `git subtree` (run from the project root):

```powershell
git add sites/atlas-pages
git commit -m "Add public project site"
git remote add site https://github.com/<your-user>/imitation-learning-site.git
git subtree push --prefix sites/atlas-pages site main
```

Then on GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch →
Branch: `main` / `(root)` → Save**. After about a minute the site is at
`https://<your-user>.github.io/imitation-learning-site/`.

The `.nojekyll` file tells Pages to serve the files as they are.

To update later: rerun `build_data.py`, commit in the main repo, and run the same
`git subtree push --prefix sites/atlas-pages site main` again.

Note: anything on GitHub Pages is publicly visible. Check with your supervisor before
publishing unpublished results. Netlify Drop and Cloudflare Pages are free alternatives that
accept the folder by drag & drop; their sites are public too.
