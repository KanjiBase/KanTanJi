# Usage Notes:

This script is supposed to be run by automated pipeline connected to google sheets API:
 - setup env variables for access
   - `GOOGLE_SERVICE` secret to the google service API
   - `FOLDER_ID` unique folder ID to scan for excel sheets to parse
 - run main.py


For testing it is possible to just run `python main.py` without a setup, it will
load test data and generate test outputs to the root of the repository.