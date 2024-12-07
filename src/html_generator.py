from utils import structure_data_vocabulary_below_kanji, generate_furigana


def get_onyomi(item):
    return ", ".join(item.get("onyomi", [])) + ", ".join(item.get("onyomi-", []))


def get_kunyomi(item):
    return ", ".join(item.get("kunyomi", [])) + ", ".join(item.get("kunyomi-", []))



id_dealer = 0
def get_word_html(word):
    global id_dealer
    id_dealer += 1


    def get_usage(usage_element):
        if not usage_element or len(usage_element) < 1:
            return ""
        parts = usage_element.split("。")
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

    usage_examples = ''.join(map(get_usage, word['usage']))
    if not usage_examples:
        return f"""
    <div class="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg shadow p-4 flex flex-col gap-2">
        <div class="flex justify-between items-center">
          <div>
            <p class="text-lg text-2xl text-gray-800">{generate_furigana(word['word'])}</p>
            <p class="text-sm text-gray-600">{word['meaning']}</p>
          </div>
        </div>
    </div>
    """

    return f"""
    
    <div class="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg shadow p-4 flex flex-col gap-2">
        <div class="flex justify-between items-center">
          <div>
            <p class="text-lg text-2xl text-gray-800">{generate_furigana(word['word'])}</p>
            <p class="text-sm text-gray-600">{word['meaning']}</p>
          </div>
            <!-- Arrow with onclick -->
            <button
            class="button-vocab-toggle text-gray-600 hover:text-gray-900 transform transition-transform duration-200"
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

def read_kanji_csv(key, data):
    import_kanji = False
    reveal_furigana = "<script>['click', 'touchstart'].forEach(event => document.addEventListener(event, () => document.querySelectorAll('ruby rt').forEach(rt => rt.style.visibility = 'visible')));</script>"

    structured_data = structure_data_vocabulary_below_kanji(data)
    output = {}

    for id in structured_data:
        item = structured_data[id]
        # < link
        # type = "text/css"
        # href = "https://cdnjs.cloudflare.com/ajax/libs/Primer/21.1.1/primer.css" >
        # < script >
        # var
        # link = document.createElement("link");
        # link.rel = "stylesheet";
        # link.href = "https://cdnjs.cloudflare.com/ajax/libs/Primer/21.1.1/primer.css";
        # document.head.appendChild(link);
        # < / script >
        output[item['kanji']] = (f"""
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
  /* Parent container */
  .image-container {{
    position: relative;
    padding: 1em;
    display: flex;
    width: 200px;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    background: linear-gradient(135deg, #d4d4ff, #e0c4ff); /* Placeholder background */
    overflow: hidden;
  }}

  /* Placeholder styling */
  .image-container::before {{
    content: "";
    position: absolute;
    width: 40px;
    height: 40px;
    border: 4px solid #e0e0e0;
    border-top-color: #7c7cfd;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }}
  .image-container.image-loaded::before {{
    display: none;
  }}

  /* Image */
  .image-container img {{
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0;
    transition: opacity 0.3s ease-in-out;
  }}

  /* Reveal the image after loading */
  .image-container img:loaded {{
    opacity: 1;
  }}

  /* Spinning animation */
  @keyframes spin {{
    0% {{
      transform: rotate(0deg);
    }}
    100% {{
      transform: rotate(360deg);
    }}
  }}
</style>

<div class="min-h-screen bg-gradient-to-r from-blue-50 to-indigo-100 p-6 space-y-10">
<div class="p-4 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg shadow mb-4">
  <div class="flex justify-between items-center flex-row-reverse">
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
      class="px-4 py-2 bg-indigo-600 text-white rounded-lg shadow hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
    >
      Přepnout ovládací prvky
    </button>
  </div>
</div>
<!-- Kanji Info Section -->
<div class="bg-white shadow-lg rounded-lg overflow-hidden md:flex">
    <!-- Stroke Order Image -->
<div class="image-container">
  <img

        src="https://github.com/jcsirot/kanji.gif/blob/master/kanji/gif/150x150/{item['kanji']}.gif?raw=true"
alt="Kanji Stroke Order"
    onload="this.style.opacity='1'; this.parentElement.classList.add('image-loaded')"
  />
    </div>
    
    <!-- Kanji Details -->
    <div class="p-6 flex-1 space-y-4">
        <h2 class="text-2xl font-bold text-gray-700">大</h2>
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
            <div>
                <p class="text-sm text-gray-500">Radikál</p>
                <p class="text-lg font-semibold text-gray-800">Not Supported</p>
            </div>
        </div>
    </div>
</div>

<!-- Vocabulary Section -->
<div>
    <h3 class="text-2xl font-bold text-gray-800 mb-4">Slovní zásoba</h3>
    <div class="flex flex-col lg:flex-row gap-6 flex-wrap">
        <div 
          class="flex-1 grid gap-4"
          style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); align-items: start;"
        >   
            {''.join(map(get_word_html, item['vocabulary']))}
        </div>
        <!-- Historical Note Section -->
        <div class="note-container flex-1 lg:max-w-sm lg:ml-6 p-4 bg-green-100 rounded-lg shadow">
            <p class="text-gray-800">
                <strong>Poznámka:</strong> Not supported.
            </p>
        </div>
    </div>
</div>
<br>
<!-- Bonus Materials Section -->
<div>
    <h3 class="text-2xl font-bold text-gray-800 mb-4">Bonusové materiály</h3>
    <div class="p-6 bg-gradient-to-br from-green-100 to-green-50 rounded-lg shadow">
      <p class="text-gray-700">Additional study resources and materials will appear here!</p>
    </div>
</div>

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
    }}
    function showSentences(doShow) {{
        doShow = rememberValue('showSentences', doShow) === 'true';
        document.querySelectorAll('.button-vocab-toggle').forEach(element => {{
            element.textContent = doShow ? "▲" : "▼";
        }});
        document.querySelectorAll('.button-vocab-example').forEach(element => {{
            element.style.display = doShow ? "block" : "none";
        }});
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
</script>
        """)
    return output

import os
def generate_html(key, data):
    output = read_kanji_csv(key, data)

    folder_path = f"html-{key}"
    os.makedirs(folder_path, exist_ok=True)

    for k, v in output.items():
        # Create a file name for each HTML file
        file_name = f"file_{k}.html"
        file_path = os.path.join(folder_path, file_name)

        # Write the string content to the HTML file
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(v)
        print(f"Saved: {file_path}")
