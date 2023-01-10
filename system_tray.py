from datetime import datetime

from PIL import Image

from pystray import Icon, Menu, MenuItem

from functions import show_console, hide_console, close_console, read_yaml, write_yaml


class SystemTray:
    status = "OCR starting..."

    scheduler = None

    def __init__(self):
        # self.redo_ocr = read_yaml("ocr.yaml")["redo_ocr"]
        self.output_txt = read_yaml("ocr.yaml")["output_txt"]

        self.force_rescan = read_yaml("config.yaml")["force_rescan"]
        self.show_console = read_yaml("config.yaml")["show_console"]
        self.notifications = read_yaml("config.yaml")["notifications"]

        if self.show_console == False:
            hide_console()

        self.icon = Icon(
            "OCR",
            icon=self.get_image(),
            menu=Menu(
                MenuItem(
                    "Console",
                    action=self.console_handler,
                    checked=lambda MenuItem: self.show_console,
                ),
                MenuItem(
                    "Notifications",
                    action=self.notifications_handler,
                    checked=lambda MenuItem: self.notifications,
                ),
                Menu.SEPARATOR,
                MenuItem(
                    lambda text: self.status,
                    action=None,
                    checked=None,
                    enabled=False,
                ),
                # MenuItem(
                #     "Separate text, objects, and images; don't rasterize all",
                #     action=self.ro_handler,
                #     checked=lambda MenuItem: self.redo_ocr,
                #     enabled=False,
                # ),
                MenuItem(
                    "Force rescan everything (skip MD5 checks)",
                    action=self.fr_handler,
                    checked=lambda MenuItem: self.force_rescan,
                ),
                MenuItem(
                    "Output .txt",
                    action=self.ot_handler,
                    checked=lambda MenuItem: self.output_txt,
                ),
                Menu.SEPARATOR,
                MenuItem("Exit", action=self.exit_, checked=None),
            ),
        )

    # def ro_handler(self, Icon, MenuItem):
    #     self.redo_ocr = not MenuItem.checked
    #     self.icon.update_menu()

    #     ocr = read_yaml("ocr.yaml")
    #     ocr["redo_ocr"] = self.redo_ocr
    #     write_yaml("ocr.yaml", ocr)

    def ot_handler(self, Icon, MenuItem):
        self.output_txt = not MenuItem.checked
        self.icon.update_menu()

        ocr = read_yaml("ocr.yaml")
        ocr["output_txt"] = self.output_txt
        write_yaml("ocr.yaml", ocr)

    def fr_handler(self, Icon, MenuItem):
        self.force_rescan = not MenuItem.checked
        self.icon.update_menu()

        config = read_yaml("config.yaml")
        config["force_rescan"] = self.force_rescan
        write_yaml("config.yaml", config)

    def console_handler(self, Icon, MenuItem):
        self.show_console = not MenuItem.checked
        self.icon.update_menu()

        if self.show_console == True:
            show_console()
        elif self.show_console == False:
            hide_console()

        config = read_yaml("config.yaml")
        config["show_console"] = self.show_console
        write_yaml("config.yaml", config)

    def notifications_handler(self, Icon, MenuItem):
        self.notifications = not MenuItem.checked
        self.icon.update_menu()

    def get_image(self):
        return Image.open("isometric.png")

    def notify(self, message: str, passthrough=False) -> None:
        if passthrough or self.notifications == True:
            self.icon.notify(message[:255], "Tesseract")
        else:
            print("WARNING:", message)

    def update_menu(self, status):
        self.status = status
        self.icon.update_menu()

    def run(self, scheduler):
        self.scheduler = scheduler
        self.scheduler.get_jobs()[0].modify(next_run_time=datetime.now())

        self.icon.run()

    def stop(self):
        self.icon.stop()

    def exit_(self):
        self.stop()
        self.scheduler.shutdown(wait=False)
        close_console()
