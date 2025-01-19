import pdfkit
from utils import retrieve_row_kanjialive_url, Value, generate_furigana_custom, generate_furigana

options = {
    'quiet': False,
    'disable-smart-shrinking': True,
    'page-size': 'A4',
    'margin-top': '10mm',
    'margin-bottom': '10mm',
    'margin-left': '10mm',
    'margin-right': '10mm'
}

font = ''
with open('misc/font_base64.txt', 'r', encoding='UTF-8') as file:
    font = file.read()


def get_reading(text):
    return f'<span style="font-weight: bold">{text}</span>'


def get_unimportant_reading(text):
    return f'<span style="color: gray;">{text}</span>'


# Generate a PDF file with kanji, on'yomi, kun'yomi, and example words
def generate(name, data, radicals, path_getter):
    if not data["modified"]:
        return False

    content_html = []
    keys = data["order"]
    content = data["content"]

    for key in keys:
        item = content[key]

        onyomi = "&emsp;&emsp;".join(map(get_reading, item.get("onyomi").get_equal(0)))
        if onyomi:
            onyomi = onyomi + "&emsp;&emsp;"
        onyomi += "&emsp;&emsp;".join(map(get_unimportant_reading, item.get("onyomi").get_below(1)))
        kunyomi = "&emsp;&emsp;".join(map(get_reading, item.get("kunyomi").get_equal(0)))
        if kunyomi:
            onyomi = onyomi + "&emsp;&emsp;"
        kunyomi += "&emsp;&emsp;".join(map(get_unimportant_reading, item.get("kunyomi").get_below(1)))

        kanji_alive = retrieve_row_kanjialive_url(item)
        link_html = f'<a style="font-size: 8pt; float: right;" href="{kanji_alive}">{kanji_alive}</a>'

        vocabulary = []

        vocabulary_content = item.vocabulary()

        for i in range(len(vocabulary_content)):
            vocab_item = vocabulary_content[i]
            usage = list(map(generate_furigana, vocab_item.get("tsukaikata")))
            if len(usage):
                usage = ('<div style="margin-top: 3px; font-size: 10pt;">'
                         + '</div><div style="font-size: 10pt;">'.join(usage)
                         + '</div>')
            else:
                usage = ""

            class_left = "bl"
            class_right = "br"
            if i == len(vocabulary_content) - 1:
                class_right += " bb"
                class_left += " bb"
            vocabulary.append(f"""
    <tr>
        <td class="bl {class_left}">{generate_furigana(vocab_item['tango'])}</td>
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
        <td class="small-cell">訓</td>
        <td class="br">{onyomi}</td>
    </tr>
    <tr>
        <td class="small-cell">音</td>
        <td class="br">{kunyomi}</td>
    </tr>
    <tr>
        <td class="bb small-cell">意味</td>
        <td class="br bb"><b>{item["imi"]}</b></td> 
    </tr>
    {''.join(vocabulary)}
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
        ruby {{
            line-height: 1;
        }}
        ruby rt {{
            visibility: visible !important;
            top: 10px;
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

    # Define output path
    pdf_output_path = f"{path_getter(name)}/{name}.pdf"

    # Convert HTML to PDF using pdfkit
    pdfkit.from_string(content_html, pdf_output_path, options=options)

    # Could also output html
    with open(f"{path_getter(name)}/{name}.html", "w", encoding="UTF-8") as file:
        file.write(content_html)

    return True