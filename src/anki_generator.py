
import genanki
import hashlib
import uuid
import markdown

from utils import generate_furigana, retrieve_row_kanjialive_url
from utils_data_entitites import InputFormat
from utils_html import parse_item_props_html


# Function to read the CSV data
def read_kanji_csv(key, data):

    reveal_furigana = "<script>['click', 'touchstart'].forEach(event => document.addEventListener(event, () => document.querySelectorAll('ruby rt').forEach(rt => rt.style.visibility = 'visible')));</script>"
    separator = f"<br><hr style=\"border: 1px solid gray\">"
    usage_title = "<b style=\"font-size: 14pt; color: gray;\">{generate_furigana('使＜つか＞い方＜かた＞')}:</b><br><br>"

    output = []
    cards = []
    cards_translation = []
    name = f"KanTanJi::{key}"

    keys = data["order"]
    content = data["content"]
    for key in keys:
        item = content[key]
        output.extend(cards)
        output.extend(cards_translation)
        cards = []
        cards_translation = []

        extra = "".join([
            f"<div style=\"color: gray; font-size: 14pt;\"><b>{generate_furigana(key)}</b>: {generate_furigana(value)}</div>"
            if value.format == InputFormat.PLAINTEXT else
            f"<div><b>{markdown.markdown(generate_furigana(value))}</div>"

            for key, value in item.get("extra", {}).items()
        ])
        if extra:
            extra = "<br>" + extra

        usage_lines = "".join([f"<div style=\"color: gray; font-size: 14pt;\">{generate_furigana(usage)}</div>" for usage in item.get("usage")])
        if usage_lines:
            usage_lines = usage_title + usage_lines
        if extra or usage_lines:
            # usage lines come first, add separator
            usage_lines = separator + usage_lines

        onyomi = item.get("onyomi").get_equal(0).join("  ")
        onyomi += "  ".join(
            f"<span style=\"color: gray; font-size: 14pt;\">{x}</span>" for x in item.get("onyomi").get_below(1))
        kunyomi = item.get("kunyomi").get_equal(0).join("　")
        kunyomi += "  ".join(
            f"<span style=\"color: gray; font-size: 14pt;\">{x}</span>" for x in item.get("kunyomi").get_below(1))

        if onyomi:
            onyomi = f"<span>Onyomi: {onyomi}</span>"
        if kunyomi:
            kunyomi = f"<span>Kunyomi: {kunyomi}</span>"
            if onyomi:
                kunyomi = " &emsp;" + kunyomi

        kanji_alive = retrieve_row_kanjialive_url(item)

        cards.append([
            f"㉆ <div style=\"font-size: 32pt;\">{item['kanji']}</div>",

            f"<div>{onyomi + kunyomi}</div>"
            f"<div style=\"font-size: 26pt;\">{item['meaning']}</div>"
            f"<br><br><div><a style=\"white-space: nowrap; font-size: 12pt;\" href=\"{kanji_alive}\">{item['kanji']} KanjiAlive</a></div>"
            + usage_lines + extra + reveal_furigana,

            item["guid"], name
        ])

        # Translation to kanji card
        cards_translation.append([
            f"㉆ <div style=\"font-size: 26pt;\">{item['meaning']}</div>",

            f"<div style=\"font-size: 30pt;\">{item['kanji']}</div>"
            f"<div>{onyomi + kunyomi}</div>"
            f"<br><br><div><a style=\"white-space: nowrap; font-size: 12pt;\" href=\"{kanji_alive}\">{item['kanji']} KanjiAlive</a></div>"
            + usage_lines + extra + reveal_furigana,

            item["guid"], name
        ])


        for vocab_item in item.vocabulary():
            extra = "".join([
                f"<div style=\"color: gray; font-size: 14pt;\"><b>{generate_furigana(key)}</b>: {generate_furigana(value)}</div>"
                if value.format == InputFormat.PLAINTEXT else
                f"<div><b>{markdown.markdown(generate_furigana(value))}</div>"

                for key, value in item.get("extra", {}).items()
            ])
            if extra:
                extra = "<br>" + extra

            usage_lines = "".join(
                [f"<div style=\"color: gray; font-size: 14pt;\">{generate_furigana(usage)}</div>" for usage in
                 vocab_item.get("usage")])
            if usage_lines:
                usage_lines = usage_title + usage_lines
            if extra or usage_lines:
                # usage lines come first, add separator
                usage_lines = separator + usage_lines

            word = f"<div style=\"font-size: 28pt;\">{generate_furigana(vocab_item['word'])}</div>"

            props_html = parse_item_props_html(vocab_item)

            # Word to translation card
            cards.append([
                f"{word}{reveal_furigana}",
                
                f"<div style=\"font-size: 26pt;\">{vocab_item['meaning']}</div>"
                + props_html + usage_lines + extra + reveal_furigana,

                vocab_item["guid"], name
            ])

            # Translation to word card

            cards_translation.append([
                f"<div style=\"font-size: 26pt;\">{vocab_item['meaning']}</div>",
                
                f"{word}"
                + props_html + usage_lines + extra + reveal_furigana,

                vocab_item["guid"], name
            ])

    # consume leftowers
    output.extend(cards)
    output.extend(cards_translation)
    return output


def generate_numeric_id_from_text(text, max_digits=16):
    # Generate a UUID from text (use SHA-256 if you want more robustness for long arbitrary text)
    namespace_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, text)  # Generate UUID
    sha_hash = hashlib.sha256(namespace_uuid.bytes + text.encode("utf-8")).hexdigest()
    
    # Convert hash to integer, then truncate to desired digit length
    numeric_id = int(sha_hash, 16) % (10 ** max_digits)
    return numeric_id


def save_deck(filename, deck):
    # Export the deck to a .apkg file
    genanki.Package(deck).write_to_file(filename)


def create_anki_deck(key, reader, filename):
    deck = None
    deck_name = None
    for row in reader:
        
        if deck_name != row[3]:
            if deck:
                raise ValueError("New anki deck created in the middle of table!")
            deck_name = f"KanTanJi::{key}"
            # Create the Anki deck
            deck = genanki.Deck(
                generate_numeric_id_from_text(deck_name),
                deck_name
            )   
        
        question_html = row[0]  # Front of the card
        answer_html = row[1]    # Back of the card

        # Create a note (card) with front and back content using the built-in model
        note = genanki.Note(
            model=genanki.BASIC_MODEL,  # Use Anki's built-in Basic model with a reverse card
            fields=[question_html, answer_html],
            guid=row[2]
        )
        
        # Add the note to the deck
        deck.add_note(note)
    if deck:
        save_deck(filename, deck)


def generate(key, data, metadata, folder_getter):
    # Anki packs only read data, so if not modified do not re-generate
    if not data["modified"]:
        return False
    anki = read_kanji_csv(key, data)
    create_anki_deck(key, anki, f"{folder_getter(key)}/{key}.apkg")
    return True
