import ocrmypdf

from functions import read_yaml


def ocr(i, o, pdf_id, problematic: bool) -> int:
    print("Scanning...")

    config = read_yaml("ocr.yaml")

    if int(config["skip_big"]) == 0:
        raise ValueError("'skip_big' argument cannot be 0. Please refer to 'ocr.yaml'.")

    redo_ocr = config["redo_ocr"]
    if problematic == True:
        print("File was identified as problematic. Forcing OCR...")
        redo_ocr = False

    if redo_ocr == True:
        # Disables image processing
        # remove_background = False
        force_ocr = False
        deskew = False
        clean = False
        unpaper_args = None
    else:
        # remove_background = True
        force_ocr = True
        deskew = config["deskew"]
        clean = config["clean"]
        unpaper_args = config["unpaper_args"]

    if config["logging"] == False:
        ocrmypdf.configure_logging(verbosity=-1)
        progress_bar = False
    else:
        ocrmypdf.configure_logging(verbosity=1)
        progress_bar = True

    return ocrmypdf.ocr(
        i,
        o,
        keywords=f"md5 {pdf_id}",
        #
        use_threads=config["use_threads"],
        # jobs=1,  # auto
        l=config["l"],
        redo_ocr=redo_ocr,
        force_ocr=force_ocr,
        # skip_text=skip_text,
        # oversample=75,  # ???
        skip_big=int(config["skip_big"]),
        # Image processing
        # remove_background=remove_background,  # NOT IMPLEMENTED
        deskew=deskew,
        rotate_pages=config["rotate_pages"],
        rotate_pages_threshold=config["rotate_pages_threshold"],
        clean=clean,
        unpaper_args=unpaper_args,
        #
        output_type=config["output_type"],
        optimize=config["optimize"],  # includes fast_web_view=0
        #
        sidecar=config["output_txt"],
        tesseract_timeout=config["tesseract_timeout"],  # ???
        progress_bar=progress_bar,
    )
