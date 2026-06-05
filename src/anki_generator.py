from pathlib import Path
from collections.abc import Callable

import hashlib
import json
import uuid
import tempfile
import os
import shutil
import time

from anki.collection import Collection
from anki.notes import Note
from anki.models import NotetypeDict
from anki.import_export_pb2 import (
    ExportAnkiPackageOptions,
    ExportLimit
)
import markdown


import config
from utils import generate_furigana, sanitize_filename, create_dataset_readme
from utils_data_entitites import InputFormat
from utils_html import parse_item_props_html
from i18n import T

# On-card user-facing strings live in `src/i18n.py` under the "anki" namespace.
# The JS init block JSON-dumps `_T` so client-side code can reference T.key;
# placeholders {drawn}/{total} are interpolated in JS via .replace().
_T = T['anki']

# -----------------------------------------------------------------------------
# HanziWriter (offline) integration for Japanese kanji stroke order practice
#
# This generator expects:
# 1) HanziWriter library file (vendored, no CDN): assets/hanziwriter/hanziwriter.min.js
# 2) Japanese stroke data files in HanziWriter JSON format (vendored):
#    assets/hanziwriter-data-ja/<KANJI>.json
#
# Recommended source for (2): mnako/hanzi-writer-data-ja (AnimCJK -> HanziWriter format)
# -----------------------------------------------------------------------------

# Stable across releases. Anki merges (does not replace) notetypes by id on
# import, so changing or renaming any of these once a deck has been shipped
# pollutes users' collections with ghost templates/fields. See
# misc/scripts/README.md "Avoiding the next template-pollution incident".
MODEL_ID = 1607392319
FIELD_IDS = [1001, 1002, 1003] # Static IDs for UID, Q, A
TEMPLATE_ID = 2001
HANZIWRITER_LIB_PATH = Path(os.environ.get("KANTANJI_HANZIWRITER_LIB", "assets/hanziwriter.min.js"))
HANZIWRITER_DATA_JA_DIR = Path(os.environ.get("KANTANJI_HANZI_DATA_JA", "assets/hanzi-writer-data-ja/data"))
# Inline the HanziWriter library into the card templates (Anki often won't load .js via <script src>)
try:
    _HW_LIB_CODE = HANZIWRITER_LIB_PATH.read_text(encoding="utf-8")
except Exception:
    _HW_LIB_CODE = ""
# Idempotency guard: the HanziWriter IIFE assigns window.HanziWriter once.
# On every Q->A flip AnkiDroid re-parses the page; without the guard the
# whole ~250 KB library is re-executed each time, causing GC pressure that
# can stall requestAnimationFrame and freeze the drawing canvas mid-stroke.
HANZIWRITER_LIB_INLINE = (
    f"<script>if(!window.HanziWriter){{\n{_HW_LIB_CODE}\n}}</script>"
    if _HW_LIB_CODE else ""
)


def _escape_json_for_html_script(text: str) -> str:
    """
    Safely embed JSON inside <script type="application/json">...</script>.
    The main pitfall is a literal '</script>' sequence.
    """
    return text.replace("</", "<\\/")


def _load_kanji_char_data_ja(ch: str) -> str:
    """
    Load Japanese kanji stroke data (HanziWriter JSON format) and return it as a JSON string.
    If missing, returns '{}' and the card will show a warning.
    """
    p = HANZIWRITER_DATA_JA_DIR / f"{ch}.json"
    if not p.exists():
        # Keep it non-fatal; user might still want to export the deck.
        print(f"W: {_T['stroke_data_missing']}'{ch}' at: {p}")
        return "{}"
    return p.read_text(encoding="utf-8")


def _hanziwriter_widget_html(ch: str, show_outline: bool, kind: str) -> str:
    """
    Inline widget HTML for one kanji.

    kind:
      - 'quiz'   -> interactive quiz for the FRONT side only
      - 'result' -> non-interactive result + correct output for the BACK side only

    Ordering (as requested):
      - cards[] (first) uses show_outline=True  (hint mode)
      - cards_translation[] (second) uses show_outline=False (recall mode)

    Vocabulary cards are not touched (no widget injected).
    """
    data_json = _escape_json_for_html_script(_load_kanji_char_data_ja(ch))
    outline = "1" if show_outline else "0"

    if kind == "quiz":
        return f"""
<div class="hw hw-quiz" data-hw-char="{ch}" data-hw-outline="{outline}">
  <div class="hw-grid"><div class="hw-target"></div></div>
  <div class="hw-status"></div>
  <script type="application/json" class="hw-data">{data_json}</script>
</div>
"""

    # kind == 'result'
    return f"""
<div class="hw hw-result" data-hw-char="{ch}" data-hw-outline="{outline}">
  <div class="hw-grid hw-composite">
    <div class="hw-correct"></div>
    <div class="hw-user"></div>
  </div>
  <div class="hw-status" style="margin-top:8px;"></div>
  <div style="margin-top:6px;font-size:9pt;color:gray;">{_T['correct_label']}</div>
  <script type="application/json" class="hw-data">{data_json}</script>
</div>
"""


def reading_label(value):
    reading = str(value).split('・')
    if len(reading) == 2:
        return f'<span class="rl copyable">{reading[0]}<span class="rldt">・{reading[1]}</span></span>'
    if len(reading) != 1:
        print('E: reading with multiple separators!', value)
    return f"""
<span class="rl copyable">{value}</span>
"""


def reading_label_unimportant(value):
    return f"""
<span class="rl rld copyable">{value}</span>
"""


css = """
.rl {padding:3px 9px;background:rgba(238,238,228,0.35);margin:0 5px;border-radius:3px;font-weight:bold;}
.rld {color: lightgray;font-weight:auto;background:rgba(238,238,228,0.25);}
.rldt {color: lightgray;}
.rlbl {visibility:hidden}
.qa {opacity:0.4;margin-bottom:15px}
.c {display: flex;flex-direction: column;justify-content: center; align-items: center;gap: 5px;width: 100%;text-align:center;}
.t {font-size:15pt;color: gray;font-weight: bold;}
.a {white-space: nowrap; font-size: 10pt;display:block;margin-bottom:10px;}
.o {background-color:rgba(188,188,188,0.1);color:gray!important;width: 100%;margin-top:25px;padding:5px 12px;border-radius:5px;text-align:left;}
.g {color:gray!important}
.u {background-color:rgba(50,50,50,0.2);border-radius:5px;padding:5px 12px;font-size:14pt;}

/* HanziWriter widget */
.hw {margin-top: 10px; width: 100%; display:flex; flex-direction:column; align-items:center;}
.hw-target {width: 240px; height: 240px;}
.hw-status {margin-top: 6px; font-size: 10pt; color: gray;}


/* HanziWriter practice block */
.hw { margin-top: 12px; }
.hw-grid {
  width: 260px;
  height: 260px;
  position: relative;
  border: 1px dashed rgba(242,242,242,0.25);
  border-radius: 6px;
  box-sizing: border-box;
}
.hw-grid::before, .hw-grid::after {
  content: "";
  position: absolute;
  left: 0; top: 0; right: 0; bottom: 0;
  pointer-events: none;
}
.hw-grid::before {
  /* center cross */
  background:
    linear-gradient(to right, rgba(242,242,242,0.18) 1px, transparent 1px) 50% 0 / 2px 100% no-repeat,
    linear-gradient(to bottom, rgba(242,242,242,0.18) 1px, transparent 1px) 0 50% / 100% 2px no-repeat;
}
.hw-target { width: 100%; height: 100%; }

/* Make user drawing thicker (SVG paths) */
.hw svg path {
  stroke-width: 28px !important;         /* tune: 20–45 */
  stroke-linecap: round !important;
  stroke-linejoin: round !important;
  vector-effect: non-scaling-stroke;     /* important if SVG gets scaled */
}
.hw .hw-user svg path {
  stroke-width: 15px !important;
}
.hw-target svg path {
  stroke-width: 14px !important;
  stroke-linecap: round !important;
  stroke-linejoin: round !important;
}

/* HanziWriter practice styling */
.hw { margin-top: 14px; }
.hw-grid { position: relative; width: 240px; height: 240px; margin: 0 auto; border: 2px dashed rgba(242,242,242,0.18); border-radius: 10px; }
.hw-grid:before, .hw-grid:after { content: ""; position: absolute; left: 50%; top: 0; width: 1px; height: 100%; background: rgba(242,242,242,0.10); transform: translateX(-0.5px); }
.hw-grid:after { left: 0; top: 50%; width: 100%; height: 1px; transform: translateY(-0.5px); }
.hw-target { position:absolute; inset:0; }
.hw-status { margin-top: 8px; font-size: 10pt; color: gray; }
.hw-panels { display:flex; gap: 22px; justify-content:center; margin-top: 14px; flex-wrap: wrap; }
.hw-panel-label { font-size: 9pt; color: gray; margin-top: 6px; }
.hw-glyph { width:240px; height:240px; display:flex; align-items:center; justify-content:center; }
.hw-glyph-char { font-size: 160px; line-height: 1; color: #f2f2f2; font-family: 'Hiragino Mincho ProN','Yu Mincho','MS Mincho',serif; }

/* Composite result overlay: red correct underneath, user drawing on top */
.hw-composite { position: relative; }
.hw-composite .hw-correct,
.hw-composite .hw-user {
  position: absolute;
  inset: 0;
}
.hw-composite .hw-correct { opacity: 1; }
.hw-composite .hw-user { pointer-events: none; } /* don't block taps */

/* Tap-to-copy (mirrors html_generator.py copyable styles) */
.copyable { position: relative; cursor: pointer; }
.copyable::after {
  content: 'Copied!'; position: absolute; top: -25px; right: -50px;
  background-color: #d9f9e6; color: #363636; font-size: 12px;
  padding: 2px 8px; border-radius: 4px;
  opacity: 0; visibility: hidden;
  transition: opacity 0.3s ease, visibility 0.3s ease;
  pointer-events: none;
}
.copyable.copied::after { opacity: 1; visibility: visible; }
"""

# Global init for HanziWriter inside Anki card HTML.
# Works for kanji cards only (cards that include .hw blocks).
# Vocabulary cards are unchanged and don't include .hw, so they won't run any drawing logic.
HANZIWRITER_INIT_JS = (
    "\n<script>\n(function() {\n var T = "
    + _escape_json_for_html_script(json.dumps(_T, ensure_ascii=False))
    + ";\n"
    + r"""
 function safeJsonParse(txt) {
  try { return JSON.parse(txt || '{}'); } catch(e) { return {}; }
 }
 function isBackSide() {
  return !!document.getElementById('hw-back-marker');
 }
 function initQuizBlocks() {
  var blocks = document.querySelectorAll('.hw.hw-quiz[data-hw-char]');
  if (!blocks || blocks.length === 0) return;
   blocks.forEach(function(block, idx) {
   if (block.dataset.hwInited === '1') return;
   block.dataset.hwInited = '1';
   var ch = block.dataset.hwChar;
   var outline = block.dataset.hwOutline === '1';
   var target = block.querySelector('.hw-target');
   var status = block.querySelector('.hw-status');
   var dataEl = block.querySelector('script.hw-data');
   if (!ch || !target || !status || !dataEl) return;

   var charData = safeJsonParse(dataEl.textContent);
   if (!charData || !charData.strokes) {
    status.textContent = T.stroke_data_missing + ch;
    return;
   }
   // Unique target id
   var tid = 'hw-target-' + idx + '-' + Math.floor(Math.random() * 1e9);
   target.setAttribute('id', tid);

   function parseRgb(rgb) {
    const m = rgb.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
    return m ? [parseInt(m[1],10), parseInt(m[2],10), parseInt(m[3],10)] : null;
   }

   function isDarkBg() {
    const bg = getComputedStyle(document.body).backgroundColor || "";
    const rgb = parseRgb(bg);
    if (!rgb) return false; // fallback: assume light
    const [r,g,b] = rgb;
    const lum = (0.2126*r + 0.7152*g + 0.0722*b) / 255;
    return lum < 0.5;
   }

   const dark = isDarkBg();
   const palette = dark ? {
    strokeColor:  "#f2f2f2",
    outlineColor: "rgba(255,255,255,0.22)",
    drawingColor: "#ffffff",
    highlightColor:"#ffd166",
    radicalColor: "#ffffff"
   } : {
    strokeColor:  "#111111",
    outlineColor: "rgba(0,0,0,0.18)",
    drawingColor: "#000000",
    highlightColor:"#f77f00",
    radicalColor: "#000000"
   };

   var writer = HanziWriter.create(tid, ch, {
    ...palette,
    width: 240,
    height: 240,
    padding: 10,
    showCharacter: false,
    showOutline: outline,
    charDataLoader: function() { return charData; }
   });

   var drawn = [];
   var mistakes = 0;
   var totalStrokes = (charData && charData.strokes) ? charData.strokes.length : null;
   var key = 'hw_last_' + ch + '_' + (outline ? 'o' : 'r');
   status.textContent = outline ? T.instruction_outline : T.instruction_recall;

   function saveProgress(complete) {
    try {
     localStorage.setItem(key, JSON.stringify({
      ch: ch,
      outline: outline,
      totalMistakes: mistakes,
      drawn: drawn,
      totalStrokes: totalStrokes,
      complete: !!complete
     }));
    } catch(e) {}
   }

   writer.quiz({
    showOutline: outline,
    showCharacter: false,
    highlightOnComplete: true,
    showHintAfterMisses: 1,
    onMistake: function(strokeData) {
     mistakes = strokeData && typeof strokeData.totalMistakes === 'number' ? strokeData.totalMistakes : (mistakes + 1);
     status.textContent = T.mistakes_prefix + mistakes;
     saveProgress(false);
    },
    onCorrectStroke: function(strokeData) {
     if (strokeData && strokeData.drawnPath && strokeData.drawnPath.pathString) {
      drawn.push(strokeData.drawnPath.pathString);
     }
     if (strokeData && typeof strokeData.totalMistakes === 'number') {
      mistakes = strokeData.totalMistakes;
     }
     saveProgress(false);
    },
    onComplete: function(summary) {
     if (summary && typeof summary.totalMistakes === 'number') {
      mistakes = summary.totalMistakes;
     }
     status.textContent = T.done_prefix + mistakes;
     saveProgress(true);
    }
   });
  });
 }

 function renderUserSvg(paths, strokeColor) {
  function inferBoxSize(ps) {
   var maxVal = 0;
   (ps || []).forEach(function(d) {
    if (!d) return;
    var nums = d.match(/-?\d*\.?\d+/g) || [];
    nums.forEach(function(n) {
     var v = Math.abs(parseFloat(n));
     if (!isNaN(v) && v > maxVal) maxVal = v;
    });
   });
   // Heuristic: if it's near 1024 assume 1024-space, otherwise use max (min 240) with padding.
   if (maxVal > 600) return 1024;
   if (maxVal < 10) return 240;
   return Math.max(240, Math.ceil(maxVal * 1.05));
  }

  var box = inferBoxSize(paths);
  var color = strokeColor || "#f2f2f2";
  var p = (paths || []).map(function(d) {
   return '<path d="' + d.replace(/"/g,'&quot;') + '" fill="none" stroke="' + color +
    '" stroke-width="22" stroke-linecap="round" stroke-linejoin="round"/>';
  }).join('');

  return ('<svg viewBox="0 0 ' + box + ' ' + box + '" width="240" height="240" style="display:block;margin:auto">' + p + '</svg>');
 }

 function initBackResults() {
  var blocks = document.querySelectorAll('.hw.hw-result[data-hw-char]');
  if (!blocks || blocks.length === 0) return;
  try {
   document.querySelectorAll('.qa').forEach(function(el){ el.style.display = 'none'; });
   document.querySelectorAll('.qa + br').forEach(function(el){ el.style.display='none'; });
   document.querySelectorAll('.qa + br + br').forEach(function(el){ el.style.display='none'; });
  } catch(e) { console.error(e); }

  var block = blocks[0];
  for (var i = 1; i < blocks.length; i++) {
   try { blocks[i].remove(); } catch(e) { console.error(e); }
  }

  (function(block, idx) {
   if (block.dataset.hwInited === '1') return;
   block.dataset.hwInited = '1';
   var ch = block.dataset.hwChar;
   var outline = block.dataset.hwOutline === '1';
   var userEl = block.querySelector('.hw-user');
   var correctEl = block.querySelector('.hw-correct');
   var status = block.querySelector('.hw-status');
   var dataEl = block.querySelector('script.hw-data');
   if (!ch || !userEl || !correctEl || !status || !dataEl) return;

   var charData = safeJsonParse(dataEl.textContent);
   var key = 'hw_last_' + ch + '_' + (outline ? 'o' : 'r');
   var saved = {};
   try { saved = safeJsonParse(localStorage.getItem(key) || '{}'); } catch(e) { console.error(e); }

   function parseRgb(rgb) {
    const m = rgb.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
    return m ? [parseInt(m[1],10), parseInt(m[2],10), parseInt(m[3],10)] : null;
   }
   function isDarkBg() {
    const bg = getComputedStyle(document.body).backgroundColor || "";
    const rgb = parseRgb(bg);
    if (!rgb) return false;
    const [r,g,b] = rgb;
    const lum = (0.2126*r + 0.7152*g + 0.0722*b) / 255;
    return lum < 0.5;
   }
   const dark = isDarkBg();
   const palette = dark ? {
    userInk: "#f2f2f2",
    correctRed: "rgb(255, 80, 80)"
   } : {
    userInk: "#111111",
    correctRed: "rgb(200, 0, 0)"
   };

   var savedDrawn = (saved && Array.isArray(saved.drawn)) ? saved.drawn : null;
   var drawnCount = savedDrawn ? savedDrawn.length : 0;
   if (saved && saved.complete === false) {
    var total = saved.totalStrokes;
    status.textContent = total
     ? T.unfinished_with_total.replace('{drawn}', drawnCount).replace('{total}', total)
     : T.unfinished_no_total.replace('{drawn}', drawnCount);
   } else if (saved && typeof saved.totalMistakes === 'number') {
    status.textContent = T.result_prefix + saved.totalMistakes;
   } else {
    status.textContent = T.mistakes_unknown;
   }

   if (drawnCount > 0) {
    userEl.innerHTML = renderUserSvg(savedDrawn, palette.userInk);
   } else {
    userEl.innerHTML = '<div style="color:gray;font-size:10pt;">' + T.no_drawing + '</div>';
   }

   try { localStorage.removeItem(key); } catch(e) {}

   var cid = 'hw-correct-' + idx + '-' + Math.floor(Math.random() * 1e9);
   correctEl.setAttribute('id', cid);
   correctEl.innerHTML = ''; 
   try {
    var w = HanziWriter.create(cid, ch, {
     width: 240,
     height: 240,
     padding: 10,
     showOutline: false,
     showCharacter: true,
     strokeColor: palette.correctRed,
     outlineColor: 'rgba(0,0,0,0)',
     drawingColor: 'rgba(0,0,0,0)',
     highlightColor: 'rgba(0,0,0,0)',
     charDataLoader: function() { return charData; }
    });
    if (w && typeof w.showCharacter === 'function') w.showCharacter();
   } catch(e) {
    correctEl.innerHTML = '<div style="color:gray;font-size:10pt;">' + T.cannot_render + '</div>';
    console.error(e);
   }
  })(block, 0);
 }

function initAll() {
 if (typeof HanziWriter === 'undefined') {
  setTimeout(initAll, 30);
  return;
 }
 if (isBackSide()) {
  initBackResults();
 } else {
  initQuizBlocks();
 }
}

setTimeout(initAll, 1);
})();
</script>
"""
)


# Tap-to-copy delegate. Capture-phase so it coexists with the bubble-phase
# furigana-toggle handler. Idempotent across Q->A re-parses.
#
# AnkiDroid's WebView usually does NOT expose navigator.clipboard (no secure
# context), so we fall back to a hidden-textarea + document.execCommand('copy').
COPY_JS = r"""
<script>
if(!window.__ktjCopyInit){
  window.__ktjCopyInit = true;
  function __ktjExtractText(node){
    if(node.nodeType===Node.TEXT_NODE) return node.textContent;
    if(node.nodeType===Node.ELEMENT_NODE && node.tagName!=='RT')
      return Array.from(node.childNodes).map(__ktjExtractText).join('');
    return '';
  }
  function __ktjCopy(text){
    // execCommand first: works in Anki Desktop's unfocused WebView (where
    // navigator.clipboard.writeText rejects with "Document is not focused")
    // and in AnkiDroid's non-secure WebView (where clipboard API is absent).
    try {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly','');
      ta.style.position = 'fixed';
      ta.style.top = '0';
      ta.style.left = '0';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      ta.setSelectionRange(0, text.length);
      var ok = document.execCommand('copy');
      document.body.removeChild(ta);
      if(ok) return Promise.resolve();
    } catch(e) { console.error(e); }
    if(navigator.clipboard && navigator.clipboard.writeText){
      try { return navigator.clipboard.writeText(text); } catch(e) { console.error(e); }
    }
    return Promise.reject(new Error('copy failed'));
  }
  document.addEventListener('click', function(e){
    var el = e.target.closest && e.target.closest('.copyable');
    if(!el) return;
    var txt = __ktjExtractText(el).trim();
    if(!txt) return;
    __ktjCopy(txt).then(function(){
      el.classList.add('copied');
      setTimeout(function(){ el.classList.remove('copied'); }, 1200);
    }).catch(console.error);
  }, true);
}
</script>
"""


# Furigana / hidden-label toggle. Each tap flips visibility of `ruby rt` and
# `.rlbl` so accidentally revealing them can be undone with another tap.
# The shown-state flag is reset on every card parse (sits outside the init
# guard) because each Q->A flip rebuilds the DOM with defaults hidden.
FURIGANA_TOGGLE_JS = r"""
<script>
window.__ktjFurShown = false;
if(!window.__ktjFurInit){
  window.__ktjFurInit = true;
  document.addEventListener('click', function(e){
    if(e.target.closest && e.target.closest('.copyable')) return;
    window.__ktjFurShown = !window.__ktjFurShown;
    var v = window.__ktjFurShown ? 'visible' : 'hidden';
    document.querySelectorAll('ruby rt, .rlbl').forEach(function(x){
      x.style.visibility = v;
    });
  });
}
</script>
"""


# Function to read the CSV data
def read_kanji_csv(key, data):
    usage_title = f"<b class='t'>{generate_furigana(_T['usage_label'])}:</b><br>"

    output = []
    cards = []
    cards_translation = []
    name = f"KanTanJi::{key}"

    keys = data["order"]
    content = data["content"]
    for key in keys:
        item = content[key]

        if item.get("kanji").significance > 0:
            continue

        output.extend(cards)
        output.extend(cards_translation)
        cards = []
        cards_translation = []

        extra = "".join([
            f"<div style=\"color: gray; font-size: 14pt;\"><b>{generate_furigana(key)}</b>: {generate_furigana(value)}</div>"
            if value.format == InputFormat.PLAINTEXT else
            f"<div><b>{markdown.markdown(generate_furigana(value))}</div>"

            for key, value in item.get("extra", {}).items()
        ])

        if extra:
            extra = f"<div class=\"o\">{extra}</div>"

        onyomi = "".join(map(reading_label, item.get("onyomi").get_equal(0)))
        onyomi += "".join(map(reading_label_unimportant, item.get("onyomi").get_below(1)))
        kunyomi = "".join(map(reading_label, item.get("kunyomi").get_equal(0)))
        kunyomi += "".join(map(reading_label_unimportant, item.get("kunyomi").get_below(1)))

        if onyomi and kunyomi:
            onyomi += "&emsp;&emsp;"

        # ---------------------------------------------------------------------
        # KANJI CARDS:
        # - cards[]: first in order => draw WITH hints (outline)
        # - cards_translation[]: second in order => draw WITHOUT hints (recall)
        # ---------------------------------------------------------------------
        hw_outline = _hanziwriter_widget_html(item['kanji'], show_outline=True, kind='quiz')
        hw_outline_result = _hanziwriter_widget_html(item['kanji'], show_outline=True, kind='result')
        hw_recall = _hanziwriter_widget_html(item['kanji'], show_outline=False, kind='quiz')
        hw_recall_result = _hanziwriter_widget_html(item['kanji'], show_outline=False, kind='result')

        cards.append([
            f"<div style=\"font-size: 32pt;\"><span class=\"copyable\">{item['kanji']}</span></div>"
            f"{hw_outline}",

            f"<div>{onyomi + kunyomi}</div>"
            f"<div style=\"font-size: 26pt;\"><span class=\"copyable\">{item['imi']}</span></div>"
            f"{hw_outline_result}{extra}",

            item["guid"], name, "kanji", 0
        ])

        # Translation to kanji card (recall / no outline)
        cards_translation.append([
            f"<div style=\"font-size: 26pt;\"><span class=\"copyable\">{item['imi']}</span></div>"
            f"<div>{onyomi + kunyomi}</div>"
            f"{hw_recall}",

            f"{hw_recall_result}<br><br><div>{onyomi + kunyomi}</div><div style=\"font-size: 30pt;\">"
            f"<div style=\"font-size: 26pt;\"><span class=\"copyable\">{item['imi']}</span></div>{extra}",

            item["guid"] + "-rev", name, "kanji", 0
        ])

        # ---------------------------------------------------------------------
        # VOCABULARY CARDS MUST STAY THE SAME
        # ---------------------------------------------------------------------
        for vocab_item in item.vocabulary():

            usage_lines = "".join(
                [f"<div>{generate_furigana(usage)}</div>" for usage in
                 vocab_item.get("tsukaikata")])

            # Extra fields
            extra = "".join([
                f"<div><b>{generate_furigana(key)}</b>: {generate_furigana(value)}</div>"
                if value.format == InputFormat.PLAINTEXT else
                f"<div><b>{markdown.markdown(generate_furigana(value))}</div>"

                for key, value in vocab_item.get("extra", {}).items()
            ])
            if usage_lines:
                usage_lines = f"<div class=\"u\">{usage_title}{usage_lines}</div>"
                if extra:
                    usage_lines = usage_lines + "<br><br>" + extra
            else:
                usage_lies = extra

            if usage_lines:
                usage_lines = f"<div class=\"o\">{usage_lines}</div>"

            # We also record vocab labels (tango:now  tango:deck  tango:other)
            # meaning the word is suitable to learn now, will appear later in the same deck with different kanji,
            # or will appear in the future
            vocab_def = vocab_item.get('tango')
            vocab_significance = vocab_def.significance

            word = f"<div style=\"font-size: 28pt;\"><span class=\"copyable\">{generate_furigana(str(vocab_def))}</span></div>"

            props_html = parse_item_props_html(vocab_item)

            # Word to translation card
            cards.append([
                f"{word}",

                f"<div class=\"rlbl\">{props_html}</div>"
                f"<div style=\"font-size: 26pt;\"><span class=\"copyable\">{vocab_item['imi']}</span></div>{usage_lines}",

                vocab_item["guid"], name, "tango", vocab_significance
            ])

            # Translation to word card
            cards_translation.append([
                f"<div style=\"font-size: 26pt;\"><span class=\"copyable\">{vocab_item['imi']}</span></div>",

                f"<div class=\"rlbl\">{props_html}</div>{word}{usage_lines}",

                vocab_item["guid"] + "-rev", name, "tango", vocab_significance
            ])

    # consume leftowers
    output.extend(cards)
    output.extend(cards_translation)
    return output


def generate_numeric_id_from_text(text, max_digits=16):
    # Generate a UUID from text (use SHA-256 if you want more robustness for long arbitrary text)
    namespace_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, text)  # Generate UUID
    sha_hash = hashlib.sha256(namespace_uuid.bytes + text.encode("utf-8")).hexdigest()

    # Convert hash to integer, then truncate to desired digit length
    numeric_id = int(sha_hash, 16) % (10 ** max_digits)
    return numeric_id


def create_anki_deck(key, reader, filename):
    temp_dir = tempfile.mkdtemp()
    col_path = os.path.join(temp_dir, "collection.anki2")
    col = Collection(col_path)

    try:
        deck_name = f"KanTanJi::{key}"
        deck_id = col.decks.id(deck_name)

        model = col.models.new("KanTanJi Anki Model")

        field_names = ["UID", "Q", "A"]
        for i, name in enumerate(field_names):
            fld = col.models.new_field(name)
            fld['id'] = FIELD_IDS[i]  # Force the field ID
            fld['ord'] = i
            col.models.add_field(model, fld)

        template = col.models.new_template("KanTanJi")
        template['id'] = TEMPLATE_ID  # Force the template ID

        template['ord'] = 0
        template['qfmt'] = (
                "<div class='c'>{{Q}}</div>"
                + FURIGANA_TOGGLE_JS
                + HANZIWRITER_LIB_INLINE + HANZIWRITER_INIT_JS + COPY_JS
        )
        template['afmt'] = (
                "<div id='hw-back-marker' style='display:none'></div><div class='c qa'>{{Q}}</div><br><br><div class='c'>{{A}}</div>"
                + FURIGANA_TOGGLE_JS
                + HANZIWRITER_LIB_INLINE + HANZIWRITER_INIT_JS + COPY_JS
        )
        col.models.add_template(model, template)
        model['css'] = css

        col.models.add(model)
        model['id'] = MODEL_ID
        col.models.update(model)

        model = col.models.get(MODEL_ID)
        col.models.set_current(model)

        for row in reader:
            note = col.new_note(model)
            note.guid = row[2]
            note.mod = int(time.time())
            note.fields[0] = row[2]  # UID
            note.fields[1] = row[0]  # Q
            note.fields[2] = row[1]  # A

            card_type, significance = row[4], row[5]
            if card_type == "kanji":
                note.add_tag("KanTanJi_Kanji")
            else:
                note.add_tag("KanTanJi_Tango")
                tag_map = {0: "KanTanJi_Learn_Now", 1: "KanTanJi_Learn_Deck"}
                note.add_tag(tag_map.get(significance, "KanTanJi_Learn_Future"))

            col.add_note(note, deck_id)

        # 4. Handle Media
        if HANZIWRITER_LIB_PATH.exists():
            # Use the absolute path to ensure Anki finds it during the temporary session
            col.media.add_file(str(HANZIWRITER_LIB_PATH.absolute()))

        options = ExportAnkiPackageOptions(
            with_scheduling=False,
            with_deck_configs=True,
            with_media=True,
            legacy=False
        )

        # Construct ExportLimit using deck_id
        limit = ExportLimit(deck_id=deck_id)

        col.export_anki_package(
            out_path=str(Path(filename).absolute()),
            options=options, limit=limit
        )
        # todo consider printing count

    finally:
        col.close()
        # Small delay to ensure SQLite releases the file handle before deletion
        time.sleep(0.1)
        shutil.rmtree(temp_dir)


def generate(key: str, data: dict, metadata: dict, folder_getter: Callable, is_debug_run: bool):
    # Anki packs only read data, so if not modified do not re-generate
    if not data["modified"] and not is_debug_run:
        return False
    rows = read_kanji_csv(key, data)

    # Split into two packs: default = kanji + significance=0 vocab,
    # advanced add-on = vocab with significance > 0 (Learn_Deck + Learn_Future).
    default_rows = [r for r in rows if r[4] == "kanji" or r[5] == 0]
    advanced_rows = [r for r in rows if r[4] == "tango" and r[5] > 0]

    if is_debug_run:
        return True

    folder = folder_getter(key)
    base = sanitize_filename(key)

    create_anki_deck(key, default_rows, f"{folder}/{base}.apkg")

    if advanced_rows:
        create_anki_deck(f"{key}::Advanced", advanced_rows,
                         f"{folder}/{base}-advanced.apkg")
    return True


def create_readme_entries(dataset_list: list):
    """Render per-subset Anki download blocks.

    One line per subset:
        - **<subset>**: <basic-link> · <advanced-link>

    Datasets often contain many subsets, so we keep each entry to a single
    bullet to avoid a vertical wall of text. The basic/advanced split is
    explained once at the section level (see main.py's README template).
    """
    result = []
    for x in dataset_list:
        files = list(Path(x["path"]).glob('**/*.apkg'))
        basic = sorted(f for f in files if not f.stem.endswith("-advanced"))
        advanced = sorted(f for f in files if f.stem.endswith("-advanced"))

        if not basic and not advanced:
            print("Warning: invalid dataset - no output files!",
                  f"{_T['package_prefix']} {x['item']['name']}", "")
            continue

        links = [f"<a href=\"{f}\">{_T['basic_pack_label']}</a>" for f in basic]
        links += [f"<a href=\"{f}\">{_T['advanced_pack_label']}</a>" for f in advanced]
        result.append(f" - **{x['item']['name']}**: &nbsp; " + " &nbsp; · &nbsp; ".join(links))
    return result
