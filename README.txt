DEPENDENCIES
------------------------------------------------------
Please install latest 64-bit versions of Ghostscript and Tesseract from:

https://ghostscript.com/releases/gsdnld.html
https://github.com/UB-Mannheim/tesseract/wiki

- Tesseract: select 'German', 'French' or other languages commonly found in documents that you will be scanning in 'Additional language data (download)' section. Everything else remains default.
Best quality language data sets cannot be downloaded from the installer. Those are found at: https://github.com/tesseract-ocr/tessdata_best

The project folder includes best models for 'English' and 'German'.
Copy these packs to 'C:\Program Files\Tesseract-OCR\tessdata' overwriting existing files.

Please NOTE that while using better language models can improve OCR results,
it can take significantly longer to process each document.

SETUP
------------------------------------------------------
1. Replace WORKING_DIRECTORY in 'config.yaml' with path to a folder that holds sample pdfs to OCR.
2. Replace BACKUP_DIRECTORY in 'config.yaml' with path to a folder that will hold backups of unscanned pdfs.

Please mind the single quotes ('') in config files.

- Scanned pdfs are be modified in place.
- Temporary .tmp files are deleted after each OCR run. In case of force-closing or errors in the program,
incomplete pdfs will be restored.
- Backups of unscanned pdfs are copied to the 'Backup' directory.

RUN
------------------------------------------------------
Click 'run.bat'. No need to install anything else.

RESULTS
------------------------------------------------------
If for some reason you get bad quality results from a normal OCR run,
you can open 'md5_log.csv' and mark a pdf as problematic: 1 for problematic, 0 for normal.
This will force OCR on the document.

Normally, the program performs detailed analysis and tries to keep existing text and vector objects,
which is good for mixed-content pdfs and is MOST SAFE for the output document overall.
However, it is less accurate with documents containing no text, and vector content, a.k.a full-image pdfs.
This option fully rasterizes the document, ignores existing text and vector objects,
and applies image processing to extract the most data --
it is more accurate with some documents but (!) can distort the final output. Apply only to problematic files, or files with abnormal OCR.

RUN ON STARTUP
------------------------------------------------------
1. Right-click 'run.bat', select 'Create shortcut'
2. Press 'Win + R'
3. Type in 'shell:startup'. A Startup folder will pop open
4. Drag and drop the newly created shortcut to the Startup folder