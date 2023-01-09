import os
import shutil
from datetime import datetime, date
import time

import traceback
import warnings
import filecmp

from threading import Thread
from pathlib import Path

from subprocess import SubprocessError, CalledProcessError, TimeoutExpired
from apscheduler.schedulers.blocking import BlockingScheduler

from ocrmypdf.exceptions import (
    MissingDependencyError,
    EncryptedPdfError,
    SubprocessOutputError,
    BadArgsError,
    # OutputFileAccessError,
)

import win32api, win32con

from pypdf import PdfReader, PdfWriter
from pypdf.generic import IndirectObject

from system_tray import SystemTray
from ocr import ocr
from functions import (
    check_ocrd,
    get_md5,
    ls,
    read_yaml,
    write_to_log,
    get_file_a_m_time,
    set_file_a_m_time,
    get_file_size_kb,
)


def decrypt() -> None:
    print("Searching for encrypted pdfs...")

    config = read_yaml("config.yaml")

    files = ls(path=config["WORKING_DIRECTORY"])

    count = 0
    for (name, path) in files:
        writer = PdfWriter()

        pdf = PdfReader(path)

        if pdf.is_encrypted == True:
            print(" ", f"'{name}' is encrypted.")

            try:
                print("   ", "Decrypting in place...")

                pdf.decrypt("")

                for page in pdf.pages:
                    writer.add_page(page)

                win32api.SetFileAttributes(path, win32con.FILE_ATTRIBUTE_NORMAL)
                with open(path, "wb") as f:
                    writer.write(f)
            except Exception:
                raise
            else:
                print(" ", f"'{name}' decrypted successfully.")

                count = count + 1

    print(f"Decrypted {count} file(s).")
    print()


def backup() -> None:
    config = read_yaml("config.yaml")

    # ---------------------------
    if config["WORKING_DIRECTORY"] == config["BACKUP_DIRECTORY"]:
        raise ValueError("Backup directory cannot be the same as working directory.")
    else:
        backup_directory_path = os.path.join(
            config["WORKING_DIRECTORY"], config["BACKUP_DIRECTORY"]
        )
    Path(backup_directory_path).mkdir(exist_ok=True, parents=True)

    # ---------------------------
    print("Creating backup of unscanned pdfs...")

    files = ls(config["WORKING_DIRECTORY"])

    count = 0
    for (name, path) in files:
        with open(path, "rb") as f:
            reader = PdfReader(f)

            pdf_id = reader.metadata.get("/Keywords", "")
            # creator = reader.metadata.get("/Creator", "")

        input_file = path
        relpath = os.path.relpath(input_file, config["WORKING_DIRECTORY"])
        output_file = os.path.join(backup_directory_path, relpath)

        if not isinstance(pdf_id, str) or not pdf_id.startswith(
            "md5"
        ):  # and not "ocrmypdf" in creator:
            try:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)

                if not os.path.exists(output_file) or not filecmp.cmp(
                    input_file, output_file, shallow=False
                ):
                    shutil.copy2(input_file, output_file)

                    print(" ", f"'{name}'")

                    count = count + 1
            except PermissionError:
                pass
            except Exception as e:
                print(str(e))

    print(f"Copied {count} file(s).")
    print()


first_run = True
run_counter = 0


def scan(scheduler, st) -> None:
    config = read_yaml("config.yaml")

    # Resets scheduler's run time for SystemTray.
    # Because a job's next scheduled run time is unknown (not exposed) before the first run,
    # We simulate this run to get the time but return before doing the actual work.
    # All consecutive jobs run normally.
    # ---------------------------
    status = f"Next OCR run on: {scheduler.get_jobs()[0].next_run_time.strftime('%B %d, %H:%M:%S')}"
    st.update_menu(status)

    global first_run
    if first_run == True:
        first_run = False

        if config["run_first_job_immediately_on_startup"] == False:
            return

    # ---------------------------
    global run_counter
    run_counter = run_counter + 1
    print("========================", f"Run {run_counter}", "========================")

    cleanup()

    try:
        backup()
    except ValueError as e:
        st.notify(str(e))

        time.sleep(1)

        return

    try:
        decrypt()
    except Exception as e:
        st.notify(str(e))

    # ---------------------------
    files = ls(config["WORKING_DIRECTORY"])

    if len(files) == 0:
        st.notify(f"No files to OCR in '{config['WORKING_DIRECTORY']}'")

        return

    # Start
    # ---------------------------
    for e, (name, path) in enumerate(files):
        print(f"'{path}'")

        with open(path, "rb") as f:
            reader = PdfReader(f)

            keywords = reader.metadata.get("/Keywords", "")

        if not isinstance(keywords, str) or not keywords.startswith("md5"):
            pdf_id = get_md5(path)

            print(
                "No ID embedded in PDF. Creating new ID from backup file's MD5:", pdf_id
            )
        else:
            pdf_id = keywords.split(" ")[1]

        date_ocrd, problematic = check_ocrd(pdf_id)

        print("PDF ID:", pdf_id)
        print("Date OCRed:", date_ocrd)

        # ---------------------------
        if not date_ocrd or problematic or config["force_rescan"]:
            if get_file_size_kb(path) > 4_000:
                st.notify(f"'{name}' may take longer to process: large file size.")

            today = date.today()

            input_file = path
            output_file = os.path.join(
                os.path.dirname(input_file),
                f"{name}.tmp",
            )

            try:
                os.rename(input_file, output_file)

                exit_code = ocr(
                    output_file, input_file, pdf_id, problematic=problematic
                )
            except MissingDependencyError as e:
                st.notify(str(e))

                time.sleep(2)

                # scheduler.shutdown(wait=False)

                break
            except EncryptedPdfError:
                st.notify(
                    f"Cannot OCR '{name}'. PDF is encrypted. Please remove any passwords, and the file will be rescanned automatically during the next run."
                )

                os.rename(output_file, input_file)
            except (
                SubprocessError,
                CalledProcessError,
                TimeoutExpired,
                SubprocessOutputError,
            ) as e:
                st.notify(
                    f"Error processing '{name}'. Restarting the job...",
                    passthrough=True,
                )

                os.rename(output_file, input_file)

                scheduler.get_jobs()[0].modify(next_run_time=datetime.now())
            except Exception as e:
                print(str(e))
                print(traceback.format_exc())

                st.notify(
                    f"Error processing '{name}'. Please refer to console output.",
                    passthrough=True,
                )

                os.rename(output_file, input_file)

                # scheduler.shutdown(wait=False)

                break
            else:
                # Success. Doesn't write to log if force-rescan is on to avoid duplicate entries
                if exit_code == 0 and not date_ocrd:
                    write_to_log(
                        st, line=f"{pdf_id},{today},{name.replace(',', '_')},0"
                    )
                elif exit_code == 0 and problematic:
                    write_to_log(
                        st,
                        line=f"{pdf_id},{today},{name.replace(',', '_')},0",
                        update=True,
                    )
                elif exit_code > 0:
                    st.notify(
                        f"Error processing '{name}'. Exit code {exit_code}.",
                        passthrough=True,
                    )

                    os.rename(output_file, input_file)

                # ---------------------------
                print("Setting original access and modification times from backup...")

                backup_directory_path = os.path.join(
                    config["WORKING_DIRECTORY"], config["BACKUP_DIRECTORY"]
                )

                backup_files = ls(path=backup_directory_path)

                for _, path in backup_files:
                    backup_md5 = get_md5(path)
                    if pdf_id == backup_md5:
                        init_atime, init_mtime = get_file_a_m_time(path)
                        set_file_a_m_time(input_file, init_atime, init_mtime)
                        break

                # a, m = get_file_a_m_time(input_file)
                # print("init_atime, init_mtime", init_atime, init_mtime)
                # print("a, m", a, m)
            finally:
                print()
        else:
            print(f"'{name}' was scanned on '{date_ocrd}'. Skipped.")
            print()

            continue

        if (e + 1) % int(config["clean_after"]) == 0:
            cleanup()

    # st.notify("OCR job finished.", passthrough=True)
    cleanup()


def cleanup() -> None:
    print("Removing temporary files...")

    config = read_yaml("config.yaml")

    files = ls(path=config["WORKING_DIRECTORY"], exts=["tmp"])

    count_rem = 0
    count_res = 0
    for (_, path) in files:
        pdf = path.rsplit(".", 1)[0]
        if os.path.isfile(pdf):
            try:
                win32api.SetFileAttributes(path, win32con.FILE_ATTRIBUTE_NORMAL)
                os.remove(path)

                count_rem = count_rem + 1
            except Exception as e:
                print(str(e))
        else:
            os.rename(path, pdf)

            count_res = count_res + 1

    print(f"Cleared {count_rem} file(s). Restored {count_res} file(s).")
    print()


# ---------------------------
def main():
    config = read_yaml("config.yaml")

    # Setup
    # ---------------------------
    st = SystemTray()

    # Turns off unrelated warnings
    warnings.simplefilter(action="ignore", category=Warning)

    scheduler = BlockingScheduler()

    scheduler.configure(
        job_defaults={
            "max_instances": 1,
        }
    )

    scheduler.add_job(
        scan,
        args=(scheduler, st),
        name="OCR",
        id="02",  # optional
        # ---------
        trigger="cron",
        year=config["cron"]["year"],
        month=config["cron"]["month"],
        week=config["cron"]["week"],
        day=config["cron"]["day"],
        day_of_week=config["cron"]["day_of_week"],
        hour=config["cron"]["hour"],
        minute=config["cron"]["minute"],
        second=config["cron"]["second"],
    )

    print("Started. OK.")
    print()

    # Run SystemTray
    # ---------------------------
    try:
        t = Thread(target=st.run, args=(scheduler,))
        t.start()

        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Stopping SystemTray...")
        st.stop()

        print("Stopping Scheduler...")
        scheduler.shutdown(wait=False)
    except Exception as e:
        print(e)

    # ---------------------------
    print("Exiting...")


if __name__ == "__main__":
    main()
