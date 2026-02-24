import re
from pathlib import Path

import markdown

from utils import generate_furigana, short_uid, create_dataset_readme
from utils_data_entitites import InputFormat
from utils_html import parse_item_props_html, get_reading_html, get_unimportant_reading_html


def get_reading(item, type):
    result = ",&emsp; ".join(map(get_reading_html, item.get(type).get_equal(0)))
    additional = ",&emsp;".join(map(get_unimportant_reading_html, item.get(type).get_below(1)))
    if result and additional:
        return result + ",&emsp;" + additional
    if result or additional:
        return result + additional
    return "-"


def wrap_html(title, head, content):
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {head}
</head>
<body>
{content}
</body>
</html>
    """


def inline_html(title, head, content):
    return f"""
{head}    
{content}
"""


def get_word_html(word, start='50', end='100'):
    uuid = short_uid(re.sub(r'\s+', '', word['tango']))

    props_html = parse_item_props_html(word)
    if props_html:
        props_html = f"<div class='my-2 vocab-properties'>{props_html}</div>"

    def get_usage(usage_element):
        if not usage_element:
            return ""
        parts = str(usage_element).rsplit("。", 1)
        if len(parts) == 2:
            return f"""
            <div>
                <div style="margin-bottom: 5px;"><span lang="JA">{generate_furigana(parts[0])}。</span></div>
                <div style="margin-bottom: 5px; color: #666;">{parts[1]}</div>
            </div>
            """
        return f"""
            <div>
                <div style="margin-bottom: 5px;">{generate_furigana(usage_element)}</div>
            </div>
            """

    usage_examples = ''.join(map(get_usage, word['tsukaikata']))
    if usage_examples:
        usage_examples = f"<div class=\"mt-2 p-2 rounded bg-white shadow\">{usage_examples}</div>"
    notes = get_notes_content(word, "mt-2")

    if not usage_examples and not notes:
        return f"""
    <div class="bg-gradient-to-r {start} {end} rounded-lg shadow p-4 flex flex-col my-2">
        <div class="flex justify-between items-center">
          <div>
            <p class="text-lg text-2xl text-gray-800 copyable cursor-pointer relative" 
            onclick="copyText(this)">{generate_furigana(word['tango'])}</p>
            <p class="text-sm text-gray-600">{word['imi']}</p>
          </div>
        </div>
        {props_html}
    </div>
    """

    return f"""
    <div class="bg-gradient-to-r {start} {end} rounded-lg shadow p-4 flex flex-col my-2">
        <div class="flex justify-between items-center cursor-pointer" onclick="toggleExample('vocab-{uuid}', this)">
            <div>
                <p class="text-lg text-2xl text-gray-800 copyable relative" 
                onclick="copyText(this)">{generate_furigana(word['tango'])}</p>
                <p class="text-sm text-gray-600">{word['imi']}</p>
            </div>
            <button class="button-vocab-toggle text-gray-600 hover:text-gray-900 
            transform transition-transform duration-200 px-2">▼</button>
        </div>
        {props_html}
        <div id="vocab-{uuid}" class="button-vocab-example hidden text-gray-700">
            {usage_examples}
            {notes}
        </div>
    </div>
    """


def get_vocab_entries(item):
    return f"""
<div 
  class="flex-1 gap-4"
  style="max-width: 400px;"
>   
    <span class="text-xl font-bold text-gray-800 mb-4">Povinná slovíčka</span>
    {''.join(map(
        lambda x: get_word_html(x, 'from-green-50', 'to-green-100'), 
        filter(lambda y: y.get_equal('tango', 0), item.vocabulary()))
    )}
</div>    
<div 
  class="flex-1 gap-4"
  style="max-width: 400px;"
>   
    <span class="text-xl font-bold text-gray-800 mb-4">Budou v sadě / Rozšiřující</span>
    {''.join(map(
        lambda x: get_word_html(x, 'from-blue-50', 'to-blue-100'), 
        filter(lambda y: y.get_equal('tango', 1), item.vocabulary()))
    )}
    {''.join(map(
        lambda x: get_word_html(x, 'from-purple-100', 'to-purple-300'), 
        filter(lambda y: y.get_below('tango', 2), item.vocabulary()))
    )}
</div>  
"""


def get_notes_content(item, cls=""):
    if cls:
        cls = f" class=\"{cls}\""
    return "".join([
        f"<div{cls}><strong><i>{generate_furigana(key)}</i></strong>: {generate_furigana(value)}</div>" if value.format == InputFormat.PLAINTEXT
        else f"<div>{markdown.markdown(generate_furigana(value))}</div>"
        for key, value in item.get("extra", {}).items()
    ])


def get_notes(item):
    notes = get_notes_content(item)
    if notes:
        return f"""
         <div class="note-container flex-1 lg:max-w-sm lg:ml-6 p-4 bg-green-100 rounded-lg shadow" style="height: fit-content;">
            <p class="text-gray-800">{notes}</p>
         </div>
        """
    return "<div></div>"


def read_kanji_csv(key, data, radicals):
    output = {}

    def find_radical(id):
        for radical in radicals:
            if radical["id"] == id:
                return radical
        return {}

    keys = data["order"]
    content = data["content"]

    for id in keys:
        item = content[id]

        if item.get("kanji").significance > 0:
            continue

        radical_exists = False
        radical_html = """
        <div>
            <p class="text-sm text-gray-500">Radikál</p>
            <p class="text-lg font-semibold text-gray-800">
        """
        rad_ref = item["references"].get("radical")
        if rad_ref:
            for ref in rad_ref:
                rad_value = find_radical(ref)
                if rad_value:
                    radical_html += f"<span>{rad_value.get('radical')} &emsp; {rad_value.get('imi')}</span>"
                    radical_exists = True
        if radical_exists:
            radical_html += """
            </p>
        </div>
        """
        else:
            radical_html = ""

        output[item['kanji']] = (f"""
<div class="min-h-screen space-y-10">
<div class="p-4 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg shadow mb-4">
  <div class="flex justify-between items-center flex-row-reverse flex-wrap">
    <!-- Label and Checkbox -->
    <div id="controls" style="display: none">
      <label for="showFurigana" class="flex items-center gap-2">
        <input 
          type="checkbox" 
          id="showFurigana" 
          class="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
          onchange="toggleShowFurigana(this.checked)"
        >
        <span class="text-gray-700 font-medium">Ukazovat furiganu</span>
      </label>
      <label for="showSentences" class="flex items-center gap-2">
        <input 
          type="checkbox" 
          id="showSentences" 
          class="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
          onchange="showSentences(this.checked)"
        >
        <span class="text-gray-700 font-medium">Vždy ukazovat věty</span>
      </label>
      <label for="showVocabProperties" class="flex items-center gap-2">
        <input 
          type="checkbox" 
          id="showVocabProperties" 
          class="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
          onchange="showVocabProperties(this.checked)"
        >
        <span class="text-gray-700 font-medium">Ukazovat vlastnosti slovíček</span>
      </label>
    </div>
  </div>
</div>
<!-- Kanji Info Section -->
<div class="bg-white shadow-lg rounded-lg overflow-hidden md:flex relative">
    <!-- Hide/Show Button -->
    <button
      id="toggleControls"
      onclick="toggleControls(document.getElementById('controls').style.display !== 'none')"
      class="my-3 mx-2 px-4 py-3 right-0 absolute bg-indigo-600 text-white rounded-lg shadow hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
    >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-gear-fill" viewBox="0 0 16 16">
            <path d="M9.405 1.05c-.413-1.4-2.397-1.4-2.81 0l-.1.34a1.464 1.464 0 0 1-2.105.872l-.31-.17c-1.283-.698-2.686.705-1.987 1.987l.169.311c.446.82.023 1.841-.872 2.105l-.34.1c-1.4.413-1.4 2.397 0 2.81l.34.1a1.464 1.464 0 0 1 .872 2.105l-.17.31c-.698 1.283.705 2.686 1.987 1.987l.311-.169a1.464 1.464 0 0 1 2.105.872l.1.34c.413 1.4 2.397 1.4 2.81 0l.1-.34a1.464 1.464 0 0 1 2.105-.872l.31.17c1.283.698 2.686-.705 1.987-1.987l-.169-.311a1.464 1.464 0 0 1 .872-2.105l.34-.1c1.4-.413 1.4-2.397 0-2.81l-.34-.1a1.464 1.464 0 0 1-.872-2.105l.17-.31c.698-1.283-.705-2.686-1.987-1.987l-.311.169a1.464 1.464 0 0 1-2.105-.872zM8 10.93a2.929 2.929 0 1 1 0-5.86 2.929 2.929 0 0 1 0 5.858z"/>
        </svg>
    </button>

    <!-- Stroke Order Image -->
    <div class="bg-gradient-to-br from-indigo-100 to-purple-100 p-6 flex items-center justify-center">
        <img
        src="https://raw.githubusercontent.com/KanjiBase/kanji.gif/refs/heads/master/kanji/gif/150x150/{item['kanji']}.gif"
        alt="Kanji Stroke Order"
        class="w-44 h-44 rounded-lg border border-gray-200 shadow"
        />
    </div>
    
    <!-- Kanji Details -->
    <div class="p-6 flex-1 space-y-4">
        <h2 class="text-2xl font-bold text-gray-700">{item['kanji']}</h2>
        <div class="grid grid-cols-2 gap-4">
            <div>
                <p class="text-sm text-gray-500">Onyomi</p>
                <p class="text-lg font-semibold text-gray-800">{get_reading(item, 'onyomi')}</p>
            </div>
            <div>
                <p class="text-sm text-gray-500">Význam</p>
                <p class="text-lg font-semibold text-gray-800">{item['imi']}</p>
            </div>
            <div>
                <p class="text-sm text-gray-500">Kunyomi</p>
                <p class="text-lg font-semibold text-gray-800">{get_reading(item, 'kunyomi')}</p>
            </div>
            {radical_html}
        </div>
    </div>
</div>

<!-- Vocabulary Section -->
<div>
    <div class="flex flex-col lg:flex-row gap-6 flex-wrap">
        {get_vocab_entries(item)}
        {get_notes(item)}
    </div>
</div>
<br>
<script>
    function extractText(node) {{
      if (node.nodeType === Node.TEXT_NODE) {{
        return node.textContent;
      }}
      
      if (node.nodeType === Node.ELEMENT_NODE && node.tagName !== 'RT') {{
        return Array.from(node.childNodes).map(child => extractText(child)).join('');
        }}
    }}
    function copyText(elem) {{
        let textToCopy = extractText(elem);
        navigator.clipboard.writeText(textToCopy).then(() => {{
          elem.classList.add('copied');
          setTimeout(() => {{
            elem.classList.remove('copied');
          }}, 1200);
        }})
    }}
    function toggleExample(exampleId, self) {{
        const example = document.getElementById(exampleId);
        const button = Array.from(self.children).find(child => child.tagName === 'BUTTON');
        if (example.style.display === "none" || !example.style.display) {{
            example.style.display = "block";
            button.textContent = "▲";
        }} else {{
            example.style.display = "none";
            button.textContent = "▼";
        }}
    }}
    function toggleShowFurigana(value) {{
        value = rememberValue('showFurigana', value) === 'true';
        document.querySelectorAll('ruby rt').forEach(element => {{
            element.style.visibility = value ? 'visible' : 'hidden';
        }});
        document.getElementById("showFurigana").checked = value;
    }}
    function toggleControls(isHidden) {{
        const controls = document.getElementById('controls');
        isHidden = rememberValue('hideControls', isHidden) === 'true';
    
        if (isHidden) {{
            controls.style.display = 'none';
        }} else {{
            controls.style.display = 'block'; 
        }}
        sendHeightToParent();
    }}
    function showSentences(doShow) {{
        doShow = rememberValue('showSentences', doShow) === 'true';
        document.querySelectorAll('.button-vocab-toggle').forEach(element => {{
            element.textContent = doShow ? "▲" : "▼";
        }});
        document.querySelectorAll('.button-vocab-example').forEach(element => {{
            element.style.display = doShow ? "block" : "none";
        }});
        document.getElementById("showSentences").checked = doShow;
        sendHeightToParent();
    }}
    function showVocabProperties(doShow) {{
        doShow = rememberValue('showVocabProperties', doShow) === 'true';
        document.querySelectorAll('.vocab-properties').forEach(element => {{
            element.style.display = doShow ? "block" : "none";
        }});
        document.getElementById("showVocabProperties").checked = doShow;
        sendHeightToParent();
    }}
    // Call functions to initialize state
    toggleShowFurigana();
    toggleControls();
    showSentences();
    showVocabProperties();
    
    // Helper functions
    function rememberValue(key, value, defaultValue='true') {{
        if (value === undefined) {{
            return (localStorage.getItem(key) || defaultValue);
        }} 
        value = String(value);
        localStorage.setItem(key, value);
        return value;
    }}
    function sendHeightToParent() {{
      setTimeout(() => {{
          const height = document.documentElement.scrollHeight;
          window.parent && window.parent.postMessage({{ iframeHeight: height, test: "true" }}, "https://elf.phil.muni.cz");
      }});
    }}

    // Call the function when the iframe is loaded
    window.addEventListener("load", sendHeightToParent);

    // Call the function when the iframe content changes (optional for dynamic content)
    window.addEventListener("resize", sendHeightToParent);
</script>
        """)
    return output


import os


def generate(key, data, metadata, path_getter, is_debug_run):
    radicals = metadata.get("radical")
    if not radicals:
        print("Warning: Radicals not defined. Skipping HTML outputs!")
        return False

    if not data["modified"] and not radicals["modified"] and not is_debug_run:
        return False

    output = read_kanji_csv(key, data, radicals["content"])

    if is_debug_run:
        return True

    did_save = False
    file_root = path_getter(key)
    for k, v in output.items():
        # Create a file name for each HTML file
        file_name = f"{k}.html"
        file_path = os.path.join(file_root, file_name)

        # Write the string content to the HTML file
        with open(file_path, 'w', encoding='utf-8') as file:
            # Todo: choose between inline-html and wrap-html

            file.write(wrap_html(k, f"""
<meta charset="UTF-8">
<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
<style>
rt {{
    font-size: 0.4em;
}}
.copyable::after {{
    content: 'Copied!';
    position: absolute;
    top: -25px;
    right: -50px;
    background-color: #d9f9e6;
    color: #363636;
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 4px;
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.3s ease, visibility 0.3s ease;
}}
.copyable.copied::after {{
  opacity: 1;
  visibility: visible;
}}
@media screen and (min-width: 1450px) {{
  .note-container {{
    min-width: 575px;
  }}
}}
@media screen and (max-width: 1450px) {{
  .note-container {{
    min-width: 95%;
  }}
}} 
</style> 
            """, v))
        did_save = True
    return did_save


def create_readme_entries(dataset_list: list):
    result = []
    for x in dataset_list:
        files = list(Path(x["path"]).glob('**/*.html'))
        result.append(create_dataset_readme(files, f"Kanji Stránky {x['item']['name']}"))
    return result
