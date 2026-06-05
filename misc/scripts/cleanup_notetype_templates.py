import argparse
import contextlib
import gc
import shutil
import sys
import time
from pathlib import Path

from anki.collection import Collection
from anki.models import NotetypeId


CANONICAL_MODEL_ID = 1607392319
CANONICAL_TEMPLATE_ID = 2001
CANONICAL_TEMPLATE_NAME = "KanTanJi"

SIDECAR_SUFFIXES = ("-wal", "-shm")

# Scheduling fields transferred from the best legacy card to the canonical
# card when both exist. Same set used by misc/scripts/copy_scheduling_anki.py.
SCHED_FIELDS = (
    "type", "queue", "due", "ivl", "factor", "reps", "lapses",
    "left", "odue", "odid", "flags", "custom_data", "data",
)


def _pick_canonical(notetype):
    for t in notetype["tmpls"]:
        if t.get("id") == CANONICAL_TEMPLATE_ID:
            return t
    for t in notetype["tmpls"]:
        if t.get("name") == CANONICAL_TEMPLATE_NAME:
            return t
    return None


def _card_count_for_ord(col, mid, ord_):
    return col.db.scalar(
        "select count(*) from cards where ord = ? "
        "and nid in (select id from notes where mid = ?)",
        ord_, mid,
    )


def _note_count(col, mid):
    return col.db.scalar("select count(*) from notes where mid = ?", mid)


def _print_diagnostics(col, notetype, label):
    print(f"--- {label} ---")
    print(f"  notetype id={notetype['id']} name={notetype['name']!r}")
    print(f"  notes: {_note_count(col, notetype['id'])}")
    print(f"  templates ({len(notetype['tmpls'])}):")
    for t in notetype["tmpls"]:
        cnt = _card_count_for_ord(col, notetype["id"], t["ord"])
        print(
            f"    ord={t['ord']:>2} id={t.get('id')!s:>20} "
            f"name={t.get('name')!r:<20} cards={cnt}"
        )


def _backup(col_path: Path) -> Path:
    ts = time.strftime("%Y%m%d-%H%M%S")
    backup = col_path.with_name(f"{col_path.name}.bak-{ts}")
    print(f"[*] Backing up {col_path.name} -> {backup.name}")
    shutil.copy2(col_path, backup)
    for suffix in SIDECAR_SUFFIXES:
        side = col_path.with_name(col_path.name + suffix)
        if side.exists():
            side_bak = backup.with_name(backup.name + suffix)
            shutil.copy2(side, side_bak)
            print(f"    + sidecar {side.name} -> {side_bak.name}")
    return backup


def _progress_key(card):
    # Higher is better. Prefer not-new, then most reviewed, then longest interval,
    # then highest ease, then most lapses (still useful signal of "this card has history").
    return (
        1 if card.type != 0 else 0,
        card.reps,
        card.ivl,
        card.factor,
        card.lapses,
    )


def _plan_and_migrate(col, notetype, canonical_ord, apply_changes):
    """Walk every note on this notetype. Decide whether to migrate scheduling
    from the best legacy card onto the canonical card, retarget a legacy card
    to become the canonical card, or leave the note alone. When apply_changes
    is False, only counts are returned; no writes happen."""
    mid = notetype["id"]
    note_ids = col.db.list("select id from notes where mid = ?", mid)

    counters = {
        "notes_total": len(note_ids),
        "notes_with_no_cards": 0,
        "notes_only_canonical": 0,
        "migrated_scheduling": 0,
        "retargeted": 0,
        "unchanged_canonical_already_best": 0,
    }

    for nid in note_ids:
        cid_rows = col.db.list("select id from cards where nid = ?", nid)
        if not cid_rows:
            counters["notes_with_no_cards"] += 1
            continue

        cards = [col.get_card(cid) for cid in cid_rows]
        by_ord = {c.ord: c for c in cards}
        canonical_card = by_ord.get(canonical_ord)

        if canonical_card is not None and len(cards) == 1:
            counters["notes_only_canonical"] += 1
            continue

        # Pick the best source across ALL of this note's cards. Tie-break
        # prefers the canonical card so we avoid pointless writes when
        # canonical already has the same (or strictly better) progress.
        best = max(
            cards,
            key=lambda c: (_progress_key(c), 1 if c.ord == canonical_ord else 0),
        )

        if canonical_card is not None:
            if best is canonical_card:
                counters["unchanged_canonical_already_best"] += 1
            else:
                if apply_changes:
                    for f in SCHED_FIELDS:
                        if hasattr(best, f) and hasattr(canonical_card, f):
                            setattr(canonical_card, f, getattr(best, f))
                    col.update_card(canonical_card)
                counters["migrated_scheduling"] += 1
        else:
            # No canonical card exists. Retarget the best legacy card.
            if apply_changes:
                best.ord = canonical_ord
                col.update_card(best)
            counters["retargeted"] += 1

    return counters


def _print_migration_counts(counters):
    print("[*] Migration plan:")
    print(f"    notes total ............................ {counters['notes_total']}")
    print(f"    notes with no cards (skipped) .......... {counters['notes_with_no_cards']}")
    print(f"    notes already only on canonical ........ {counters['notes_only_canonical']}")
    print(f"    migrated scheduling -> canonical ....... {counters['migrated_scheduling']}")
    print(f"    retargeted legacy card to canonical .... {counters['retargeted']}")
    print(f"    canonical already best (no change) ..... {counters['unchanged_canonical_already_best']}")


def cleanup(col_path: Path, apply_changes: bool, do_backup: bool) -> int:
    if not col_path.exists():
        print(f"[!] Collection file not found: {col_path}", file=sys.stderr)
        return 2

    if apply_changes and do_backup:
        _backup(col_path)

    col = Collection(str(col_path))
    try:
        notetype = col.models.get(NotetypeId(CANONICAL_MODEL_ID))
        if notetype is None:
            print(
                f"[!] No notetype with id={CANONICAL_MODEL_ID} in this collection.",
                file=sys.stderr,
            )
            return 3

        _print_diagnostics(col, notetype, "BEFORE")

        canonical = _pick_canonical(notetype)
        if canonical is None:
            print(
                f"[!] Could not identify canonical template "
                f"(looked for id={CANONICAL_TEMPLATE_ID} or "
                f"name={CANONICAL_TEMPLATE_NAME!r}). Aborting.",
                file=sys.stderr,
            )
            return 4

        victims = [t for t in notetype["tmpls"] if t is not canonical]
        canonical_ord = canonical["ord"]

        print(
            f"\n[*] Canonical: name={canonical['name']!r} "
            f"id={canonical.get('id')} ord={canonical_ord}."
        )
        if victims:
            print(f"[*] Legacy templates to be removed after migration ({len(victims)}):")
            for t in victims:
                cnt = _card_count_for_ord(col, notetype["id"], t["ord"])
                print(
                    f"    - name={t['name']!r:<14} ord={t['ord']:>2} "
                    f"id={t.get('id')!s:>20}  currently holds {cnt} card(s)"
                )
        else:
            print("[*] No legacy templates present.")

        print()
        counters = _plan_and_migrate(col, notetype, canonical_ord, apply_changes)
        _print_migration_counts(counters)

        if not apply_changes:
            print("\n[*] Dry-run: no changes written. Re-run with --apply to mutate.")
            return 0

        if victims:
            print()
            for t in list(victims):
                print(f"[*] removing template name={t['name']!r} ord={t['ord']}")
                col.models.remove_template(notetype, t)
            col.models.update_dict(notetype)

        with contextlib.suppress(Exception):
            col.db.execute("PRAGMA wal_checkpoint(FULL);")
            col.db.execute("PRAGMA journal_mode=DELETE;")
            col.db.execute("PRAGMA wal_checkpoint(FULL);")

        notetype = col.models.get(NotetypeId(CANONICAL_MODEL_ID))
        print()
        _print_diagnostics(col, notetype, "AFTER")
        print("\n[✓] Cleanup complete.")
        return 0
    finally:
        col.close()
        gc.collect()
        time.sleep(0.1)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Migrate scheduling from legacy card templates to the canonical "
            f"'KanTanJi' template (id={CANONICAL_TEMPLATE_ID}) on notetype "
            f"id={CANONICAL_MODEL_ID}, then remove the legacy templates. "
            "Anki must be closed while this runs."
        )
    )
    parser.add_argument(
        "collection",
        help=(
            "Path to collection.anki2 (e.g. "
            r"%%APPDATA%%\Anki2\<profile>\collection.anki2)."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform the migration and removal. Without this flag the script is dry-run only.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip the timestamped .bak copy before mutating (only honoured with --apply).",
    )
    args = parser.parse_args()

    col_path = Path(args.collection).expanduser().resolve()
    rc = cleanup(col_path, apply_changes=args.apply, do_backup=not args.no_backup)
    sys.exit(rc)


if __name__ == "__main__":
    main()
