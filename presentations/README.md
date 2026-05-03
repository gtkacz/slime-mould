# presentations/

Source of record for talks about ZipMould. Rendered with [Marp](https://marp.app/) so the markdown is the canonical artifact and HTML/PDF are derived outputs.

## Files

| File | Role |
|---|---|
| `zipmould.md` | Source. Marp markdown with KaTeX math + inline theme. Edit this. |
| `zipmould.html` | Standalone deck. Open in a browser, press <kbd>F</kbd> for fullscreen. |
| `zipmould.pdf` | Print/share copy. Generated via headless Chrome. |

## Render

The repo does not pin Marp — `bunx` fetches it on demand. Run from inside `presentations/`:

```bash
# HTML (fast, browser-friendly)
bunx --bun @marp-team/marp-cli@latest zipmould.md --html --output zipmould.html

# PDF (Chrome-based; --allow-local-files needed for KaTeX fonts)
bunx --bun @marp-team/marp-cli@latest zipmould.md --pdf --allow-local-files --output zipmould.pdf
```

Both targets in one shot:

```bash
bunx --bun @marp-team/marp-cli@latest zipmould.md --html --output zipmould.html \
  && bunx --bun @marp-team/marp-cli@latest zipmould.md --pdf --allow-local-files --output zipmould.pdf
```

Requires Chrome at `/usr/bin/google-chrome` (or set `CHROME_PATH`). Bun + Node are picked up automatically.

## Present

Three options, in order of preference for live talks:

1. **Marp speaker view** (Marp VS Code extension or `--preview` flag): notes pane + timer.
2. **HTML in browser**: open `zipmould.html`, press <kbd>F</kbd> for fullscreen, arrow keys to navigate.
3. **PDF fallback**: any PDF reader in fullscreen — works offline, no Chrome dependency at present time.

Pagination is enabled (`paginate: true` in front-matter) so the slide number is visible bottom-right; the lead title slide opts out via `<!-- _paginate: false -->`.

## Edit

The deck uses an **inline custom theme** in the front-matter `style:` block — a dark slate (`#0f172a`) base with cyan headings (`#22d3ee`) and amber accents (`#fbbf24`). To change look-and-feel, edit `style:` in `zipmould.md`; do not import a separate `.css` file (Marp would need to be invoked with `--theme-set`).

### Layout primitives baked into the theme

- `<div class="columns">` — 1 : 1 two-column grid.
- `<div class="columns-wide-left">` — 3 : 2 two-column grid.
- `<div class="ribbon">` — left-bordered emphasis block.
- `<p class="citation">` — small-italic footer for source attributions.
- `section.lead` — full-bleed title-slide variant (set per-slide via `<!-- _class: lead -->`).

### Math gotchas (verified the hard way)

- KaTeX is enabled via `math: katex` in the front-matter.
- **Inside markdown tables**, `|` is the column separator. Math like `\mathbb{R}^{|E|}` or `|F_0 - F_1|` will silently split the cell. Use `\lvert ... \rvert`, or rewrite without pipes (`\mathbb{R}^m` with a legend).
- HTML blocks (`<p>`, `<div>`) generally render math fine, **except** when inline `$...$` falls inside a wider HTML construct that bypasses Marp's markdown phase. If math fails to render in a `<p class="citation">`, fall back to Unicode Greek (`α`, `β`).

## Re-validate after edits

Render PDF, then dump per-page PNGs and inspect:

```bash
mkdir -p /tmp/zm-review && rm -f /tmp/zm-review/slide-*.png
pdftoppm -png -r 110 zipmould.pdf /tmp/zm-review/slide
# then open /tmp/zm-review/slide-NN.png for any slide of interest
```

Watch for:

- Bottom-edge overflow on text-heavy slides.
- Math rendered as raw `$...$` (front-matter `math:` typo, or a table-pipe collision).
- Code blocks scrolling horizontally (reduce font-size in `pre` rule, or split the listing).

## Tooling versions known to work

- `bunx` resolving `@marp-team/marp-cli@4.3.1`
- `bun 1.3.x`, `node 24.x`
- `google-chrome` 127+
- `pdftoppm` from poppler 25+

Older Marp CLI versions (≤ 3.x) lack `--allow-local-files`; KaTeX fonts will then load as base64 and PDF generation slows by ~3×.
