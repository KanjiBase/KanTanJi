import traceback
from pathlib import Path

from src.pdf_generator import generate_pdf
from src.anki_generator import generate_anki
from src.html_generator import generate_html

def process_row(row):
    item = {"onyomi": [], "kunyomi": [], "onyomi-": [], "kunyomi-": [], "usage": [], "pdf-usage": [], "extra": {}, "type": ""}
    import_kanji = False
    for i in range(0, len(row), 2):
        key = row[i]
        if type(key) == "string":
            key = (row[i]).strip().lower()
        else:
            key = f"{key}".lower()
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
            item["kanji"] = value
            import_kanji = True
            item["guid"] = 'k' + str( hash(value))
        elif key == 'id':
            item["id"] = value
        elif key == 'onyomi':
            item["onyomi"].append(value)
        elif key == 'onyomi-':
            item["onyomi-"].append(value)
        elif key == 'kunyomi':
            item["kunyomi"].append(value)
        elif key == 'kunyomi-':
            item["kunyomi"].append(value)
        elif key == 'imi':
            item["meaning"] = value
        elif key == 'tango':
            item["type"] = 'tango'
            item["word"] = value

            import_kanji = False
            item["guid"] = 'w' + str(hash(value))
            
        elif key == 'tsukaikata':
            item["usage"].append(value)

        else:
            item["extra"][key] = value

    if not item.get("guid", False):
        print("IGNORES: invalid data:", row)
        return None, False
    item["guid"] += item["id"]

    return item, import_kanji


def parse_data(data):
    result = {}
    for dataset_name in data:
        output = []
        reader = data[dataset_name]
        for row in reader:
            try:
                item, import_kanji = process_row(row)

                if not item:
                    continue

                output.append((item, import_kanji))
            except Exception as e:
                print(f"Error on line {row}", e)
                print(traceback.format_exc())
        output.sort(key=lambda x: str(x[0]["id"]) + x[0]["type"])
        result[dataset_name] = output
    return result


def try_read_data(getter, message, old_data, success_read):
    if not success_read:
        try:
            print(message)
            return getter(), True
        except FileNotFoundError:
            pass
    return old_data, success_read



from src.read_input_google_api import read_sheets_google_api
from src.read_input_test_data import read_local_data


success_read = False
data = None
# Read data provides in desired order here
data, success_read = try_read_data(read_sheets_google_api,
                                   "Google Services: Reading data...", data, success_read)


# Fallback test data
uses_test_data = not success_read
data, success_read = try_read_data(read_local_data,
                                   "No data provider configured: using local test demo data.", data, success_read)

if not success_read:
    print("Error: Unable to read input data!")
    exit(1)

if not data:
    print("No data found to process: all is up to date.")
    exit(0)

data = parse_data(data)

readme = """
# Kan<sup>Tan</sup>Ji &nbsp; 漢<sup>単</sup>字
Jednoduchá aplikace na trénování Kanji - pomocí PDF souborů a přidružených Anki balíčků.
<br><br>
"""



for key in data:
    try:
        generate_anki(key, data)
        print(f"Anki cards have been successfully saved to anki-kanji-{key}.")
    except Exception as e:
        print(f"Failed to write file anki-kanji-{key}", e)
        print(traceback.format_exc())


for key in data:
    try:
        generate_pdf(key, data[key])
        print(f"PDF file generated: Kanji_{key}.pdf")
    except Exception as e:
        print(f"Failed to write file Kanji_{key}.pdf", e)
        print(traceback.format_exc())


for key in data:
    try:
        generate_html(key, data[key])
        print(f"HTML files generated: Kanji_{key}.pdf")
    except Exception as e:
        print(f"Failed to write HTML for dataset", key, e)
        print(traceback.format_exc())


# Directory where the PDF files are stored
directory = Path(".")
files = directory.glob("*.pdf")
files = list(files)

directory = Path("pdf")
# Ensure the PDF directory exists
if directory.is_dir():
    files.extend(list(directory.glob("*.pdf")))

if len(files):
    readme += """
## Sady Kanji:
"""
    files.sort()
    
    existing_set = set()
    for pdf_file in files:
        try:
            # Generate a link for each PDF file found
            file_name = pdf_file.stem  # Get the file name without the extension
            if file_name in existing_set:
                continue
            existing_set.add(file_name)
            readme += f" - <a href=\"{directory}/{pdf_file.name}\">Set {file_name}</a>\n"
            print(f"PDF file found and linked: {pdf_file.name}")
        except Exception as e:
            print(f"Failed to process file {pdf_file.name}", e)
            print(traceback.format_exc())
else:
    print(f"Directory {directory} does not exist.")


directory = Path(".")
files = directory.glob("*.apkg")
files = list(files)

directory = Path("anki")
# Ensure the PDF directory exists
if directory.is_dir():
    files.extend(list(directory.glob("*.apkg")))

if len(files):
    readme += """
## Anki Packs
"""
    files.sort()
    
    existing_set = set()
    for anki_file in files:
        try:
            # Generate a link for each PDF file found
            file_name = anki_file.stem  # Get the file name without the extension
            
            if file_name in existing_set:
                continue
            existing_set.add(file_name)
            readme += f" - <a href=\"{directory}/{anki_file.name}\">Package {file_name}</a>\n"
            print(f"PDF file found and linked: {anki_file.name}")
        except Exception as e:
            print(f"Failed to process file {anki_file.name}", e)
            print(traceback.format_exc())
else:
    print(f"Directory {directory} does not exist.")

if not uses_test_data:
    # Write the README.md with links to the PDF files
    with open("README.md", mode='w+', encoding='utf-8') as file:
        file.write(readme)
    print("README.md updated with PDF links.")
else:
    print("Skipping writing README.md: test mode.")
    print(readme)

