# Gurugram Narrative Dashboard

This repository contains a GitHub Pages-ready bundle of the Gurugram flood dashboard.

## Publish bundle

- `docs/index.html`: static dashboard entry point
- `docs/assets/`: extracted images and lazy-loaded query dataset
- `docs/.nojekyll`: disables Jekyll processing on GitHub Pages

## Rebuild

Run:

```bash
python3 scripts/build_github_pages_bundle.py
```

## Notes

The original local source dashboard is larger than GitHub's single-file limit, so this repository stores the optimized publish bundle instead of the raw `OPEN_THIS_FINAL_DASHBOARD.html` file.
