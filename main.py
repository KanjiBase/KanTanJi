import csv
import re
import traceback
import os
import json
import hashlib

my_secret = os.environ.get("GOOGLE_SERVICE")
folder_id = os.environ.get("FOLDER_ID")
my_secret = json.loads(my_secret) if my_secret else None


import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Set up Google API credentials
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly"
]
creds = Credentials.from_service_account_info(my_secret, scopes=SCOPES) if my_secret else None

# Initialize gspread and Google Drive API clients
client = gspread.authorize(creds) if creds else None
drive_service = build('drive', 'v3', credentials=creds) if client else None


def compute_hash(records):
    hash_obj = hashlib.md5()
    for row in records:
        # Convert each row to a string and encode it
        hash_obj.update(str(row).encode('utf-8'))
    return hash_obj.hexdigest()



# Function to find a folder in Google Drive by name and return its ID
def find_folder_id(folder_name):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])
    if not folders:
        print(f"No folder found with name: {folder_name}")
        return None
    else:
        folder_id = folders[0]['id']  # Take the first matching folder
        print(f"Found folder '{folder_name}' with ID: {folder_id}")
        return folder_id

# Function to list all Google Sheets in a specific folder
def list_sheets_in_folder(folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    sheets = results.get('files', [])
    if not sheets:
        print("No Google Sheets found in the folder.")
        return []
    else:
        print("Sheets found:")
        for sheet in sheets:
            print(f"- {sheet['name']} (ID: {sheet['id']})")
        return sheets

# Function to read and print content of all sheets in a folder
def read_sheets_in_folder():
    
    if drive_service is None:
        # test demo
        print("Google services not set up: using local test demo data.")
        with open('misc/test-data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
        raise Exception("Could not load test data!")
    
    previous_hashes = {}
    hash_file_path = 'misc/update_guard.json'
    if os.path.exists(hash_file_path):
        with open(hash_file_path, 'r') as f:
            previous_hashes = json.load(f)
    output = {}
    sheets = list_sheets_in_folder(folder_id)
    for sheet in sheets:
        sheet_id = sheet['id']
        google_sheet = client.open_by_key(sheet_id)
        print(f"\nReading '{sheet['name']}'...")
        for worksheet in google_sheet.worksheets():
            print(f"  Worksheet: {worksheet.title}")
            records = worksheet.get_all_values()

            # Convert the list of dictionaries to an array of arrays format
            if records:
                
                hash = previous_hashes.get(sheet_id, None)
                current_hash = compute_hash(records)

                if hash and hash == current_hash:
                    print("  Skip: hash matches previous version.")
                    continue
                previous_hashes[sheet_id] = current_hash
                
                # Extract each row's values in order
                rows = [list(row.values()) for row in records]
                # Combine headers and rows
                output[sheet['name']] = rows
            else:
                output[sheet['name']] = None
    with open(hash_file_path, 'w+') as f:
        json.dump(previous_hashes, f)
    return output
            
# Specify the folder name and read sheets


### Function to generate furigana in HTML format (only one character can have furigana)
##def generate_furigana(text):
##    # Match exactly one character followed by furigana in <>, and convert to <ruby> tags with hidden furigana
##    return re.sub(r'([^\s<>]{1})<([^>]+)>', r'<ruby>\1<rt style="visibility: hidden">\2</rt></ruby>', text)
##
### Function to remove furigana, leaving only the main character
##def remove_furigana(text):
##    # Match exactly one character followed by furigana in <>, and remove the furigana part
##    return re.sub(r'([^\s<>]{1})<([^>]+)>', r'\1', text)
##

# Function to generate furigana in HTML format (support both > and ＞ for furigana)
def generate_furigana(text):
    # Match exactly one character followed by furigana in <> or ＜＞ (supports both half-width and full-width)
    return re.sub(r'([^\s<>]{1})[<>＜＞]([^<>＜＞]+)[<>＜＞]', r'<ruby>\1<rt style="visibility: hidden">\2</rt></ruby>', text)

# Function to remove furigana, leaving only the main character
def remove_furigana(text):
    # Match exactly one character followed by furigana in <> or ＜＞ and remove the furigana part
    return re.sub(r'([^\s<>]{1})[<>＜＞]([^<>＜＞]+)[<>＜＞]', r'\1', text)

def process_row(row):
    item = {"onyomi": [], "kunyomi": [], "pdf-onyomi": [], "pdf-kunyomi": [], "url": [], "usage": [], "pdf-usage": [], "extra": [], "type": ""}
    import_kanji = False
    for i in range(0, len(row), 2):
        key = row[i]
        if type(key) == "string":
            key = (row[i]).strip()
        else:
            key = f"{key}"
        if len(key) < 1:
            continue
        if key[0] == "$":
            key = key[1:len(key)]
        value = row[i+1]
        if type(value) == "string":
            value = value.strip()
        else:
            value = f"{value}"

        if key == 'kanji':
            if len(value) != 1:
                print(f"ERROR kanji value '{value}' longer than 1")
            item["type"] = 'kanji'
            item["kanji"] = f"<div style=\"font-size: 30pt;\">{value}</div>"
            item["kanji_front"] = f"㉆ <div style=\"font-size: 32pt;\">{value}</div>"

            item["kanji_original"] = value
            import_kanji = True
            item["url"] = f"https://app.kanjialive.com/{remove_furigana(value)}"
            item["guid"] = 'k' + str( hash(value))
        elif key == 'ID':
            item["id"] = value
        elif key == 'onyomi':
            item["onyomi"].append(value)
            item["pdf-onyomi"].append(value)
        elif key == 'onyomi-':
            item["onyomi"].append(f"<span style=\"color: gray; font-size: 14pt;\">{value}</span>")
            item["pdf-onyomi"].append(f"<font color=\"gray\" size=\"10\"> {value} </font>")

        elif key == 'kunyomi':
            item["kunyomi"].append(value)
            item["pdf-kunyomi"].append(value)

        elif key == 'kunyomi-':
            item["kunyomi"].append(f"<span style=\"color: gray; font-size: 14pt;\">{value}</span>")
            item["pdf-kunyomi"].append(f"<font color=\"gray\" size=\"10\"> {value} </font>")

        elif key == 'imi':
            item["meaning"] = f"<div style=\"font-size: 26pt;\">{value}</div>"
            item["meaning_front"] = f"㉆ <div style=\"font-size: 26pt;\">{value}</div>"
            item["pdf-meaning"] = value

        
        elif key == 'tango':
            item["type"] = 'tango'
            item["word"] = f"<div style=\"font-size: 28pt;\">{generate_furigana(value)}</div>"
            item["pdf-word"] = value

            import_kanji = False
            item["guid"] = 'w' + str(hash(value))
            
        elif key == 'tsukaikata':
            item["usage"].append(f"<div style=\"color: gray; font-size: 14pt;\">{generate_furigana(value)}</div>")
            item["pdf-usage"].append(value)

        else:
            item["extra"].append(f"<div style=\"color: gray; font-size: 14pt;\"><b>{generate_furigana(key)}</b>: {generate_furigana(value)}</div>")  # Store unexpected fields in extra
    if not item.get("guid", False):
        print("IGNORES: invalid data:", row)
        return None, False
    item["guid"] += item["id"]

    return item, import_kanji


def detect_bom(file_path):
    with open(file_path, 'rb') as file:
        # Read the first 4 bytes to check for BOM
        first_bytes = file.read(4)

    # Detect the BOM and return the appropriate encoding
    if first_bytes.startswith(b'\xef\xbb\xbf'):
        return "utf-8-sig"  # UTF-8 BOM
    elif first_bytes.startswith(b'\xff\xfe\x00\x00'):
        return "utf-32-le"  # UTF-32 Little Endian BOM
    elif first_bytes.startswith(b'\x00\x00\xfe\xff'):
        return "utf-32-be"  # UTF-32 Big Endian BOM
    elif first_bytes.startswith(b'\xff\xfe'):
        return "utf-16-le"  # UTF-16 Little Endian BOM
    elif first_bytes.startswith(b'\xfe\xff'):
        return "utf-16-be"  # UTF-16 Big Endian BOM
    else:
        return "utf-8"  # Default to UTF-8 if no BOM is found


# Function to read the CSV data
def read_kanji_csv(key, data):

    import_kanji = False
    reveal_furigana = "<script>['click', 'touchstart'].forEach(event => document.addEventListener(event, () => document.querySelectorAll('ruby rt').forEach(rt => rt.style.visibility = 'visible')));</script>"
    separator = f"<br><hr style=\"border: 1px solid gray\"><b style=\"font-size: 14pt; color: gray;\">{generate_furigana('使＜つか＞い方＜かた＞')}:</b><br>"

    output = []
    cards = []
    cards_translation = []
    name = f"KanTanJi::{key}"
    for row in data:
        (item, import_kanji) = row

        if not item:
            continue
            
        ttype = item.get("type")

        #mingle cards together
        if import_kanji:
            # Move first kanji -> translation and then others to the output
            output.extend(cards)
            output.extend(cards_translation)
            cards = []
            cards_translation = []
        extra = "".join(item.get("extra", []))
        if extra:
            extra = "<br>" + extra

        usage_lines = "".join([f"<div>{usage}</div>" for usage in item.get("usage", [])])
        if usage_lines:
            usage_lines = "<br>" + usage_lines
        if extra or usage_lines:
            # usage lines come first, add separator
            usage_lines = separator + usage_lines
                
        if ttype == "kanji":
            onyomi = "　".join(item.get("onyomi", []))  # Concatenate onyomi with a long space
            kunyomi = "　".join(item.get("kunyomi", []))  # Concatenate kunyomi with a long space

            if onyomi:
                onyomi = f"<span>Onyomi: {onyomi}</span>"
            if kunyomi:
                kunyomi = f"<span>Kunyomi: {kunyomi}</span>"
                if onyomi:
                    kunyomi = " &emsp;" + kunyomi
            
            cards.append([
                item['kanji_front'],
                
                f"<div>{onyomi + kunyomi}</div>" 
                f"{item['meaning']}"
                f"<br><br><div><a style=\"white-space: nowrap; font-size: 12pt;\" href=\"{item['url']}\">{item['kanji_original']} KanjiAlive</a></div>"
                + usage_lines + extra + reveal_furigana,

                item["guid"], name
            ])

            # Translation to kanji card
            cards_translation.append([
                item['meaning_front'],

                f"{item['kanji']}"
                f"<div>{onyomi + kunyomi}</div>"
                f"<br><br><div><a style=\"white-space: nowrap; font-size: 12pt;\" href=\"{item['url']}\">{item['kanji_original']} KanjiAlive</a></div>"
                + usage_lines + extra + reveal_furigana,

                item["guid"], name
            ])

        elif ttype == "tango":
            # Word to translation card
            cards.append([
                f"{item['word']}{reveal_furigana}",
                
                f"{item['meaning']}"
                + usage_lines + extra + reveal_furigana,

                item["guid"], name
            ])

            # Translation to word card

            cards_translation.append([
                f"{item['meaning']}",
                
                f"{item['word']}"
                + usage_lines + extra + reveal_furigana,

                item["guid"], name
            ])
        else:
            print(f"ERROR card invalid type {ttype}: {item} -> ignoring!")

    # consume leftowers
    output.extend(cards)
    output.extend(cards_translation)
    return output



# Write the Anki cards to a file with a custom separator
def write_anki_csv(output_file, output, separator='§'):
    with open(output_file, mode='w', encoding='utf-8') as file:
        # Write deck headers
        file.write(f"#separator:{separator}\n")
        file.write("#html:true\n")
        file.write(f"#guid column:3\n")
        file.write(f"#deck column:4\n")

        # Write the Anki cards
        for card in output:
            if len(card) != 4 or not all(card):
                print(f"WARNING: Card {card} not correctly formated - skipping!")
            else:
                file.write(separator.join(card) + '\n')



def parse_data(data):
    result = {}
    for key in data:
        output = []
        reader = data[key]
        for row in reader:
            item, import_kanji = process_row(row)

            if not item:
                continue

            output.append((item, import_kanji))
        result[key] = output
    return result









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


# Function to create inline furigana using <sup> tags in a Paragraph
def generate_furigana_paragraph(text, style, aditional=''):
    # Regular expression to match kanji and furigana
    pattern = r'([^\s<>]{1})[<>＜＞]([^<>＜＞]+)[<>＜＞]'

    # Replace kanji-furigana pairs with a <sup> (superscript) structure
    formatted_text = re.sub(pattern, r'\1<sup size="5">\2</sup>', text)

    if aditional:
        formatted_text = aditional + '<br/><br/>&nbsp;&nbsp;&nbsp;' + formatted_text

    # Return a formatted Paragraph with furigana and kanji inline
    return Paragraph(formatted_text, style)


font = 'misc/font.ttf'
pdfmetrics.registerFont(TTFont('NotoSans', font))
pdfmetrics.registerFont(TTFont('NotoSans-Bold', font))

# Generate a PDF file with kanji, on'yomi, kun'yomi, and example words
def generate_pdf(key, data):
    doc = SimpleDocTemplate(f"Kanji_{key}.pdf", pagesize=letter, topMargin=12, bottomMargin=10)
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
            if 'kanji_original' not in item:
                (item,_) = next(item_gen)
                continue  # Ensure the item contains the necessary fields
            
            # Kanji in large font
            kanji_paragraph = Paragraph(f"<font size=40>{item['kanji_original']}</font>", styles['KanjiHeader'])

            # Onyomi, Kunyomi, and Meaning in separate rows
            onyomi = item.get("pdf-onyomi", "")
            kunyomi = item.get("pdf-kunyomi", "")
            meaning = item.get("meaning", "")

            onyomi_paragraph = Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;".join(onyomi), styles['NormalNoto'])
            kunyomi_paragraph = Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;".join(kunyomi), styles['NormalNoto'])
            meaning_paragraph = Paragraph(meaning, styles['NormalNoto'])

            # KanjiAlive URL as a clickable link
            link_paragraph = Paragraph(f'<a href="{item["url"]}">{item["url"]}</a>', styles['NormalNoto'])
            
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
                while 'kanji_original' not in item:
                    if not item['type']:
                        (item,_) = next(item_gen)
                        continue
                    
                    word = generate_furigana_paragraph(item['pdf-word'], styles['NormalNoto'])
                    meaning = item['pdf-meaning']

                    usage_list = item.get("pdf-usage", [])
                    if len(usage_list) < 1:
                        usage_list.append("")  # trigger insertion of the word
                    
                    for usage in usage_list:
                        usage = generate_furigana_paragraph(usage, styles['NormalNoto'], meaning) if usage else Paragraph(meaning, styles['NormalNoto'])
                        current_pos = len(table_data)
                        # first row contains also word and meaning, the rest joined cells
                        if word and meaning:
                            table_data.append([word, usage, ''])
                            table_style.append(('SPAN', (1, current_pos), (2, current_pos)))
                            word = ''
                            meaning = ''
                        elif usage:
                            table_data.append([usage, '', ''])
                            table_style.append(('SPAN', (0, current_pos), (2, current_pos)))
                        
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


data = read_sheets_in_folder()
data = parse_data(data)

readme = """
# Kan<sup>Tan</sup>Ji &nbsp; 漢<sup>単</sup>字
Jednoduchá aplikace na trénování Kanji - pomocí PDF souborů a přidružených Anki balíčků.
<br><br>
## Sady Kanji:
<br>
"""


for key in data:
    try:
        anki = read_kanji_csv(key, data[key])
        write_anki_csv(f"anki-kanji-{key}.csv", anki, '|')
        print(f"Anki cards have been successfully saved to anki-kanji-{key}.")
    except Exception as e:
        print(f"Failed to write file anki-kanji-{key}", e)
        print(traceback.format_exc())


for key in data:
    try:
        generate_pdf(key, data[key])
        readme += f"<a href=\"pdf/Kanji_{key}.pdf\">Kanji {key}</a>"
        print(f"PDF file generated: Kanji_{key}.pdf")
    except Exception as e:
        print(f"Failed to write file Kanji_{key}.pdf", e)
        print(traceback.format_exc())


with open("README.md", mode='w', encoding='utf-8') as file:
    file.write(readme)
