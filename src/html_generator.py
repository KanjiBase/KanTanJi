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
    <div class="vocabulary-container">
        <div class="vocabulary-content">
            <div class="vocabulary-paragraph">
                <strong>
                    {generate_furigana(word['word'])}
                </strong>
                : {word['meaning']}
            </div>
        </div>
    </div>
    """

    return f"""
    <div class="vocabulary-container">
        <div class="vocabulary-content">
            <div class="vocabulary-paragraph">
                <strong>
                    {generate_furigana(word['word'])}
                </strong>
                : {word['meaning']}
            </div>
            <!-- Arrow with onclick -->
            <span id="arrowGreen{id_dealer}" class="expand-button" onclick="toggleExample('green{id_dealer}', 'arrowGreen{id_dealer}')">▼</span>
        </div>
        <div id="green{id_dealer}" class="vocabulary-detail">
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
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100..900&display=swap" rel="stylesheet">        
<style>
body {{
font-family: "Noto Sans JP", sans-serif;
  font-optical-sizing: auto;
  font-style: normal;
}}
.expand-button {{
transition: transform 0.3s; cursor: pointer; user-select: none;     padding: 5px 17px;
}}
.vocabulary-container {{
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 10px;
    box-shadow: rgba(0, 0, 0, 0.1) 0px 4px 8px;
    transition: transform 0.3s, background-color 0.3s;
    cursor: default;
    transform: scale(1);
    background: linear-gradient(175deg, #e0f8fa, #cdd3f6);
}}
.vocabulary-content {{
display: flex; justify-content: space-between; align-items: center;
}}
.vocabulary-paragraph {{
margin-bottom: 0; display: inline-flex; align-items: baseline; gap: 5px;
}}
.vocabulary-detail {{
    display: none; 
    border-radius: 8px;
    background: white;
    padding: 8px;
    opacity: 60%;
    margin-top: 8px;
}}
.kanji-container {{
    background: linear-gradient(175deg, #dadaff, #f6cde6); padding: 15px; border-radius: 10px; margin-bottom: 20px; display: flex; align-items: center; box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
    flex-wrap: wrap;
}}
.note-container {{
min-width: max-content;

flex: 1;
padding: 15px;
    border-radius: 10px;
    flex: 1;
    box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);
    font-style: italic;
    color: #656565;
    background: linear-gradient(45deg, #ececec, transparent);
}}
.kanji-subtitle {{
    color: black;
    display: inline-block;
    width: 100px;
    font-size: small;
    font-weight: 100;
}}
.kanji-detail {{
    display: block;
    font-size: 16pt;
    font-weight: 700;
}}
.kanji-column {{
    flex: 1;
    min-width: fit-content;
}}
.kanji-column-row {{
    margin: 7px 5px 7px 11px;
}}
.kanji-glyph-container {{
    margin-left: 20px; padding: 15px; text-align: center;
}}
.kanji-glyph {{
    width: 200px; height: 200px;
    mix-blend-mode: darken;
}}
.h3-title-separator {{
    margin-top: 0;
    margin-bottom: 15px;
    padding-bottom: 5px;
}}
.h3-title {{
    font-size: 20pt;
}}
.vocab-column {{
flex: 1;
min-width: max-content;
}}
.vocabulary-outer-container {{
display: flex; gap: 20px; justify-content: space-between; align-items: flex-start;
flex-wrap: wrap;
}}
@media only screen and (max-width: 645px){{
}}
</style>
<div>
<label for="showFurigana"><input type="checkbox" id="showFurigana" onchange="toggleShowFurigana(this.checked)"> Ukazovat furiganu </label>
</div>
<!-- Kanji Info Section --><h4 dir="ltr">
<div class="kanji-container">
<!-- Kanji Stroke Order with green border -->
     <div class="kanji-glyph-container kanji-column">
         <img src="https://github.com/jcsirot/kanji.gif/blob/master/kanji/gif/150x150/{item['kanji']}.gif?raw=true" alt="" class="kanji-glyph"
         role="presentation" class="img-fluid atto_image_button_middle">
     </div>    

    <div class="kanji-column">
         
         <div class="kanji-column-row"><span class="kanji-subtitle">Onyomi</span> <span class="kanji-detail">{get_onyomi(item)}</span></div>
         <div class="kanji-column-row"><span class="kanji-subtitle">Kunyomi</span> <span class="kanji-detail">{get_kunyomi(item)}</span></div>
         <div class="kanji-column-row"><span class="kanji-subtitle">Význam</span> <span class="kanji-detail">{item['meaning']}</span></div>
    </div>
    
    <div class="kanji-column">
         <div class="kanji-column-row"><span class="kanji-subtitle">Radikál</span> <span class="kanji-detail">not supported</span></div>
    
        <!-- Radicals as Interactive Elements todo
    <div style="margin-left: 20px; display: flex; gap: 10px; align-items: flex-start;">
         <span class="kanji-component" style="position: relative; color: #4b7d57; font-weight: bold; cursor: pointer; padding: 5px 10px; background-color: #e0f7e0; border-radius: 5px; border: 1px solid #4b7d57; transition: all 0.3s; transform-origin: center;">氺
    
    <span class="tooltip" style="visibility: hidden; opacity: 0; position: absolute; bottom: 120%; left: 50%; transform: translateX(-50%); background-color: #333; color: #fff; padding: 5px; border-radius: 5px; white-space: nowrap; font-size: 12px; transition: visibility 0.2s, opacity 0.2s;">
      Voda (したみず) - Radikál #85

      </span>
    </span>
     </div>-->
    
    </div>
   </div>
</h4>

<!-- JavaScript for Tooltip Hover Effect -->
<script>    
    // Tooltip visibility and hover effects for enlarging
    document.querySelectorAll('.kanji-component').forEach(function(element) {{
        element.addEventListener('mouseenter', function() {{
            const tooltip = this.querySelector('.tooltip');
            tooltip.style.visibility = 'visible';
            tooltip.style.opacity = '1';
            this.style.backgroundColor = '#c8e6c9'; // Slightly darker background on hover
            this.style.transform = 'scale(1.1)'; // Increase size on hover
            this.style.zIndex = '1'; // Ensure the element "pops out" on hover
        }});
        element.addEventListener('mouseleave', function() {{
            const tooltip = this.querySelector('.tooltip');
            tooltip.style.visibility = 'hidden';
            tooltip.style.opacity = '0';
            this.style.backgroundColor = '#e0f7e0'; // Reset background color
            this.style.transform = 'scale(1)'; // Reset size on hover out
            this.style.zIndex = '0'; // Reset stacking order on hover out
        }});
    }});
    
    function toggleShowFurigana(value) {{
        if (value === undefined) {{
            value = (localStorage.getItem('showFurigana') || 'true') === true;
        }} else {{
            localStorage.setItem('showFurigana', value ? 'true' : 'false')
        }}
        document.querySelectorAll('ruby rt').forEach(function(element) {{
            element.style.visibility = value ? 'visible' : 'hidden';
        }});
        return value;
    }}

    document.getElementById('showFurigana').checked = toggleShowFurigana();
</script>


<!-- Divider and Vocabulary Row -->
<h3 class="h3-title-separator">
    <strong class="h3-title">Slovní zásoba</strong>
</h3>

<div class="vocabulary-outer-container">

    <!-- Green Vocabulary Column -->
    <div class="vocab-column">
        {''.join(map(get_word_html, item['vocabulary']))}
    </div>


    <!-- Historical Note Section -->
    <div class="note-container">
        <p><strong>Poznámka: </strong> Not supported.
        </p>
    </div>

    <!-- JavaScript for Toggle Functionality -->
    <script>
        function toggleExample(exampleId, arrowId) {{
            const example = document.getElementById(exampleId);
            const arrow = document.getElementById(arrowId);

            if (example.style.display === "none" || !example.style.display) {{
                example.style.display = "block";
                arrow.textContent = "▲";
            }} else {{
                example.style.display = "none";
                arrow.textContent = "▼";
            }}
        }}
    </script>
</div>
<br>
<!-- Bonus Materials Section -->
<h3 class="h3-title-separator">
    <strong class="h3-title">Bonusové materiály</strong>
</h3>

<div>
    ...
</div>
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
