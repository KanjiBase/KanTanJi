import pdfkit
from utils import retrieve_row_kanjialive_url, Value, generate_furigana_custom, generate_furigana
from utils_html import get_reading_html, get_unimportant_reading_html

options = {
    'quiet': False,
    'disable-smart-shrinking': True,
    'page-size': 'A4',
    'margin-top': '10mm',
    'margin-bottom': '10mm',
    'margin-left': '10mm',
    'margin-right': '10mm',
    'print-media-type': None,
}

font = ''
with open('misc/font_base64.txt', 'r', encoding='UTF-8') as file:
    font = file.read()


def get_reading(item, type):
    result = ",&emsp; ".join(map(get_reading_html, item.get(type).get_equal(0)))
    additional = ",&emsp;".join(map(get_unimportant_reading_html, item.get(type).get_below(1)))
    if result and additional:
        return result + ",&emsp;" + additional
    if result or additional:
        return result + additional
    return "-"


# Generate a PDF file with kanji, on'yomi, kun'yomi, and example words
def generate(name, data, radicals, path_getter, is_debug_run):
    if not data["modified"] and not is_debug_run:
        return False

    content_html = []
    keys = data["order"]
    content = data["content"]

    for key in keys:
        item = content[key]

        if item.get("kanji").significance > 0:
            continue

        onyomi = get_reading(item, "onyomi")
        kunyomi = get_reading(item, "kunyomi")

        kanji_alive = retrieve_row_kanjialive_url(item)
        link_html = f'<a style="font-size: 8pt; float: right;" href="{kanji_alive}">{kanji_alive}</a>'

        vocabulary_now = []
        vocabulary_deck = []
        vocabulary_future = []

        vocabulary_content = item.vocabulary()
        vocab_row_style = "line-height: 18pt;"

        for i in range(len(vocabulary_content)):
            vocab_item = vocabulary_content[i]

            style_usage = "font-size: 10pt"
            class_left = "bl"
            class_right = "br"
            if i == len(vocabulary_content) - 1:
                class_right += " bb"
                class_left += " bb"

            target_list = vocabulary_now
            word = vocab_item.get('tango')
            if word.significance == 1:
                class_right += " deck"
                class_left += " deck"
                target_list = vocabulary_deck
                style_usage = "font-size: 8pt"
                vocab_row_style = "line-height: 15pt;"

            elif word.significance > 1:
                class_right += " future"
                class_left += " future"
                target_list = vocabulary_future
                style_usage = "font-size: 8pt"
                vocab_row_style = "line-height: 15pt;"

            usage = list(map(generate_furigana, vocab_item.get("tsukaikata")))
            if len(usage):
                usage = (f'<div style="margin-top: 3px; {style_usage}">'
                         + f'</div><div style="{style_usage}">'.join(usage)
                         + '</div>')
            else:
                usage = ""

            target_list.append(f"""
        <tr style={vocab_row_style}>
            <td class="bl {class_left}">{generate_furigana(str(word))}</td>
            <td class="br {class_right}" colspan="2"><b>{vocab_item['imi']}</b>{usage}</td>
        </tr>""")

        content_html.append(f"""
<table>
    <tr>
        <td class="bt bl" style="text-align: center">{item["id"]}</td>
        <td class="bt br" colspan="2">{link_html}</td>
    </tr>
    <tr>
        <td class="kanji bl bb" rowspan="3">{item["kanji"]}</td>
        <td class="small-cell">音</td>
        <td class="br">{onyomi}</td>
    </tr>
    <tr>
        <td class="small-cell">訓</td>
        <td class="br">{kunyomi}</td>
    </tr>
    <tr>
        <td class="bb small-cell">意味</td>
        <td class="br bb"><b>{item["imi"]}</b></td> 
    </tr>
    {''.join(vocabulary_now)}
    {''.join(vocabulary_deck)}
    {''.join(vocabulary_future)}
</table>""")

    # Generate output HTML
    content_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Kanji Output</title>
    <style>
        @font-face {{
            font-family: 'Gen Jyuu Gothic';
            src: url('{font}') format('truetype');
        }}
        body {{
            font-family: 'Gen Jyuu Gothic', sans-serif;
        }}
        table {{
            border-collapse: collapse;
            border-spacing: 0;
            width: 100%;
            page-break-inside: avoid;
        }}
        tr {{
            page-break-inside: avoid;
        }}
        th, td {{
            border: 2px solid lightgray;
            padding: 3px 7px;
            text-align: left;
            vertical-align: middle;
        }}
        /* Todo ubuntu destroys the formatting :/ */
        th.bt, td.bt {{
            border-top: 2px solid lightgray;
        }}
        th.bb, td.bb {{
            border-bottom: 2px solid lightgray;
        }}
        th.br, td.br {{
            border-right: 2px solid lightgray;
        }}
        th.bl, td.bl {{
            border-left: 2px solid lightgray;
        }}
        .kanji {{
            text-align: center;
            font-weight: bold;
            font-size: 52pt;
            width: 120px;
            line-height: 1.4;
        }}
        .deck {{
            font-size: 10pt;
            color: #222222;
            line-height: 15pt;
        }}
        .future {{
            font-size: 10pt;
            color: #555555;
            line-height: 15pt;
        }}
        ruby {{
            line-height: 1;
        }}
        ruby rt {{
            visibility: visible !important;
            top: 3px;
            position: relative;
        }}
        .small-cell {{
            width: 50px;
        }}
    </style>
</head>
<body>
    {"<br>".join(content_html)}
</body>
</html>"""

    if not is_debug_run:
        # Define output path
        pdf_output_path = f"{path_getter(name)}/{name}.pdf"
        # Convert HTML to PDF using pdfkit
        pdfkit.from_string(content_html, pdf_output_path, options=options)

        # Could also output html
        # with open(f"{path_getter(name)}/{name}.html", "w", encoding="UTF-8") as file:
        #     file.write(content_html)

    return True
