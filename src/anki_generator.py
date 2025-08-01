import genanki
import hashlib
import uuid
import markdown

from utils import generate_furigana, retrieve_row_kanjialive_url, sanitize_filename
from utils_data_entitites import InputFormat
from utils_html import parse_item_props_html


def reading_label(value):
    reading = str(value).split('・')
    if len(reading) == 2:
        return f'<span class="rl">{reading[0]}<span class="rldt">・{reading[1]}</span></span>'
    if len(reading) != 1:
        print('E: reading with multiple separators!', value)
    return f"""
<span class="rl">{value}</span>    
"""


def reading_label_unimportant(value):
    return f"""
<span class="rl rld">{value}</span>    
"""


css = """
.rl {padding:3px 9px;background:rgba(238,238,228,0.35);margin:0 5px;border-radius:3px;font-weight:bold;}
.rld {color: lightgray;font-weight:auto;background:rgba(238,238,228,0.25);}
.rldt {color: lightgray;}
.rlbl {visibility:hidden}
.qa {opacity:0.4;margin-bottom:15px}
.c {display: flex;flex-direction: column;justify-content: center; align-items: center;gap: 5px;width: 100%;text-align:center;}
.t {font-size:15pt;color: gray;font-weight: bold;}
.a {white-space: nowrap; font-size: 10pt;display:block;margin-bottom:10px;}
.o {background-color:rgba(188,188,188,0.1);color:gray!important;width: 100%;margin-top:25px;padding:5px 12px;border-radius:5px;text-align:left;}
.g {color:gray!important}
.u {background-color:rgba(50,50,50,0.2);border-radius:5px;padding:5px 12px;font-size:14pt;}
"""

kantanji_model = genanki.Model(
    1607392319,
    'KanTanJi Anki Model',
    fields=[{
        "name": 'Q',
    }, {
        "name": 'A'
    }],
    templates=[
        {
            'name': 'Card 1',
            'qfmt': "<div class='c'>{{Q}}</div><script>['click','touchstart'].forEach(event=>document.addEventListener(event,()=>document.querySelectorAll('ruby rt, .rlbl').forEach(x=>x.style.visibility='visible')));</script>",
            'afmt': "<div class='c qa'>{{Q}}</div><br><br><div class='c'>{{A}}</div><script>['click','touchstart'].forEach(event=>document.addEventListener(event, ()=>document.querySelectorAll('ruby rt, .rlbl').forEach(x=>x.style.visibility='visible')));</script>",
        },
    ],
    css=css
)


# Function to read the CSV data
def read_kanji_csv(key, data):
    usage_title = f"<b class='t'>{generate_furigana('使＜つか＞い方＜かた＞')}:</b><br>"

    output = []
    cards = []
    cards_translation = []
    name = f"KanTanJi::{key}"

    keys = data["order"]
    content = data["content"]
    for key in keys:
        item = content[key]

        if item.get("kanji").significance > 0:
            continue

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
            extra = f"<div class=\"o\">{extra}</div>"

        onyomi = "".join(map(reading_label, item.get("onyomi").get_equal(0)))
        onyomi += "".join(map(reading_label_unimportant, item.get("onyomi").get_below(1)))
        kunyomi = "".join(map(reading_label, item.get("kunyomi").get_equal(0)))
        kunyomi += "".join(map(reading_label_unimportant, item.get("kunyomi").get_below(1)))

        if onyomi and kunyomi:
            onyomi += "&emsp;&emsp;"

        kanji_alive = retrieve_row_kanjialive_url(item)

        cards.append([
            f"<a class=\"a\" href=\"{kanji_alive}\">{item['kanji']} KanjiAlive</a><div style=\"font-size: 32pt;\">{item['kanji']}</div>",

            f"<div>{onyomi + kunyomi}</div>"
            f"<div style=\"font-size: 26pt;\">{item['imi']}</div>{extra}",

            item["guid"], name, "kanji", 0
        ])

        # Translation to kanji card
        cards_translation.append([
            f"<a class=\"a\" href=\"{kanji_alive}\">{item['kanji']} KanjiAlive</a><div style=\"font-size: 26pt;\">{item['imi']}</div>",

            f"<div>{onyomi + kunyomi}</div>"
            f"<div style=\"font-size: 30pt;\">{item['kanji']}</div>{extra}",

            item["guid"], name, "kanji", 0
        ])

        for vocab_item in item.vocabulary():

            usage_lines = "".join(
                [f"<div>{generate_furigana(usage)}</div>" for usage in
                 vocab_item.get("tsukaikata")])

            # Extra fields
            extra = "".join([
                f"<div><b>{generate_furigana(key)}</b>: {generate_furigana(value)}</div>"
                if value.format == InputFormat.PLAINTEXT else
                f"<div><b>{markdown.markdown(generate_furigana(value))}</div>"

                for key, value in vocab_item.get("extra", {}).items()
            ])
            if usage_lines:
                usage_lines = f"<div class=\"u\">{usage_title}{usage_lines}</div>"
                if extra:
                    usage_lines = usage_lines + "<br><br>" + extra
            else:
                usage_lies = extra

            if usage_lines:
                usage_lines = f"<div class=\"o\">{usage_lines}</div>"

            # We also record vocab labels (tango:now  tango:deck  tango:other)
            # meaning the word is suitable to learn now, will appear later in the same deck with different kanji,
            # or will appear in the future
            vocab_def = vocab_item.get('tango')
            vocab_significance = vocab_def.significance

            word = f"<div style=\"font-size: 28pt;\">{generate_furigana(str(vocab_def))}</div>"

            props_html = parse_item_props_html(vocab_item)

            # Word to translation card
            cards.append([
                f"{word}",

                f"<div class=\"rlbl\">{props_html}</div>"
                f"<div style=\"font-size: 26pt;\">{vocab_item['imi']}</div>{usage_lines}",

                vocab_item["guid"], name, "tango",  vocab_significance
            ])

            # Translation to word card
            cards_translation.append([
                f"<div style=\"font-size: 26pt;\">{vocab_item['imi']}</div>",

                f"<div class=\"rlbl\">{props_html}</div>{word}{usage_lines}",

                vocab_item["guid"], name, "tango", vocab_significance
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

        question_html = row[0]
        answer_html = row[1]
        card_type = row[4]
        significance = row[5]

        tags = []
        if card_type == "kanji":
            tags.append("KanTanJi_Kanji")
        else:
            tags.append("KanTanJi_Tango")
            if significance == 0:
                tags.append("KanTanJi_Learn_Now")
            elif significance == 1:
                tags.append("KanTanJi_Learn_Deck")
            else:
                tags.append("KanTanJi_Learn_Future")

        # Create a note (card) with front and back content using the built-in model
        note = genanki.Note(
            model=kantanji_model,
            fields=[question_html, answer_html],
            guid=row[2],
            tags=tags
        )

        # Add the note to the deck
        deck.add_note(note)
    if deck:
        save_deck(filename, deck)


def generate(key, data, metadata, folder_getter, is_debug_run):
    # Anki packs only read data, so if not modified do not re-generate
    if not data["modified"] and not is_debug_run:
        return False
    anki = read_kanji_csv(key, data)

    if not is_debug_run:
        create_anki_deck(key, anki, f"{folder_getter(key)}/{sanitize_filename(key)}.apkg")
    return True
