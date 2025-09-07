from pathlib import Path
import pdfkit
from utils import generate_furigana, create_dataset_readme
# If you need any of your other utils (e.g., Value, retrieve_row_kanjialive_url), you can import them too.

# Compact PDF options (allow smart shrinking for tighter packing)
compact_pdf_options = {
    'quiet': False,
    'page-size': 'A4',
    'margin-top': '8mm',
    'margin-bottom': '8mm',
    'margin-left': '8mm',
    'margin-right': '8mm',
    # TIP: Do NOT disable smart shrinking — wkhtmltopdf will fit more content per page.
    # 'disable-smart-shrinking': True,  # <-- leave out or set to False to allow shrinking
    'print-media-type': None,
}

# Embed font (same mechanism as your existing generator)
font = ''
with open('misc/font_base64.txt', 'r', encoding='UTF-8') as f:
    font = f.read()


def _render_vocab_block(kanji_char, vocab_item):
    """
    Renders a single vocab block:
      KANJI | VOCAB | MEANING
      - sentence 1
      - sentence 2 (if any)
    """
    word = vocab_item.get('tango')
    meaning = vocab_item.get('imi')

    # Examples (use up to two, if present)
    usage_list = list(map(generate_furigana, vocab_item.get('tsukaikata')))
    examples_html = ""
    if usage_list:
        # Use at most 2 bullets (adjust if you want more)
        bullets = usage_list[:2]
        li = ''.join([f"<li>{u}</li>" for u in bullets])
        examples_html = f'<tr class="ex-row"><td class="ex-cell" colspan="3"><ul class="ex-list">{li}</ul></td></tr>'

    return f"""
<table class="vocab-block">
  <tr class="head-row">
    <td class="kanji-cell">{kanji_char}</td>
    <td class="vocab-cell">{generate_furigana(str(word))}</td>
    <td class="meaning-cell">{meaning}</td>
  </tr>
  {examples_html}
</table>
"""


def generate_content(name, data, radicals, path_getter, is_debug_run):
    """
    NEW: Generate a compact PDF focused ONLY on:
      KANJI | VOCAB | MEANING
      - example 1
      - example 2 (if exists)

    Args:
        name: output name (without extension)
        data: the same data structure your existing generator uses
        path_getter: function to resolve output directory
        is_debug_run: if True, don't write PDF to disk
    """
    # If nothing changed and not debugging, skip
    if not data.get("modified") and not is_debug_run:
        return False

    keys = data["order"]
    content = data["content"]

    blocks = []

    # Iterate through kanji entries
    for key in keys:
        item = content[key]

        # If you only want primary/now kanji, keep this check (mirrors your original):
        # Skip entries where the kanji significance > 0
        if item.get("kanji").significance > 0:
            continue

        kanji_char = item["kanji"]

        # Collect vocab items for this kanji
        vocabulary_content = item.vocabulary()

        # If you want to include ALL vocab regardless of significance, keep as is.
        # If you want to filter only current significance, uncomment this filter:
        # vocabulary_content = [v for v in vocabulary_content if v.get('tango').significance == 0]

        for vocab_item in vocabulary_content:
            blocks.append(_render_vocab_block(kanji_char, vocab_item))

    # Build compact HTML
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>{name}</title>
  <style>
    @font-face {{
      font-family: 'Gen Jyuu Gothic';
      src: url('{font}') format('truetype');
    }}
    html, body {{
      font-family: 'Gen Jyuu Gothic', sans-serif;
      font-size: 9pt;           /* Small base font for packing */
      line-height: 1.25;
      margin: 0;
      padding: 0;
    }}
    body {{
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}

    /* Make blocks as tight as possible */
    table.vocab-block {{
      width: 100%;
      border-collapse: collapse;
      border-spacing: 0;
      margin: 0;        
      page-break-inside: avoid; 
      border: 1px solid #e0e0e0;
    }}

    .head-row td {{
      padding: 2px 4px;
      vertical-align: middle;
      border-bottom: none;
      background-color: #e0e0e0;
    }}

    .kanji-cell {{
      width: 28px;   
      text-align: center;
      font-weight: 100;
      font-size: 8pt;  
      white-space: nowrap;
      line-height: 1;
    }}

    .vocab-cell {{
      width: 25%;
      padding-left: 6px;
      white-space: normal;
    }}

    .meaning-cell {{
      width: auto;
      text-align: left;
      white-space: normal;
      color: #111;
      font-weight: 700;
    }}

    .ex-row {{
      border-left: 12px solid #e0e0e0;
    }}
    .ex-row td {{
      padding: 2px 6px 4px 4px;
    }}
    .ex-list {{
      margin: 0;
      padding-left: 6px;
    }}
    .ex-list li {{
      margin: 0;
      padding: 0;
      line-height: 1;
      list-style-type: none;
    }}
    .ex-list ul {{
      list-style-type: none;
    }}

    ruby {{
      line-height: 1;
    }}
    ruby rt {{
      visibility: visible !important;
      top: 2px;
      position: relative;
      font-size: 7pt;
    }}
  </style>
</head>
<body>
  {"".join(blocks)}
</body>
</html>
"""


def generate(name, data, radicals, path_getter, is_debug_run):
    html = generate_content(name, data, radicals, path_getter, is_debug_run)

    if not is_debug_run:
        output_dir = path_getter(name)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        pdf_output_path = f"{output_dir}/{name}.pdf"
        pdfkit.from_string(html, pdf_output_path, options=compact_pdf_options)

        # # (Optional) also save the HTML for debugging
        # with open(f"{output_dir}/{name}.html", "w", encoding="UTF-8") as f:
        #     f.write(html)

    return True



def create_readme_entries(dataset_list: list):
    """
    (Unchanged helper) Build README entries for produced PDFs.
    """
    result = []
    for x in dataset_list:
        files = list(Path(x["path"]).glob('**/*.pdf'))
        result.append(create_dataset_readme(files, f"PDF Stránky {x['item']['name']}", ""))
    return result
