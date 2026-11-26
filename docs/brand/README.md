# neuDB brand assets

Canonical, original brand files for the README, GitHub, website, and social previews. The mark combines a lowercase **n** with a horizontal record line and a violet memory node inside an inspectable frame.

| File | Use |
|------|-----|
| `logo.svg` | Wordmark for dark backgrounds |
| `logo-light.svg` | Wordmark for light backgrounds |
| `icon.svg` | Favicon and compact product mark |
| `social-preview.svg` | Editable 1200×630 social card |
| `social-preview.png` | Raster social card for Open Graph and Twitter |
| `logo-mark.jpg` | Square raster mark for legacy placements |
| `app-icon.jpg` | Square raster app/touch icon |

## Design

- **Mark:** an original framed **n**, record line, and memory node. Do not stretch, rotate, recolor individual elements, or add effects.
- **Wordmark:** `neuDB`, with a capital **D**. Use the SVG rather than typesetting the name.
- **Palette:** monochrome `#0B0B0E`, `#17171C`, and `#F7F7F8`, with one restrained violet accent (`#6D5BD0` on light backgrounds, `#8B7BFF` on dark backgrounds).
- **Clear space:** leave at least one quarter of the icon width around the mark.
- **Minimum sizes:** 20 px high for the wordmark and 24 px for the icon. Use `icon.svg` below those sizes.
- **Backgrounds:** pair `logo.svg` with dark surfaces and `logo-light.svg` with light surfaces. The icon includes its own dark tile.

The JPGs are raster derivatives of `icon.svg`; the PNG is rendered from `social-preview.svg`. Regenerate them after changing the canonical SVGs so legacy placements stay consistent.

## Website sync

The landing page uses the files in `website/assets/`. The Pages workflow also copies `docs/brand/*` into that directory before deployment. After a manual brand change, sync the canonical files:

```bash
cp docs/brand/*.svg docs/brand/*.png docs/brand/*.jpg website/assets/
```

When raster tools are available, regenerate the derivatives before syncing:

```bash
rsvg-convert -w 512 -h 512 docs/brand/icon.svg -o neudb-icon.png
magick neudb-icon.png -background '#0B0B0E' -flatten -quality 90 docs/brand/logo-mark.jpg
magick neudb-icon.png -background '#0B0B0E' -flatten -quality 90 docs/brand/app-icon.jpg
rsvg-convert -w 1200 -h 630 docs/brand/social-preview.svg -o docs/brand/social-preview.png
cp docs/brand/*.svg docs/brand/*.png docs/brand/*.jpg website/assets/
rm neudb-icon.png
```