import re

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Flowable, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.fonts import addMapping
from reportlab.lib import fonts
from reportlab.platypus import Spacer

from utils import retrieve_row_kanjialive_url, Value


# Function to create inline furigana using <sup> tags in a Paragraph
def generate_furigana_paragraph(text, style, aditional=''):
    # Regular expression to match kanji and furigana
    pattern = r'([^\s<>]{1})[<>＜＞]([^<>＜＞]+)[<>＜＞]'

    # Replace kanji-furigana pairs with a <sup> (superscript) structure
    formatted_text = re.sub(pattern, r'\1<sup size="5">\2</sup>', str(text))

    if aditional:
        formatted_text = str(aditional) + '<br/><br/>&nbsp;&nbsp;&nbsp;' + formatted_text

    # Return a formatted Paragraph with furigana and kanji inline
    return Paragraph(formatted_text, style)


font = 'misc/font.ttf'
pdfmetrics.registerFont(TTFont('NotoSans', font))
pdfmetrics.registerFont(TTFont('NotoSans-Bold', font))

# Generate a PDF file with kanji, on'yomi, kun'yomi, and example words
def generate_pdf(key, data, path_getter):
    doc = SimpleDocTemplate(f"{path_getter(key)}/{key}.pdf", pagesize=letter, topMargin=12, bottomMargin=10)
    elements = []

    # Map bold font
    addMapping('NotoSans', 0, 0, 'NotoSans')  # Normal
    addMapping('NotoSans', 1, 0, 'NotoSans-Bold')  # Bold

    # Define custom paragraph styles with NotoSans
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SmallNoto', fontName='NotoSans', fontSize=6))
    styles.add(ParagraphStyle(name='NormalNoto', fontName='NotoSans', fontSize=11))
    styles.add(ParagraphStyle(name='BoldNoto', fontName='NotoSans-Bold', fontSize=11))
    styles.add(ParagraphStyle(name='KanjiHeader', fontName='NotoSans', fontSize=30))
    
    def item_generator(data):
        for item in data:
            yield item
            
    item_gen = item_generator(data)

    try:
        (item,_) = next(item_gen)
        while True:
            if 'kanji' not in item:
                (item,_) = next(item_gen)
                continue  # Ensure the item contains the necessary fields
            
            # Kanji in large font
            kanji_paragraph = Paragraph(f"<font size=40>{item['kanji']}</font>", styles['KanjiHeader'])

            # Onyomi, Kunyomi, and Meaning in separate rows
            onyomi_values = item.get("onyomi")
            onyomi = onyomi_values.get_equal(0)
            onyomi.extend([f"<font color=\"gray\" size=\"10\"> {x} </font>" for x in onyomi_values.get_below(1)])
            kunyomi_values = item.get("kunyomi", [])
            kunyomi = kunyomi_values.get_equal(0)
            kunyomi.extend([f"<font color=\"gray\" size=\"10\"> {x} </font>" for x in kunyomi_values.get_below(1)])

            meaning = f"<div style=\"font-size: 26pt;\">{item['meaning']}</div>"

            onyomi_paragraph = Paragraph(onyomi.join("&nbsp;&nbsp;&nbsp;&nbsp;"), styles['NormalNoto'])
            kunyomi_paragraph = Paragraph(kunyomi.join("&nbsp;&nbsp;&nbsp;&nbsp;"), styles['NormalNoto'])
            meaning_paragraph = Paragraph(meaning, styles['NormalNoto'])

            # KanjiAlive URL as a clickable link
            kanji_alive = retrieve_row_kanjialive_url(item)
            link_paragraph = Paragraph(f'<a href="{kanji_alive}">{kanji_alive}</a>', styles['NormalNoto'])
            
            # Create a structured table similar to your image
            table_data = [
                [item['id'], link_paragraph, ''],
                [kanji_paragraph, Paragraph('音', styles['NormalNoto']), onyomi_paragraph],
                ['', Paragraph('訓', styles['NormalNoto']), kunyomi_paragraph],
                ['', Paragraph('意味', styles['NormalNoto']), meaning_paragraph],
            ]

            table_style = [
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('SPAN', (0, 1), (0, 3)),
                ('SPAN', (1, 0), (2, 0)),  
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]

            try:
                (item,_) = next(item_gen)
                while 'kanji' not in item:
                    if not item['type']:
                        (item,_) = next(item_gen)
                        continue
                    
                    word = generate_furigana_paragraph(item['word'], styles['NormalNoto'])
                    meaning = item['meaning']

                    usage_list = item.get("usage").copy()
                    if len(usage_list) < 1:
                        usage_list.append(Value(False))  # trigger insertion of the word
                    
                    usage_extra_rows = 0
                    start_position = len(table_data)
                    for usage in usage_list:
                        usage = generate_furigana_paragraph(usage, styles['NormalNoto'], meaning) if usage else Paragraph(str(meaning), styles['NormalNoto'])
                        current_pos = len(table_data)
                        # first row contains also word and meaning, the rest joined cells
                        if word and meaning:
                            table_data.append([word, usage, ''])
                            table_style.append(('SPAN', (1, current_pos), (2, current_pos)))
                            word = ''
                            meaning = ''
                        elif usage:
                            usage_extra_rows += 1
                            table_data.append(['', usage, ''])
                            table_style.append(('SPAN', (1, current_pos), (2, current_pos)))
                    if usage_extra_rows > 0:
                        table_style.append(('SPAN', (0, start_position), (0, start_position + usage_extra_rows)))
                    (item,_) = next(item_gen)
            except StopIteration:
                pass


            # Create a table with the kanji on the left and information on the right
            table = Table(table_data, colWidths=[3*cm, 2*cm, 15*cm])
            table.setStyle(TableStyle(table_style))

            elements.append(KeepTogether(table))
            elements.append(Spacer(1, 12))  # Add space between each entry
    except StopIteration:
        # Generator is exhausted
        pass        
    if elements:  # Only build the document if there are elements
        doc.build(elements)
    else:
        print("No content to add to the PDF.")