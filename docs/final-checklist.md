# Final profile checklist

## Already assembled locally

- `README.md` includes the theme-aware banner `<picture>`.
- `README.md` includes the self-hosted GitHub stats cards.
- `README.md` includes the streak card.
- `README.md` includes clickable social badges.
- `assets/dark.svg` and `assets/light.svg` are generated.
- `scripts/generate_banner.py` and `data/*.npy` are kept as the banner source of truth.

## Do by hand

1. Push this repo to `rithunkp/rithunkp` on the `main` branch.
2. Confirm `assets/dark.svg` and `assets/light.svg` are uploaded with the README.
3. Keep the GitHub token only in Vercel as `PAT_1`; never paste it into the repo.
4. Confirm the Vercel stats domain stays live:

```text
https://github-readme-stats-six-rouge-24.vercel.app
```

5. Check the README in both GitHub light and dark themes.
6. If an SVG change looks unchanged, open the raw URL with a cache-busting query:

```text
https://raw.githubusercontent.com/rithunkp/rithunkp/main/assets/dark.svg?v=999
```

Then use view-source and search for the changed hex/code. Most "didn't change" cases are GitHub CDN cache or the wrong theme.

## Skipped for now

Phase 3 contribution snake was intentionally skipped. Add it later only after creating the workflow and letting it run green, because the `output` branch does not exist before the first successful Action run.
