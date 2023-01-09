import os
import subprocess
import tempfile
import shutil

import pytesseract, cv2

from pytesseract import Output
from pytesseract.pytesseract import TesseractError

from pypdf import PdfReader, PdfWriter

from functions import ls

import imutils
import cv2
import img2pdf


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class PdfPreprocessor:
    def __init__(self, path: str) -> None:
        self.images: list[tuple] | None = None

        self.td = tempfile.mkdtemp()

        # temporary directory + pdf name
        self.pdf = os.path.join(self.td, path.rsplit("\\", 1)[1])
        shutil.copy2(path, self.pdf)

    def _pdf_to_images(self, image_type="png") -> list:
        output = subprocess.run(
            [r".\poppler\bin\pdftocairo", f"-{image_type}", self.pdf],
            text=True,
            capture_output=True,
        )

        print(output)

        return ls(path=self.td, exts=["png"])

    def _read_image(self, path: str):
        im = cv2.imread(path)

        return cv2.cvtColor(im, cv2.COLOR_BGR2RGB)

    def _write_image(self, im, path: str):
        cv2.imwrite(path, im)

    def resize_images(self, n: float = 1.50):
        if self.images == None:
            self.images = self._pdf_to_images()

        for (_, path) in self.images:
            im = self._read_image(path)

            resized_im = self._resize_image(im, n=n)

            self._write_image(resized_im, path)

        return self

    def _resize_image(self, im, n: float):
        w = int(im.shape[1] * n)
        h = int(im.shape[0] * n)
        dsize = (w, h)

        return cv2.resize(im, dsize=dsize, interpolation=cv2.INTER_CUBIC)
        # return cv2.resize(im, None, fx=n, fy=n, interpolation=cv2.INTER_CUBIC)

    def threshold_images(self):
        if self.images == None:
            self.images = self._pdf_to_images()

        for (_, path) in self.images:
            im = self._read_image(path)

            thresholded_im = self._threshold_image(im)

            self._write_image(thresholded_im, path)

        return self

    def _threshold_image(self, im):
        image = im
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # image = cv2.GaussianBlur(image, (5, 5), 0)
        return cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    def _show_image(self, im) -> None:
        cv2.imshow("im", im)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def images_to_pdf(self):
        if self.images != None:
            images = sorted([image[1] for image in self.images])
            tf = tempfile.NamedTemporaryFile(dir=self.td, delete=False)
            with open(tf.name, "wb") as f:
                f.write(img2pdf.convert(images))

            return tf.name

    def rotate_images(self):
        if self.images == None:
            self.images = self._pdf_to_images()

        for (_, path) in self.images:
            im = self._read_image(path)

            try:
                rotated_im = self._rotate_image(im)
            except TesseractError as e:
                if "Too few characters" in e.message:
                    raise ValueError("Cannot rotate image.")
            except Exception as e:
                print(str(e))
            else:
                self._write_image(rotated_im, path)

        return self

    def _rotate_image(self, im):
        results = pytesseract.image_to_osd(im, output_type=Output.DICT)

        print("ORIENTATION:", results["orientation"], "ROTATE:", results["rotate"])

        if results["orientation"] == 0 and results["rotate"] == 0:
            return im

        return imutils.rotate_bound(im, angle=results["rotate"])

    def add_margins(self, margin: int = 50):
        """Add N pixel margins to PDF"""

        pdf = open(self.pdf, "rb")
        reader = PdfReader(pdf)

        writer = PdfWriter()

        for page in reader.pages:
            x, y = page.mediabox.upper_right
            # print(x, y)
            page.mediabox.upper_right = (float(x) + margin, float(y))

            # cropbox - ???
            # ---------------------------------------------------------------------------------
            x, y = page.mediabox.upper_left
            # print(x, y)
            page.mediabox.upper_left = (float(x), float(y) + margin)

            # ---------------------------------------------------------------------------------
            x, y = page.mediabox.lower_right
            # print(x, y)
            page.mediabox.lower_right = (float(x), float(y) - margin)

            # ---------------------------------------------------------------------------------
            x, y = page.mediabox.lower_left
            # print(x, y)
            page.mediabox.lower_left = (float(x) - margin, float(y))

            writer.add_page(page)

        pdf.close()

        writer.write(self.pdf)

        return self

    def cleanup(self):
        shutil.rmtree(self.td)


if __name__ == "__main__":
    pp = PdfPreprocessor(
        # r"C:\Users\Sergey\Desktop\arbeitauslagern-attachments\test in 90 degree (1).pdf"
        r"C:\Users\Sergey\Desktop\arbeitauslagern-attachments\00.pdf"
    )

    try:
        pp.threshold_images().rotate_images()
    except Exception as e:
        print(e)
        pp.add_margins().resize_images(n=2).threshold_images().rotate_images()

    processed_pdf = pp.images_to_pdf()

    shutil.move(processed_pdf, "test.pdf")

    os.startfile("test.pdf")

    pp.cleanup()
