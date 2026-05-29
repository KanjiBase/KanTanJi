# Scripts

Standalone scripts for ad-hoc Anki maintenance. Not part of the KanTanJi
build pipeline — invoke manually from a Python environment that has the
project's `requirements.txt` installed (the `.venv` at the repo root is
fine).

All scripts that touch a live Anki collection (`collection.anki2`) require
Anki Desktop to be **closed** while they run; otherwise the database lock
will fail.

## `cleanup_notetype_templates.py`

Removes accumulated legacy card templates from the KanTanJi notetype
(`MODEL_ID=1607392319`) in your Anki collection, migrating each note's
best-studied scheduling onto the canonical `KanTanJi` template
(`TEMPLATE_ID=2001`) before the legacy templates are deleted.

**When you need it.** After a `.apkg` re-import has left your notetype
with extra "Typ karty" entries beyond `KanTanJi` (e.g. `Card`, `Card 1`,
`Card 2`) — typically caused by an earlier build version using a
differently-named template under the same `MODEL_ID`, which Anki merges
into the existing notetype rather than replacing.

**What it does, per note:**

- Picks the card with the most progress across all templates using the
  tuple key `(type != 0, reps, ivl, factor, lapses)`; ties favour the
  canonical card.
- If a canonical (`KanTanJi`) card already exists and a legacy card has
  better progress, copies the scheduling fields (`type, queue, due, ivl,
  factor, reps, lapses, left, odue, odid, flags, custom_data, data`) onto
  the canonical card.
- If no canonical card exists for that note, retargets the best legacy
  card by setting its `ord` to the canonical template's ord — that card
  becomes the KanTanJi card with its scheduling preserved.
- Once every note is processed, removes the legacy templates. Anki
  cascade-deletes any remaining legacy cards (which by now hold only
  inferior or already-copied scheduling).

**Usage:**

```bash
# Dry-run (default): prints BEFORE/AFTER diagnostics and a migration plan,
# no changes written.
python misc/scripts/cleanup_notetype_templates.py "<path to collection.anki2>"

# Apply: writes a timestamped collection.anki2.bak-<timestamp> next to the
# original, then performs the migration and template removal.
python misc/scripts/cleanup_notetype_templates.py "<path to collection.anki2>" --apply

# Apply without the automatic backup (only do this if you've already
# backed up via Anki's own export):
python misc/scripts/cleanup_notetype_templates.py "<path to collection.anki2>" --apply --no-backup
```

On Windows the collection file usually lives at
`%APPDATA%\Anki2\<profile>\collection.anki2`.

**Healthy steady-state output** (after a successful `--apply`) is exactly
one template (`KanTanJi` at `ord=0`), `notes_only_canonical` equal to the
note count, and zero retargets/migrations. Anything else is a sign of
drift and worth investigating.

## `copy_scheduling_anki.py`

Transfers card scheduling from one `.apkg` onto another by **matching
notes by GUID**, then re-exports the target `.apkg`. Use it to recover
scheduling from an older export before importing a freshly-built one, or
to splice progress between two snapshots of the same deck.

**Usage:**

```bash
python misc/scripts/copy_scheduling_anki.py <source.apkg> <target.apkg> <output.apkg>
```

- `source.apkg` — the deck that holds the scheduling you want to keep.
- `target.apkg` — the deck whose content/structure you want to keep.
- `output.apkg` — written by the script; this is the file you actually
  import into Anki.

Fields transferred per matched card: `type, queue, due, ivl, factor, reps,
lapses, left, odue, odid, flags, custom_data, data`. If the source card
is in review state (`type == 2`), the destination is forced into review
state regardless of its prior queue.

## `move_scheduling.py`

Same intent as `copy_scheduling_anki.py` but matches by **normalized
first-field content** rather than by GUID. Reach for it when GUIDs have
diverged between source and destination (e.g. one of the decks was
re-keyed at some point), so a GUID-based join would miss otherwise
equivalent cards.

**Usage:**

```bash
python misc/scripts/move_scheduling.py \
    --source <source.apkg> \
    --destination <target.apkg> \
    --output <output.apkg> \
    [--missing suspend|ignore] \
    [--output-source <suspended-source.apkg>]
```

- `--missing suspend` will suspend the source cards that did transfer to
  the destination, so the source deck can continue being used to study
  only the non-transferred remainder (saved to `--output-source`).
- `--missing ignore` (default-ish) just proceeds.

## `deck_wrangling.py`

Library, not a CLI. Provides:

- `ApkgUnzippingManager` — context manager that unzips an `.apkg` into a
  temporary working directory and re-zips it on exit.
- `ApkgAsAnki` — gives access to the underlying `anki.collection.Collection`
  inside an unzipped `.apkg`.
- `ApkgAsPandas` — exposes the deck contents as pandas DataFrames for
  ad-hoc analysis.

`move_scheduling.py` imports from this module. If you write a new ad-hoc
script that needs to poke at the raw `.apkg` structure, build it on top
of these helpers rather than re-implementing zip/sqlite plumbing.

---

## Avoiding the next template-pollution incident

The cleanup tool above exists because earlier build evolutions changed
the notetype shape under a stable `MODEL_ID`. Anki imports key notetypes
by id and *merge* fields/templates rather than replacing them, so any
divergence between the build's notetype and a user's collection
accumulates as extra "ghost" templates that the user has to clean up
later. These rules keep that from happening again:

1. **Treat `MODEL_ID`, `FIELD_IDS`, and `TEMPLATE_ID` in
   `src/anki_generator.py` (around lines 36–38) as immutable** for the
   lifetime of the deck. Once a `.apkg` with a given id has been
   distributed/imported, that id is owned by the existing user
   collections — changing it under the same id is the source of the
   merge hazard.
2. **Never rename an existing template or field** once a build has been
   imported anywhere. If a rename is genuinely required (e.g. a
   model-shape redesign), bump `MODEL_ID` to a *new* numeric value so
   Anki sees a fresh, separate notetype. Then run
   `cleanup_notetype_templates.py` (or a one-off variant pointed at the
   new id) to migrate progress from the old id to the new id in a single
   intentional pass.
3. **Reverse cards stay separate notes**, using the `-rev` GUID suffix
   pattern that `src/anki_generator.py` already follows. Do *not* convert
   them into a second template on the same notetype — that re-introduces
   the multi-template merge hazard.
4. **Run `cleanup_notetype_templates.py` in dry-run periodically**,
   especially after any change to `src/anki_generator.py`'s model code.
   The expected steady-state output is exactly one template (`KanTanJi`)
   and zero migration work. Anything else is early warning of drift.
5. **Keep `with_scheduling=False`** in `ExportAnkiPackageOptions`
   (`src/anki_generator.py` around line 660). It is what makes
   GUID-matched re-imports update note *content* without overwriting the
   user's card scheduling. Flipping it back to `True` resets every
   updated card to "new" on every re-import.

### What re-import *does* update

The flip side of the rules above — useful when shipping template fixes
(HanziWriter tweaks, CSS changes, callback rewrites):

- **Template `qfmt`, `afmt`, and `css` are overwritten** on re-import
  whenever the imported notetype id matches an existing one (empirically
  verified with `with_scheduling=False, legacy=False`). This is the
  intended channel for delivering template-code fixes to users who
  already imported earlier builds — no hand-editing of the notetype in
  Anki Desktop required.
- **Field contents on existing notes are updated by GUID match**
  (`utils_data_entitites.py:339, 362`); brand-new notes are added.
- **What stays untouched**: card scheduling on existing cards (because
  of rule 5), the `MODEL_ID` / `FIELD_IDS` / `TEMPLATE_ID` join keys
  (because of rule 1), and cards already sitting on the canonical
  template ord.
