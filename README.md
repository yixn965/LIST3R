# LIST3R: Long-sequence Instance-aware 3D Reconstruction

Project page for **LIST3R**, an instance-aware framework for long-sequence 3D reconstruction.

🌐 **Live page:** https://yixn965.github.io/LIST3R/

## What's here

The `docs/` folder holds a self-contained static project page:

- `index.html`, `styles.css`, `app.js` — the page (single white theme)
- `assets/figs/` — paper figures
- `assets/turntable/` — pre-rendered 180° turntable frames of the fused point
  clouds for 6 methods × 4 scenes, used by the interactive "Spin & compare" viewer
- `tools/` — the Python scripts that generated the turntable frames
- `serve.py` — a tiny no-cache static server for local preview

## Run locally

```bash
cd docs
python serve.py          # serves at http://localhost:8731
# or: python -m http.server 8000
```

## Citation

```bibtex
@inproceedings{gao2026list3r,
  title     = {LIST3R: Long-sequence Instance-aware 3D Reconstruction},
  author    = {Gao, Jing and Wang, Wei and Wang, Feiran and Yan, Yan},
  booktitle = {Advances in Neural Information Processing Systems (NeurIPS)},
  year      = {2026}
}
```
