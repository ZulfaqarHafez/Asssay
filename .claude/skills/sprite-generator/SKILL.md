---
name: sprite-generator
description: >-
  Create, extend, or regenerate Interviu's pixel-art SVG sprite sheets (dojo,
  judging, lessons, runs). Use when the user asks to add a sprite/tile, make a
  state visual, restyle a sheet, or "regenerate the sprites".
---

# Interviu Sprite Generator

Interviu renders pixel-art via deterministic 32px-grid SVG sprite sheets in
`apps/web/public/sprites/`. Each sheet is one SVG + a JSON manifest; the web app
references tiles purely by CSS class. This skill is how the sprite system "keeps
improving": add tiles or whole sheets on request and keep everything in sync.

## The sheet system (must stay consistent)

- **Files**: `apps/web/public/sprites/interviu-<sheet>-sprites.svg` + a sibling
  `interviu-<sheet>-sprites.json`. Sheets: `dojo` (9×5), `judging`, `lessons`,
  `runs` (each 9×1).
- **SVG conventions** (copy from `interviu-dojo-sprites.svg`): `<svg ...
  shape-rendering="crispEdges">`, a background `<rect fill="#fbfaf7"/>`, a
  `<defs><style>` palette block, and one `<g transform="translate(col*32 row*32)">`
  per tile drawn with `<rect class="..." x y width height/>` on a local 0..31 grid.
- **Palette classes (the only colors allowed)**:
  `.k`#2b2724 ink · `.w`#fff · `.t`#1f9e9a teal · `.g`#76a84f grass ·
  `.r`#e25b45 coral · `.y`#e8ae2e gold · `.v`#725ac1 violet · `.m`#6e6760 muted ·
  `.b`#4f86d9 blue. Semantics: grass=pass/approve, coral=fail/reject,
  gold=queued/caution, teal=active/running, violet=meta/marker.
- **Manifest**: `{ "image": "/sprites/interviu-<sheet>-sprites.svg", "tileSize": 32,
  "columns": 9, "sprites": { "<camelCaseName>": { "x": col, "y": row } } }`.
- **CSS wiring** in `apps/web/src/app/globals.css`:
  - `.sprite-sheet` is the base; it reads `--sprite-sheet-url`, `--sprite-cols`,
    `--sprite-rows`, `--sprite-x`, `--sprite-y`, `--sprite-scale`.
  - A `.sheet-<sheet>` class overrides url + cols/rows (e.g. `.sheet-runs`).
  - A `.sprite-<kebab-name>` class sets `--sprite-x`/`--sprite-y` for each tile.
  - Usage: `class="sprite-sheet sheet-runs sprite-pass-bead"`.

## To ADD a tile to an existing sheet

1. Edit the sheet's `.svg`: append a `<g transform="translate(col*32 row*32)">…</g>`
   in the next free cell (left→right, top→bottom). Use only palette classes; keep a
   clear chunky silhouette that reads at 32px (silhouette test); at most 1–2 `.w`
   glints.
2. Add the tile to the sheet's `.json` `sprites` map with its `{x,y}`.
3. If the sheet grew a row, bump `--sprite-rows` on its `.sheet-<sheet>` class.
4. Add a `.sprite-<kebab-name> { --sprite-x: <col>; --sprite-y: <row>; }` rule in
   `globals.css` (near the other tile classes).
5. Reference it in the UI as `sprite-sheet sheet-<sheet> sprite-<kebab-name>`.

## To ADD a whole new sheet

Mirror the existing `sheet-forge` approach: a deterministic 9×N SVG
(`288 × N*32`), a manifest, a `.sheet-<name>` CSS block, and tile classes. For a
fresh art pass you may fan out one author per sheet (see
`workflows/scripts/sprite-forge-*.js` for the prompt shape) — each agent writes
only its own `.svg`+`.json`, so they never conflict.

## Hybrid concept art (optional)

For visual direction, generate concept references with a Hugging Face image Space
(e.g. a pixel-art / SDXL pixel LoRA Space) or Canva, then **hand-redraw on the
32px grid** into SVG — the app ships SVG only (deterministic, testable). Never
ship raster tiles.

## Always verify after changes

- `python -c "import xml.dom.minidom as m; m.parse('apps/web/public/sprites/interviu-<sheet>-sprites.svg')"`
  (well-formed check).
- `npm --workspace apps/web run test` (web tests still pass).
- Open the app and eyeball the tile at 100% and at hero scale.
- Keep `docs/sprites.md` updated with new tiles.
