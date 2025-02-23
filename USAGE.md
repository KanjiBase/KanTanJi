# Usage Notes:

This script is supposed to be run by automated pipeline connected to google sheets API:
 - setup env variables for access
   - `GOOGLE_SERVICE` secret to the google service API
   - `FOLDER_ID` unique folder ID to scan for excel sheets to parse
 - run main.py


For testing it is possible to just run `python main.py` without a setup, it will
load test data and generate test outputs to the root of the repository.

## Embedding
Content can be embedded via iframe using the iframe scripts. You can embed just the script tag,
or optionally embed the snipled below (suitable for WYSIWYG editors to support visual warning).
````html
<div id="kantanji" style="display: block; background: yellow; padding: 10px;">
    🚨 KANTANJI: DO NOT DELETE <script src="https://kanjibase.github.io/KanTanJi/misc/embed.js" data-target="[CONTENT URL ABSOLUTE OR RELATIVE TO STATIC FOLDER]"></script> 🚨
</div>
````