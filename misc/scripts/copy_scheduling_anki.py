import argparse
import os
import tempfile
import gc
import time
import contextlib
from pathlib import Path

from anki.collection import Collection

# Robust Protobuf Imports based on provided specs
try:
    from anki.import_export_pb2 import (
        ImportAnkiPackageRequest,
        ExportAnkiPackageOptions,
        ExportLimit
    )
    from anki.generic_pb2 import Empty
except ImportError:
    # Fallback to internal paths if pb2 files are nested differently
    from anki.models_pb2 import ImportAnkiPackageRequest
    from anki.import_export_pb2 import ExportAnkiPackageOptions, ExportLimit
    from anki.generic_pb2 import Empty


def transfer_scheduling(source_apkg: str, target_apkg: str, output_apkg: str):
    src_col = None
    dst_col = None
    tmp_src = tempfile.TemporaryDirectory()
    tmp_dst = tempfile.TemporaryDirectory()

    try:
        # 1. Setup Source Collection
        print(f"[*] Extracting source: {source_apkg}")
        src_path = os.path.join(tmp_src.name, "collection.anki2")
        src_col = Collection(src_path)
        # ImportAnkiPackageRequest uses 'package_path'
        src_col.import_anki_package(ImportAnkiPackageRequest(
            package_path=str(Path(source_apkg).absolute())
        ))

        # 2. Setup Target Collection
        print(f"[*] Extracting target: {target_apkg}")
        dst_path = os.path.join(tmp_dst.name, "collection.anki2")
        dst_col = Collection(dst_path)
        dst_col.import_anki_package(ImportAnkiPackageRequest(
            package_path=str(Path(target_apkg).absolute())
        ))

        # 3. Data Transfer Logic via Note GUID
        src_map = {}
        for nid in src_col.find_notes(""):
            n = src_col.get_note(nid)
            cids = src_col.card_ids_of_note(nid)
            src_map[n.guid] = {src_col.get_card(cid).ord: src_col.get_card(cid) for cid in cids}

        updated_count = 0
        for nid in dst_col.find_notes(""):
            n = dst_col.get_note(nid)
            if n.guid in src_map:
                cids = dst_col.card_ids_of_note(nid)
                src_cards = src_map[n.guid]
                for cid in cids:
                    dc = dst_col.get_card(cid)
                    if dc.ord in src_cards:
                        sc = src_cards[dc.ord]

                        # 1. Sync all standard scheduling fields
                        for field in [
                            "type", "queue", "due", "ivl", "factor", "reps", "lapses",
                            "left", "odue", "odid", "flags", "custom_data", "data"
                        ]:
                            if hasattr(sc, field) and hasattr(dc, field):
                                setattr(dc, field, getattr(sc, field))

                        # 2. FORCE REVIEWS: If the source card was a review card,
                        # ensure the target card is moved out of the 'New' queue (0).
                        if sc.type == 2:  # 2 = Review
                            dc.type = 2
                            dc.queue = 2

                        dst_col.update_card(dc)
                        updated_count += 1

        dst_col.save()
        with contextlib.suppress(Exception):
            dst_col.db.execute("PRAGMA wal_checkpoint(FULL);")
            dst_col.db.execute("PRAGMA journal_mode=DELETE;")
            dst_col.db.execute("PRAGMA wal_checkpoint(FULL);")
        dst_col.save()
        print(f"[✓] Successfully updated {updated_count} cards.")

        # 4. Export logic following provided .proto specs
        all_decks = dst_col.decks.all_names_and_ids()
        export_deck_id = all_decks[0].id
        for deck in all_decks:
            if deck.name != "Default":
                export_deck_id = deck.id
                break

        # Construct ExportAnkiPackageOptions
        options = ExportAnkiPackageOptions(
            with_scheduling=True,
            with_deck_configs=True,
            with_media=True,
            legacy=False
        )

        # Construct ExportLimit using deck_id
        limit = ExportLimit(deck_id=export_deck_id)

        dst_col.export_anki_package(
            out_path=str(Path(output_apkg).absolute()),
            options=options, limit=limit
        )
        print(f"[*] Export complete: {output_apkg}")

    except Exception as e:
        print(f"[!] Critical Error: {e}")
    finally:
        if src_col: src_col.close()
        if dst_col: dst_col.close()
        src_col = dst_col = None
        gc.collect()
        time.sleep(0.5)
        tmp_src.cleanup()
        tmp_dst.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Source APKG (with progress)")
    parser.add_argument("target", help="Target APKG (to be updated)")
    parser.add_argument("output", help="Output APKG path")
    args = parser.parse_args()
    transfer_scheduling(args.source, args.target, args.output)