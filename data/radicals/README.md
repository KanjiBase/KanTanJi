# Radical data

Three bundled JSON datasets drive automatic radical→kanji linking with
localised meanings.

## `kangxi-214.json`

The 214 Kangxi radicals — language-neutral details. Keyed by Kangxi number
(as a string). Each entry:

| field        | type       | notes                                                              |
|--------------|------------|--------------------------------------------------------------------|
| `number`     | int        | 1–214                                                              |
| `radical`    | str        | Canonical character (CJK Unified Ideographs form, e.g. `水`)        |
| `variants`   | list[str]  | Graphical variants used in compounds (e.g. `氵`, `氺` for water)    |
| `strokes`    | int        | Stroke count of the canonical form                                  |
| `meaning_en` | str        | Baked-in English gloss (used as ultimate fallback)                  |
| `onyomi`     | list[str]  | Sino-Japanese readings (katakana)                                   |
| `kunyomi`    | list[str]  | Native Japanese names, including the standard *bushu* name          |

Hand-curated; regenerate by editing and running:

```
python misc/scripts/build_kangxi_214.py
```

## `kangxi-214.<lang>.json`

Per-language **meaning** translations. Flat object keyed by Kangxi number,
value is the localised meaning string:

```json
{
  "1": "jedna, vodorovný tah",
  "9": "člověk",
  "85": "voda"
}
```

Shipped languages:

- `kangxi-214.cs.json` — Czech (default; matches `config.LANGUAGE = "cs"`).
- `kangxi-214.en.json` — English (extracted from the main bundle's `meaning_en`).

### Adding a new language

1. Copy `kangxi-214.en.json` to `kangxi-214.<lang>.json`.
2. Translate every value. All 214 keys should be present; any missing key
   falls back to `meaning_en` and is reported at build time.
3. Set `LANGUAGE = "<lang>"` in `src/config.py`.

There is no sheet-based override mechanism — translations live exclusively in
these files.

## `generate/kanjidic2.xml`

The upstream KANJIDIC2 dump from EDRDG, vendored verbatim. The pipeline reads
it directly at startup (`src/radical_index.py`) and extracts the classical
radical number per kanji from `<rad_value rad_type="classical">`. No derived
JSON is kept — there is nothing to regenerate.

Either `kanjidic2.xml` (~15 MB) or `kanjidic2.xml.gz` (~6 MB) is accepted in
this folder; the loader picks whichever it finds first. To refresh, replace
the file with the latest version from EDRDG:

- Download: <http://www.edrdg.org/kanjidic/kanjidic2.xml.gz>

KANJIDIC2 is © EDRDG, CC BY-SA 4.0
(<https://www.edrdg.org/edrdg/licence.html>).

## Design notes

- **One radical per kanji.** We display the classical (Kangxi) radical only.
  Component decomposition (KRADFILE/IDS) is out of scope.
- **Canonical form on cards.** When a kanji uses a variant (e.g. 河 with `氵`),
  the card still shows the canonical form (`水`) because KANJIDIC2 only gives
  us the number, not the variant actually used in the glyph.
- **Missing kanji.** Kanji absent from KANJIDIC2 render no radical block; the
  build logs them once so the maintainer can patch coverage.
- **Missing translations.** If the active language file is missing some
  numbers, those radicals fall back to `meaning_en` and the build prints a
  single summary line counting the gaps.
