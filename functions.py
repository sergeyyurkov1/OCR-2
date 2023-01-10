import os
import sys
import shutil
import hashlib
import functools
import time

import win32gui
import win32con

import pickle

from pathlib import Path

from csv import DictReader, DictWriter
from tempfile import NamedTemporaryFile

from ruamel.yaml import YAML


# Setup
# ---------------------------
yaml = YAML(typ="rt", pure=True)
yaml.preserve_quotes = True
yaml.default_flow_style = False

fw = win32gui.FindWindowEx(None, None, None, "Tesseract OCR")


FIELDNAMES = ["MD5/PDF ID", "Date OCRed", "Name", "Problematic/Force OCR"]


# ---------------------------
def get_file_size_kb(path: str) -> int:
    """Returns file size in kilobytes"""
    return Path(path).stat().st_size // 1_000


def get_file_a_m_time(path: str) -> tuple[float, float]:
    return (Path(path).stat().st_atime, Path(path).stat().st_mtime)


def set_file_a_m_time(path: str, atime: float, mtime: float) -> None:
    os.utime(path, (atime, mtime))


def hide_console() -> None:
    win32gui.ShowWindow(fw, win32con.SW_HIDE)


def close_console() -> None:
    win32gui.SendMessage(fw, win32con.WM_CLOSE)
    # win32gui.PostMessage(fw, win32con.WM_CLOSE)  # queue


def show_console() -> None:
    win32gui.ShowWindow(fw, win32con.SW_SHOW)


def load_blockchains() -> list:
    try:
        with open("blockchains.pkl", "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return []


def save_blockchains(blockchain: dict) -> None:
    with open("blockchains.pkl", "wb") as f:
        pickle.dump(blockchain, f)


def read_yaml(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.load(f)

    except FileNotFoundError:
        print(f"{path} is not found. Exiting.")
        sys.exit()


def write_yaml(path: str, data: dict) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
    except Exception as e:
        print(str(e))
        sys.exit()


def get_md5(path: str) -> str:
    with open(path, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()
        f.close()
        return md5


def retry(times=99999, message=None):
    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper_retry(*args, **kwargs):
            tries = 0
            success = False
            while tries < times and not success:
                try:
                    func(*args, **kwargs)
                    success = True
                except PermissionError:
                    if message != None:
                        st = args[0]
                        if st:
                            st.notify(message, passthrough=True)
                        else:
                            print(message)
                    time.sleep(15)
                    tries += 1

        return wrapper_retry

    return decorator_retry


@retry(
    message="Unable to update the MD5 log. Please close any program that uses the file."
)
def write_to_log(st, line: str, update: bool = False) -> None:
    if update == False:
        with open("md5_log.csv", "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.close()
    else:
        temporary_file = NamedTemporaryFile(mode="w", newline="", delete=False)
        dictwriter = DictWriter(temporary_file, fieldnames=FIELDNAMES)

        l = line.strip().split(",")
        id = l[0].strip()
        date = l[1].strip()
        name = l[2].strip()
        problematic = l[-1].strip()

        with open("md5_log.csv", "r", encoding="utf-8") as f, temporary_file:
            dictreader = DictReader(f, fieldnames=FIELDNAMES)

            for i in dictreader:
                if i[FIELDNAMES[0]] == id:
                    i[FIELDNAMES[1]] = date
                    i[FIELDNAMES[2]] = name
                    i[FIELDNAMES[-1]] = problematic

                dictwriter.writerow(i)

        shutil.move(temporary_file.name, "md5_log.csv")


def check_ocrd(pdf_id: str) -> tuple:
    try:
        with open("md5_log.csv", "r", encoding="utf-8") as f:
            lines = f.readlines()
            if len(lines) == 0:
                raise FileNotFoundError

            for e, line in enumerate(lines):
                if e == 0:
                    continue

                md5_date_ocrd = line.strip().split(",")

                md5 = md5_date_ocrd[0].strip()
                date_ocrd = md5_date_ocrd[1].strip()

                force_ocr = md5_date_ocrd[-1].strip()
                if force_ocr == "1":
                    problematic = True
                else:
                    problematic = False

                if md5 == pdf_id:
                    return (date_ocrd, problematic)
            return (None, None)
    except FileNotFoundError:
        with open("md5_log.csv", "w", encoding="utf-8") as f:
            f.write("MD5/PDF ID,Date OCRed,Name,Problematic/Force OCR" + "\n")
        return (None, None)


def ls(path: str = ".", all: bool = False, exts: list = ["pdf"]) -> list:
    config = read_yaml("config.yaml")
    backup_directory = config["BACKUP_DIRECTORY"].split("\\")[-1]
    files_recursive = []
    for root, dirs, files in os.walk(path):
        if backup_directory in dirs:
            dirs.remove(backup_directory)
        for name in files:
            if all == False:
                if name.rsplit(".", 1)[1].lower() in exts:
                    p = os.path.join(root, name)
                    files_recursive.append((name, p))
            else:
                p = os.path.join(root, name)
                files_recursive.append((name, p))
    return files_recursive


if __name__ == "__main__":
    pass
