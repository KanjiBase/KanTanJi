"""
export relevant libraries from anki, as .apkg, with all extra information, to this folder.
"""

import argparse

import pandas as pd
import regex as re

from deck_wrangling import ApkgAsPandas

parser = argparse.ArgumentParser(
    prog="scheduling-transfer",
    description="Copies scheduling information from one anki deck to another, using user-specified functions to match cards between the decks",
)

parser.add_argument(
    "-s",
    "--source",
    type=str,
    help="Anki deck from which the scheduling information to transfer will be extracted, given as an .apkg file",
)
parser.add_argument(
    "-d",
    "--destination",
    type=str,
    help="Anki deck to which the transferred scheduling information will be inserted, given as an .apkg file",
)
parser.add_argument(
    "-o",
    "--output",
    type=str,
    help="Apkg filename to which the modified destination deck will be saved. Defaults to the same value as --destination (thus overwriting the destination deck). Changing this name will NOT change the name of the anki deck itself, only the .apkg file.",
)
parser.add_argument(
    "--missing",
    choices=["suspend", "ignore"],
    help="""How to handle the situation if some cards from the source deck have no equivalent in the destination deck. Unnecessary argument otherwise.
ignore: proceed as normal.
suspend: suspend all cards on the source deck that do have an equivalent on the destination deck. This is so that the source deck can continue being used to study only those cards that could not be transferred.""",
)
parser.add_argument(
    "--output-source",
    type=str,
    help="Only relevant if --missing is set to suspend, ignored otherwise. Apkg filename to which the modified source deck will be saved. Defaults to the same value as --source (thus overwriting the source deck). Changing this name will NOT change the name of the anki deck itself, only the .apkg file.",
)


# functions to normalize names


class MultipleAnnotator:
    def __init__(self):
        self.items = []

    def process(self, item):
        if item in self.items:
            i = 1
            item = f"{item} ({i})"
            while item in self.items:
                i += 1
                item = f"{item} ({i})"
        self.items.append(item)
        return item


defuriganizing_matcher = re.compile(r"<ruby><rb>(.*?)</rb><rt[^>]*>.*?</rt></ruby>")
defuriganize = lambda text: re.sub(defuriganizing_matcher, r"\1", text)
fix_okurigana_snafus = (
    lambda text: text.replace("と共にと共に", "と共に")
    .replace("係係らず", "係わらず")
    .replace("多多", "多い")
)
remove_pissy_notes = lambda text: text.replace(
    "(literally no example with you) ", ""
).replace("(e-stem) ", "")
remove_e_stem_paren = lambda text: text.replace("(エの形) ", "")

substitutions = {
    "逹": "達",  # miswritten character
    "晚": "晩",  # miswritten character
    "友逢": "友達",  # mistyped. 友逢 is correct but in usage it is clear that 友達 is intended
    "意昧": "意味",  # mistype, 意昧 is not a word
    "鷗": "鴎",
    # not wrong, but mecab has trouble with it, presumably due to being kyujitai. we select the shinjitai form. this is the 'kamome' in 'kamomedai', meaning 'seagull'
    "傾": "斜め",  # outdated kanji
    "頸": "頚",  # again we keep it shinjitai
    "ヶ月": "箇月",  # ヶ is an abbreviation of 箇 (looks like the top bit) but it's awkward to put furigana on it
    "悲しみした": "悲しみました",  # mistype
}


def kanji_substitutions(text):
    for pair in substitutions.items():
        text = text.replace(*pair)
    return text


def main(args):
    source_name = args.source
    if source_name.endswith(".apkg"):
        source_name = source_name[:-5]
    destination_name = args.destination
    if destination_name.endswith(".apkg"):
        destination_name = destination_name[:-5]
    output_name = args.output or destination_name
    if not output_name.endswith(".apkg"):
        output_name += ".apkg"
    output_source_name = args.output_source or source_name
    if not output_source_name.endswith(".apkg"):
        output_source_name += ".apkg"

    def ensure_missing_arg():
        if args.missing is None:
            raise Exception(
                f"""Because not all cards in the source deck have a match in the destination deck, the script will only run when the '--missing' flag has been set.
    In most instances, if you intend to continue studying all the material of the source deck (albeit having transferred part of it to the destination deck), you'll want to use '--missing suspend'. This will suspend all the cards on the source deck that get transferred to the destination deck, meaning you can continue using the source deck to study only the cards that did not get transferred.
    If for some other reason you do not want to do this, use '--missing ignore' - this will transfer the scheduling data from the source deck to the destination deck only for cards which exist in both, but leave the source deck untouched. There will be no way to continue studying the material that is only on the source deck, unless you go back to the source deck entirely.
    """
            )
        elif args.missing == "suspend":
            print(
                f"The '--missing' argument has been set to suspend, so cards in the source deck that have their scheduling data transferred onto the destination deck will be suspended in the source deck."
            )
        elif args.missing == "ignore":
            print(
                f"The '--missing' argument has been set to ignore, so we will transfer the scheduling data we can and leave the source deck otherwise untouched."
            )

    with (
        ApkgAsPandas(source_name, proceed_if_unzipped=True) as old_deck,
        ApkgAsPandas(destination_name, proceed_if_unzipped=True) as new_deck,
    ):
        new_field_data = new_deck.notes[["id", "flds"]].set_index("id")
        new_sched_data = new_deck.cards.set_index("nid")

        old_field_data = old_deck.notes[["id", "flds"]].set_index("id")
        old_sched_data = old_deck.cards.set_index("nid")

        # good idea to uncomment this if you are porting only a few cards
        # makes it so that the data gets copied only for cards with have been studied (if ivl=0 they've never been seen)
        # old_sched_data = old_sched_data[old_sched_data["ivl"]>0]
        # old_field_data = old_field_data.loc[old_sched_data.index]

        # separate and normalize first field of each card - as identifier
        select_first_field = lambda fields: fields.split("\x1f")[0]

        # for new vs old furiganized dojg decks (the latter has more steps b/c it was an old deck that i manually modified over time)
        normalized_names_new = new_field_data["flds"].apply(select_first_field)
        normalized_names_new = normalized_names_new.apply(remove_e_stem_paren)
        normalized_names_new = normalized_names_new.apply(MultipleAnnotator().process)

        normalized_names_old = old_field_data["flds"].apply(select_first_field)
        normalized_names_old = normalized_names_old.apply(defuriganize)
        normalized_names_old = normalized_names_old.apply(fix_okurigana_snafus)
        normalized_names_old = normalized_names_old.apply(remove_pissy_notes)
        normalized_names_old = normalized_names_old.apply(kanji_substitutions)
        normalized_names_old = normalized_names_old.apply(MultipleAnnotator().process)

        """
        # rtk -> migaku
        normalized_names_new = new_field_data['flds'].apply(select_first_field)

        normalized_names_old = old_field_data['flds'].apply(select_first_field)
        normalized_names_old = normalized_names_old[normalized_names_old.apply(lambda x: x!='阝')]
        normalized_names_old = normalized_names_old[normalized_names_old.apply(lambda x: re.match(r'\d\.\d',x) is None)]
        normalized_names_old = normalized_names_old[normalized_names_old.apply(lambda x: 'img' not in x)]
        """

        # some info for the user
        n_old, n_new = len(normalized_names_old), len(normalized_names_new)

        if n_old > len(set(list(normalized_names_old))):
            seen = set()
            dupes = [x for x in normalized_names_old if x in seen or seen.add(x)]
            raise Exception(
                f"Normalized identifier field in source deck does not uniquely determine a card. This can probably be fixed by either selecting a different field or using MultipleAnnotator. Duplicate ids are:\n{dupes}"
            )

        if n_new > len(set(list(normalized_names_new))):
            raise Exception(
                "Normalized identifier field in destination deck does not uniquely determine a card. This can probably be fixed by either selecting a different field or using MultipleAnnotator"
            )

        n_overlap = len(set(normalized_names_new) & set(normalized_names_old))
        print(f"Source deck contains {n_old} cards.")
        print(f"Destination deck contains {n_new} cards.")
        print(
            f"{n_overlap} (on each deck) of these cards have been matched to transfer scheduling data."
        )
        print("")

        new_surplus = set(list(normalized_names_new)) - set(list(normalized_names_old))
        if len(new_surplus) > 0:
            if len(new_surplus) > 1:
                print(
                    f"There are {len(new_surplus)} cards in the destination deck that have no equivalent in the source deck:"
                )
            else:
                print(
                    f"There is 1 card in the destination deck that has no equivalent in the source deck:"
                )
            print(new_surplus)
            print(
                "This only means the new deck has material that isn't in the source deck, which isn't necessarily a concern."
            )
            print("")

        old_surplus = set(list(normalized_names_old)) - set(list(normalized_names_new))
        if len(old_surplus) > 0:
            if len(old_surplus) > 1:
                print(
                    f"There are {len(old_surplus)} cards in the source deck that have no equivalent in the destination deck:"
                )
            else:
                print(
                    f"There is 1 card in the source deck that has no equivalent in the destination deck:"
                )
            print(old_surplus)
            ensure_missing_arg()
            print("")

        # find the match
        index_pairs = pd.merge(
            normalized_names_old.reset_index(name="name"),
            normalized_names_new.reset_index(name="name"),
            on="name",
            suffixes=("_old", "_new"),
        )[["id_old", "id_new"]]

        # gather the data that we will use to update it and switch the index to the new deck
        to_update = old_sched_data.merge(
            index_pairs, left_index=True, right_on="id_old", how="inner"
        )
        to_update.drop("id_old", axis=1, inplace=True)
        to_update.set_index("id_new", inplace=True)
        to_update = to_update[
            ["due", "ivl", "factor", "lapses", "type", "queue", "reps"]
        ]

        # write (overwrite) the scheduling data from the source deck onto the destination deck
        new_sched_data.update(to_update)
        new_sched_data.insert(1, "nid", new_sched_data.index)
        new_sched_data.reset_index(drop=True, inplace=True)
        new_sched_data.index.name = None

        new_sched_data.to_sql(
            name="cards", con=new_deck.engine, if_exists="replace", index=False
        )

        new_deck.commit_and_save(with_name=output_name, overwrite=True)

        if args.missing == "suspend":
            old_sched_data.loc[index_pairs["id_old"], "queue"] = -1
            old_sched_data.to_sql(
                name="cards", con=old_deck.engine, if_exists="replace", index=False
            )
            old_deck.commit_and_save(with_name=output_source_name, overwrite=True)


if __name__ == "__main__":
    args = parser.parse_args()
    # args = parser.parse_args(['-s','Japanese__Dictionary of Japanese Grammar +F +A with_scheduling_info','-d','Dictionary of Japanese Grammar +F +A','-o','output-destination','--missing','suspend','--output-source','output-source'])
    # args = parser.parse_args('-s', 'Japanese__Recognition RTK', '-d', 'Japanese__Recognition Migaku', '-o', 'output-destination','--missing', 'suspend', '--output-source', 'output-source'])
    main(args)