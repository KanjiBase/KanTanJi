from utils import generate_furigana, InputFormat, verb_prop_html

import markdown


def get_onyomi(item):
    return item.get("onyomi").join(", ")


def get_kunyomi(item):
    return item.get("kunyomi").join(", ")


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


id_dealer = 0


def get_word_html(word, color='blue'):
    global id_dealer
    id_dealer += 1

    props = word["properties"]
    props_html = "&nbsp;".join(map(verb_prop_html, props.get("verb", [])))

    def get_usage(usage_element):
        if not usage_element:
            return ""
        parts = str(usage_element).split("。")
        if len(parts) == 2:
            return f"""
            <div>
                <div style="margin-bottom: 5px;"><span lang="JA">{generate_furigana(parts[0])}</span></div>
                <div style="margin-bottom: 5px; color: #666;">{parts[1]}</div>
            </div>
            """
        return f"""
            <div>
                <div style="margin-bottom: 5px;">{generate_furigana(usage_element)}</div>
            </div>
            """

    usage_examples = props_html + ''.join(map(get_usage, word['usage']))
    if not usage_examples:
        return f"""
    <div class="bg-gradient-to-r from-{color}-50 to-{color}-100 rounded-lg shadow p-4 flex flex-col my-2">
        <div class="flex justify-between items-center">
          <div>
            <p class="text-lg text-2xl text-gray-800">{generate_furigana(word['word'])}</p>
            <p class="text-sm text-gray-600">{word['meaning']}</p>
          </div>
        </div>
    </div>
    """

    return f"""
    
    <div class="bg-gradient-to-r from-{color}-50 to-{color}-100 rounded-lg shadow p-4 flex flex-col my-2">
        <div class="flex justify-between items-center">
          <div>
            <p class="text-lg text-2xl text-gray-800">{generate_furigana(word['word'])}</p>
            <p class="text-sm text-gray-600">{word['meaning']}</p>
          </div>
            <!-- Arrow with onclick -->
            <button
            class="button-vocab-toggle text-gray-600 hover:text-gray-900 transform transition-transform duration-200 px-2"
            onclick="toggleExample('vocab{id_dealer}', this)"
              >
                ▼
              </button>
        </div>
        <div id="vocab{id_dealer}" class="button-vocab-example hidden mt-2 p-2 rounded bg-white text-gray-700 shadow">
          {usage_examples}
        </div>
    </div>
    """


def get_vocab_entries(item):
    return ''.join([f"""
        <div 
          class="flex-1 gap-4"
          style="min-width: 350px; max-width: 500px;"
        >   
            {''.join(map(lambda x: get_word_html(x, color), filter(lambda x: getattr(x, handler)('word', level), item.vocabulary())))}
        </div>
        """ for (level, color, handler) in [(0, 'green', 'get_equal'), (1, 'blue', 'get_equal'), (2, 'purple', 'get_below')]
    ])


def read_kanji_csv(key, data, radicals):
    output = {}

    def find_radical(id):
        for radical in radicals:
            if str(radical["id"]) == id:
                return radical
        return {}

    keys = data["order"]
    content = data["content"]
    for id in keys:
        item = content[id]

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
                    radical_html += f"<span>{rad_value.get('radical')} &emsp; {rad_value.get('meaning')}</span>"
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
    <div id="controls">
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
    </div>

    <!-- Hide/Show Button -->
    <button
      onclick="toggleControls(document.getElementById('controls').style.display === 'none')"
      class="my-3 mx-2 px-4 py-2 bg-indigo-600 text-white rounded-lg shadow hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
    >
      Přepnout ovládací prvky
    </button>
  </div>
</div>
<!-- Kanji Info Section -->
<div class="bg-white shadow-lg rounded-lg overflow-hidden md:flex">
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
                <p class="text-lg font-semibold text-gray-800">{get_onyomi(item)}</p>
            </div>
            <div>
                <p class="text-sm text-gray-500">Význam</p>
                <p class="text-lg font-semibold text-gray-800">{item['meaning']}</p>
            </div>
            <div>
                <p class="text-sm text-gray-500">Kunyomi</p>
                <p class="text-lg font-semibold text-gray-800">{get_kunyomi(item)}</p>
            </div>
            {radical_html}
        </div>
    </div>
</div>

<!-- Vocabulary Section -->
<div>
    <h3 class="text-2xl font-bold text-gray-800 mb-4">Slovní zásoba</h3>
    <div class="flex flex-col lg:flex-row gap-6 flex-wrap">
        {get_vocab_entries(item)}
        <!-- Historical Note Section -->
        <div class="note-container flex-1 lg:max-w-sm lg:ml-6 p-4 bg-green-100 rounded-lg shadow">
            <p class="text-gray-800">
                {
"".join([
    f"<div><strong><i>{generate_furigana(key)}<i></strong>: {generate_furigana(value)}</div>" if value.format == InputFormat.PLAINTEXT
    else f"<div>{markdown.markdown(generate_furigana(value))}</div>"
    for key, value in item.get("extra", {}).items()
])
                }
            </p>
        </div>
    </div>
</div>
<br>
<script>
    function toggleExample(exampleId, button) {{
        const example = document.getElementById(exampleId);
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
    }}
    function toggleControls(isHidden) {{
        const controls = document.getElementById('controls');
        isHidden = rememberValue('hideControls', isHidden) === 'true';
    
        if (isHidden) {{
          controls.style.display = 'block';
        }} else {{
          controls.style.display = 'none'; 
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
        sendHeightToParent();
    }}
    function rememberValue(key, value, defaultValue='true') {{
        if (value === undefined) {{
            value = (localStorage.getItem(key) || defaultValue);
        }} else {{
            localStorage.setItem('showFurigana', value);
        }}
        return String(value);
    }}
    toggleShowFurigana();
    toggleControls();
    showSentences();
    function sendHeightToParent() {{
      const height = document.documentElement.scrollHeight;
      window.parent && window.parent.postMessage({{ iframeHeight: height, test: "true" }}, "https://elf.phil.muni.cz");
    }}

    // Call the function when the iframe is loaded
    window.addEventListener("load", sendHeightToParent);

    // Call the function when the iframe content changes (optional for dynamic content)
    window.addEventListener("resize", sendHeightToParent);
</script>
        """)
    return output


import os


def generate(key, data, metadata, path_getter):
    radicals = metadata.get("radical")
    if not radicals:
        print("Warning: Radicals not defined. Skipping HTML outputs!")
        return False

    if not data["modified"] and not radicals["modified"]:
        return False

    output = read_kanji_csv(key, data, radicals["content"])

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
