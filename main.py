import traceback
from pathlib import Path
import os

from src.pdf_generator import generate_pdf
from src.anki_generator import generate_anki
from src.html_generator import generate_html
from src.utils import Value, ValueList, Entry


def process_row(row):
    # Todo solve extra
    item = Entry({"onyomi": ValueList(), "kunyomi": ValueList(), "usage": ValueList(), "extra": {}, "type": ""})
    import_kanji = False
    
    if len(row) < 1:
        return None, False
    
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


        key_significance = 0
        if key.endswith("-"):
            temp = key.rstrip('-')
            key_significance = len(key) - len(temp)
            key = temp


        if key == 'kanji':
            if len(value) != 1:
                print(f"ERROR kanji value '{value}' longer than 1")
            if item.get("kanji", False):
                print(f"ERROR kanji redefinition, only one value allowed!")
            else:
                item["type"] = 'kanji'
                item["kanji"] = Value(value, key_significance)
                import_kanji = True
                item["guid"] = 'k' + str(hash(value))
        elif key == 'id':
            if key_significance > 0:
                print("Warning: ID cannot have lesser significance! Ignoring the property.", value)
            item["id"] = Value(value, key_significance)

        elif key == 'onyomi':
            item["onyomi"].append(Value(value, key_significance))
        elif key == 'kunyomi':
            item["kunyomi"].append(Value(value, key_significance))
        elif key == 'imi':
            item["meaning"] = Value(value, key_significance)
        elif key == 'tango':
            item["type"] = 'tango'
            item["word"] = Value(value, key_significance)

            import_kanji = False
            item["guid"] = 'w' + str(hash(value))
        elif key == 'tsukaikata':
            item["usage"].append(Value(value, key_significance))

        else:
            # TODO does not support chaining
            item["extra"][key] = Value(value, key_significance)

    if not item.get("guid", False):
        print("IGNORES: invalid data:", row)
        return None, False
    item["guid"] += str(item["id"])

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


def try_read_data(getter, message, output, hash_guard, success_read):
    if not success_read:
        try:
            print(message)
            output, hash_guard = getter()
            return output, hash_guard, True
        except FileNotFoundError:
            pass
    return output, hash_guard, success_read



from src.read_input_google_api import read_sheets_google_api
from src.read_input_test_data import read_local_data


success_read = False
hash_guard = None
data = None
# Read data provides in desired order here
data, hash_guard, success_read = try_read_data(read_sheets_google_api,
                                   "Google Services: Reading data...", data, hash_guard, success_read)


# Fallback test data
uses_test_data = not success_read
data, hash_guard, success_read = try_read_data(read_local_data,
                                   "No data provider configured: using local test demo data.", data, hash_guard, success_read)

if not success_read:
    print("Error: Unable to read input data!")
    exit(1)

if not data:
    print("No data found to process: all is up to date.")
    exit(0)

if not hash_guard:
    raise ValueError("HashGuard must be provided by the input logics!")

data = parse_data(data)

readme = """
# Kan<sup>Tan</sup>Ji &nbsp; 漢<sup>単</sup>字
Jednoduchá aplikace na trénování Kanji - pomocí PDF souborů a přidružených Anki balíčků.
<br><br>
"""

def filepath_dealer(key):
    folder_path = f".temp/{key}/"
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def move_file_path_dealer(key, parent_folder):
    folder_path = f"{parent_folder}/{key}/"
    return folder_path


os.makedirs(".temp", exist_ok=True)

for key in data:
    try:
        generate_anki(key, data, filepath_dealer)
        print(f"Anki cards have been successfully saved:", key)
    except Exception as e:
        print(f"Failed to write file", key, e)
        print(traceback.format_exc())


for key in data:
    try:
        generate_pdf(key, data[key], filepath_dealer)
        print(f"PDF file generated:", key)
    except Exception as e:
        print(f"Failed to write file", key, e)
        print(traceback.format_exc())


for key in data:
    try:
        generate_html(key, data[key], filepath_dealer)
        print(f"HTML files generated:   ", key)
    except Exception as e:
        print(f"Failed to write HTML for dataset", key, e)
        print(traceback.format_exc())


target_folder_to_output = None

def clean_files(item, outdated):
    global target_folder_to_output
    target_folder_to_output = ".temp"
    try:
        name = item["name"]
        source = filepath_dealer(name)
        target = move_file_path_dealer(name, target_folder_to_output)
        print("Moving ", name, source, target)

        if outdated:
            Path(source).unlink(missing_ok=True)
            Path(target).unlink(missing_ok=True)
        else:
            target_dir = os.path.dirname(target)
            if target_dir:  # Non-empty path
                os.makedirs(target_dir, exist_ok=True)
            os.replace(source, target)
    except Exception as e:
        print(f"ERROR: Could not clean files for {item}", e)
        print(traceback.format_exc())


def get_readme_content():
    global target_folder_to_output
    readme = ""

    pdf_files = []
    anki_files = []
    html_files = []
    directory_list = [Path(x) for x in Path(target_folder_to_output).rglob('*') if x.is_dir()]
    for dir in directory_list:
        pdf_files.append(dir.glob("*.pdf"))
        anki_files.append(dir.glob("*.apkg"))
        html_files.append({
            "parent": dir.name,
            "data": dir.glob("*.html")
        })

    if len(pdf_files):
        readme += """
## PDF Sady Kanji:
"""
        files = [item for row in pdf_files for item in row]
        files.sort()

        for pdf_file in files:
            readme += f" - <a href=\"{target_folder_to_output}/{pdf_file.parent.name}/{pdf_file.name}\">Sada {pdf_file.parent.name}</a>\n"

    if len(anki_files):
        readme += """
## Anki Balíčky
"""
        files = [item for row in anki_files for item in row]
        files.sort()

        for anki_file in files:
            readme += f" - <a href=\"{target_folder_to_output}/{anki_file.parent.name}/{anki_file.name}\">Balíček {anki_file.parent.name}</a>\n"

    if len(html_files):
        readme += """
## HTML Materiály
"""
        html_files.sort(key=lambda x: x["parent"])

        for item in html_files:
            files = item["data"]
            readme += f"""
- <details>
  <summary>
  Sada {item["parent"]}
  </summary>
"""
            for file in files:
                readme += f"   - <a href=\"{target_folder_to_output}/{file.parent.name}/{file.name}\">Kanji {file.name}</a>\n"
            readme += "  </details>"
    return readme


hash_guard.save()
if not uses_test_data:
    target_folder_to_output = "static"
    hash_guard.for_entries(clean_files)

    # Write the README.md with links to the PDF files
    with open("README.md", mode='w+', encoding='utf-8') as file:
        file.write(readme + get_readme_content())
    print("README.md updated with PDF links.")
else:
    target_folder_to_output = ".test"
    hash_guard.for_entries(clean_files)
    print("Skipping writing README.md: test mode.")
    print(readme + get_readme_content())
