# viz/lib

Vendored front-end libraries for `viz/inspect.html` so it runs offline / on a
static host with no CDN.

- `d3.v7.min.js` — 2D force graph (UMD global `d3`).
- `three.min.js` — three@0.157.0 (UMD global `THREE`), loaded **only** so
  `three-spritetext` can build the 3D node labels.
- `three-spritetext.min.js` — three-spritetext@1.8.2 (global `SpriteText`).
- `3d-force-graph.min.js` — 3d-force-graph@1.73.4 (global `ForceGraph3D`).
  Its UMD bundles its own three (r168) for the actual WebGL rendering.

## ⚠️ Do not "upgrade" the 3D three version blindly

An earlier attempt bundled these with esbuild against a newer three (r185).
That build threw `THREE.WebGLRenderer: Error creating WebGL context` on some
browsers/GPUs where the r168 UMD renders fine. Keep this pinned combo unless
you can verify a newer three still creates a context on those machines.

## Refresh the vendored files (same versions)

```bash
cd viz/lib
curl -sSL -o three.min.js            https://unpkg.com/three@0.157.0/build/three.min.js
curl -sSL -o three-spritetext.min.js https://unpkg.com/three-spritetext@1.8.2/dist/three-spritetext.min.js
curl -sSL -o 3d-force-graph.min.js   https://unpkg.com/3d-force-graph@1.73.4/dist/3d-force-graph.min.js
```
