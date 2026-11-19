# atlas-pages · public project site

Static, dependency-free site (HTML/CSS/JS, no build step) for the proposal
*Beyond the Demonstrated Task*. It walks a reader through the project as a guided tour:

1. **Question** – what the project asks, scope
2. **Why it's hard** – interactive compounding-error calculator, where the transfer breaks
3. **Approach** – BC vs. Actor–Critic (new critic) vs. Actor–Critic (IL-informed critic), hypothesis
4. **Evidence** – five preliminary experiments (BC-002, BC-003, BC-004, BC-005, AC-001) with charts
5. **Status** – critic pipeline (AC-002 … AC-006), open decision
6. **Plan** – Gantt and milestones from `schedule.tex`, with per-package status
7. **Journal** – searchable/filterable view of `experiments/HYPOTHESENJOURNAL.md`
8. **Literature** – the five proposal references

`sites/research-atlas-source/` stays the internal research atlas (paper library, training
monitor). This folder is the outward-facing, proposal-centred view and contains only
condensed numbers, two plots and no model weights or raw data.

## Open locally

Double-click `index.html` - it works from `file://` because the data is loaded as a script
(`data/site-data.js`), not via `fetch`.

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
