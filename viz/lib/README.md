# viz/lib

Vendored front-end libraries for `viz/inspect.html` so it runs offline / on a
static host with no import map or CDN.

- `d3.v7.min.js` — 2D force graph (UMD global `d3`).
- `graph3d.bundle.js` — 3D stack: `3d-force-graph` + `three-spritetext` +
  a **single** `three@0.185.1`, bundled with esbuild. Exposes global
  `Graph3D = { ForceGraph3D, SpriteText }`.

## Why a bundle?

`3d-force-graph` ships its own `three`, while `three-spritetext` needs a
matching `three`. Loading them separately produced **two three instances**,
which threw while rendering label sprites and blanked the whole 3D view.
esbuild bundles them against one deduped `three`, eliminating the conflict.

## Regenerate `graph3d.bundle.js`

```bash
cd /tmp && rm -rf sg-build && mkdir sg-build && cd sg-build
npm init -y
# three version must match 3d-force-graph's dependency (currently 0.185.1)
npm i 3d-force-graph@1.73.4 three-spritetext@1.8.2 three@0.185.1 esbuild
printf "import ForceGraph3D from '3d-force-graph';\nimport SpriteText from 'three-spritetext';\nexport { ForceGraph3D, SpriteText };\n" > entry.js
./node_modules/.bin/esbuild entry.js --bundle --format=iife \
  --global-name=Graph3D --minify \
  --outfile=<repo>/viz/lib/graph3d.bundle.js
# sanity: exactly one three revision
grep -oE 'REVISION[=:]"?[0-9]+' <repo>/viz/lib/graph3d.bundle.js | sort | uniq -c
```
