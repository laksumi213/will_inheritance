import io
import os
import subprocess
from datetime import datetime

import pypdf
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3, A4, landscape, portrait
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# import re
# import shutil


class PdfCreate:
    def __del__(self):
        # print('del PdfCreate')
        self.obj_write = None
        self.obj_write2 = None
        self.cc_obj_write = None
        self.cc_obj_write2 = None
        self.reader_page = None
        self.reader_page2 = None
        self.output = None
        self.cc = None

    def __init__(self, pagesize=A4, vertical_and_horizontal=portrait):
        super().__init__()
        self._last_pos = None
        self.reader_page2 = None
        self.cc_obj_write2 = None
        self.obj_write2 = None
        self.cc_obj_write = None
        self.obj_write = None
        self.reader_page = None
        self.output = None
        self.cc = None
        if pagesize == "A3":
            self.pagesize = A3
        else:
            self.pagesize = A4

        if vertical_and_horizontal == "landscape":
            self.vertical_and_horizontal = landscape
        else:
            self.vertical_and_horizontal = portrait

        # self.vertical_and_horizontal = vertical_and_horizontal if vertical_and_horizontal == portrait else landscape

    def build(self):
        return self.cc

    def init_set(self, obj):
        self.output = PdfWriter()
        cc = canvas.Canvas(obj, pagesize=self.vertical_and_horizontal(self.pagesize))
        # cc = canvas.Canvas(obj, pagesize=portrait(A4))
        pdfmetrics.registerFont(
            TTFont("IPAexGothic", os.path.dirname(os.path.dirname(__file__)) + "/utils/ipaexg.ttf")
        )
        cc.setFillColorRGB(0, 0, 0)
        return cc

    def set_font(self, size):
        self.cc.setFont("IPAexGothic", size)

    # def get_Width(self):
    #     pdf = PdfReader(self.obj_write)
    #     page_num = pdf.getNumPages()
    #     for page in range(page_num):
    #         p = pdf_reader.getPage(page)
    #         p_size = p.mediaBox
    #         p_width = p_size.getWidth()
    #         p_height = p_size.getHeight()
    #         print(f'\nページ{page + 1}')
    #         print('RectangleObject: ', p_size)
    #         print('幅　: ', p_width, 'pt')
    #         print('高さ: ', p_height, 'pt')

    def draw_string(self, tx, ty, s, size=10, colors="#000000"):
        self.obj_write = None
        self.obj_write = io.BytesIO()
        self.cc_obj_write = self.init_set(self.obj_write)
        self.cc_obj_write.setFont("IPAexGothic", size)
        self.cc_obj_write.setFillColor(HexColor(colors))
        self.cc_obj_write.drawString(tx * mm, ty * mm, str(s))
        self.obj_write.seek(0)
        self.cc_obj_write.save()
        pdf = PdfReader(self.obj_write)
        if self.reader_page is None:
            self.reader_page = pdf.pages[0]
        else:
            self.reader_page.merge_page(pdf.pages[0])

        self.obj_write2 = io.BytesIO()
        self.cc_obj_write2 = self.init_set(self.obj_write2)
        self.cc_obj_write2.setFont("IPAexGothic", size)
        self.cc_obj_write2.setFillColor(HexColor(colors))
        self.cc_obj_write2.drawString(tx * mm, ty * mm, str(s))
        self.obj_write2.seek(0)
        self.cc_obj_write2.save()
        # pdf = PdfReader(self.obj_write)
        pdf2 = PdfReader(self.obj_write2)
        self.reader_page2 = pdf2.pages[0]

    def draw_rect(self, x, y, tx, ty, size=10, colors="#000000", linewidth=1):
        self.obj_write = None
        self.obj_write = io.BytesIO()
        self.cc_obj_write = self.init_set(self.obj_write)
        # self.cc_obj_write.setFont('IPAexGothic', size)
        if colors != "#000000":
            self.cc_obj_write.setStrokeColorRGB(1, 0, 0)
        self.cc_obj_write.setLineWidth(linewidth)
        self.cc_obj_write.rect(x * mm, y * mm, (tx - x) * mm, (ty - y) * mm)
        self.cc_obj_write.save()

        pdf = PdfReader(self.obj_write)
        if self.reader_page is None:
            # pdf = PdfReader(self.obj_write)
            self.reader_page = pdf.pages[0]
        else:
            # pdf = PdfReader(self.obj_write)
            self.reader_page.merge_page(pdf.pages[0])

    def draw_line(self, x1, y1, x2, y2):
        self.obj_write = None
        self.obj_write = io.BytesIO()
        self.cc_obj_write = self.init_set(self.obj_write)
        self.cc_obj_write.line(x1 * mm, y1 * mm, x2 * mm, y2 * mm)
        self.obj_write.seek(0)
        self.cc_obj_write.save()
        pdf = PdfReader(self.obj_write)
        if self.reader_page is None:
            # pdf = PdfReader(self.obj_write)
            self.reader_page = pdf.pages[0]
        else:
            # pdf = PdfReader(self.obj_write)
            self.reader_page.merge_page(pdf.pages[0])

    def get_pos(self, t):
        self.output = PdfWriter()
        self.output.add_page(self.reader_page2)
        with open(os.path.dirname(__file__) + "_tmp.pdf", "wb") as f:
            self.output.write(f)
        with open(os.path.dirname(__file__) + "_tmp.pdf", "rb") as fp:
            device = PDFPageAggregator(PDFResourceManager(), laparams=LAParams())
            interpreter = PDFPageInterpreter(PDFResourceManager(), device)
            for page in PDFPage.create_pages(PDFDocument(PDFParser(fp))):
                # for page in PDFPage.create_pages(PDFDocument(PDFParser(self.obj_write))):
                interpreter.process_page(page)
                layout = device.get_result()
                for element in layout:
                    # print(element.get_text())
                    # if hasattr(element, "get_text") and element.get_text().replace('\n', '') == t:
                    #     pos = [round(element.bbox[0] * 0.352778),
                    #            round(element.bbox[1] * 0.3538),
                    #            element.bbox[2] * 0.352778,
                    #            element.bbox[3] * 0.3538
                    #            ]
                    #     return pos

                    # if hasattr(element, "get_text") and element.get_text().partition('\n')[-1].replace('\n', '') == t:
                    # if hasattr(element, "get_text") and re.findall('\n', element.get_text()) == t:
                    # print('element.get_text().splitlines()[-1]:', element.get_text().splitlines()[-1])
                    if hasattr(element, "get_text") and element.get_text().splitlines()[-1] == str(
                        t
                    ):
                        pos = [
                            round(element.bbox[0] * 0.352778),
                            round(element.bbox[1] * 0.3538),
                            element.bbox[2] * 0.352778,
                            element.bbox[3] * 0.35,
                            # element.bbox[3] * 0.3538
                        ]
                        # print(element.get_text(), 'pos:', pos)
                        # print()

                        return pos

    def pdf_save(self, output_name, marge_pdf=None, page=1, open_bool=False):
        ### PDFを保存 ###
        self.output = PdfWriter()
        if os.path.splitext(output_name)[1] != ".pdf":
            output_name += ".pdf"
        if marge_pdf is not None:
            # self.output.add_page(self.reader_page)
            # with open(output_name, 'wb') as f:
            #     self.output.write(f)
            # pdf = PdfReader(output_name)
            # self.reader_page = pdf.pages[0]
            marge_pdf = PdfReader(marge_pdf)
            if self.reader_page is not None:
                marge_pdf.pages[page - 1].merge_page(self.reader_page)
            self.output.add_page(marge_pdf.pages[page - 1])
        else:
            self.output.add_page(self.reader_page)
        with open(output_name, "wb") as f:
            self.output.write(f)
            if open_bool:
                if os.name == "nt":
                    subprocess.Popen(
                        [
                            "C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
                            output_name.replace("/", "\\"),
                        ]
                    )
                elif os.name == "posix":
                    subprocess.Popen(["open", output_name])

        # print('PdfCreate save end')
        self.obj_write = None
        self.obj_write2 = None
        self.cc_obj_write = None
        self.cc_obj_write2 = None
        self.reader_page = None
        self.reader_page2 = None
        self.output = None
        self.cc = None

    def pdf_marge(self, output_name, *args):
        output = PdfWriter()
        for arg in args:
            if os.path.splitext(arg)[1] != ".pdf":
                arg += ".pdf"
            output.add_page(PdfReader(arg).pages[0])
            os.remove(arg)
        if os.path.splitext(output_name)[1] != ".pdf":
            output_name += ".pdf"
        with open(output_name, "wb") as f:
            output.write(f)
        # print('output_name: ', output_name)
        if os.name == "nt":
            subprocess.Popen(
                [
                    "C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
                    output_name.replace("/", "\\"),
                ]
            )
        elif os.name == "posix":
            subprocess.Popen(["open", output_name])

    @classmethod
    def a3_marge(
        cls,
        save_path="./",
        *args,
    ):
        merger = pypdf.PdfMerger()
        # folder = '//DS220/New WINZM7/New文書管理/職員個人用/森町/銀行解約手順/'
        folder = os.path.dirname(__file__)
        if save_path == "./":
            save_path = folder

        for i, arg in enumerate(args):
            merger.append(
                os.path.join(os.path.dirname(args[i]), os.path.splitext(args[i])[0] + "_output.pdf")
            )

        merger.write(os.path.join(save_path, os.path.splitext(args[0])[0] + "_merge.pdf"))
        merger.close()

        input_file = os.path.join(save_path, os.path.splitext(args[0])[0] + "_merge.pdf")  # 原稿

        output_file = os.path.join(
            save_path,
            os.path.basename(str(os.path.splitext(args[0])[0]).replace("1", "") + "_A3.pdf"),
        )  # 見開きにしたPDFの保存

        reader = PdfReader(input_file)
        writer = PdfWriter()

        for i in range(0, len(reader.pages), 2):
            p1 = reader.pages[i]
            if i + 1 == len(reader.pages):  # ページ総数が奇数の場合に、右ページに空白を補完
                p2 = PageObject.create_blank_page(width=p1.mediabox.right, height=p1.mediabox.top)
            else:
                p2 = reader.pages[i + 1]
            width_1_2 = p1.mediabox.right + p2.mediabox.right
            height_1_2 = max(p1.mediabox.top, p2.mediabox.top)
            p_1_2 = PageObject.create_blank_page(width=width_1_2, height=height_1_2)

            # 見開きにするため、右ページ用のPDFを右に平行移動、mediaboxもそれに合わせて右に平行移動
            op = Transformation().translate(tx=p1.mediabox.right)
            p2.add_transformation(op)
            p2.mediabox.left = p1.mediabox.right
            p2.mediabox.right = p1.mediabox.right + p2.mediabox.right

            p_1_2.merge_page(p1)
            p_1_2.merge_page(p2)
            writer.add_page(p_1_2)

        with open(output_file, mode="wb") as f:
            writer.write(f)

        os.remove(input_file)
        for i, arg in enumerate(args):
            os.remove(
                os.path.join(os.path.dirname(args[i]), os.path.splitext(args[i])[0] + "_output.pdf")
            )

    @property
    def last_pos(self):
        return self._last_pos

    @last_pos.setter
    def last_pos(self, value):
        self._last_pos = value


if __name__ == "__main__":
    # reader = PdfReader("./pdf/三菱UFJモルガン・スタンレー証券_相続資産受取依頼書.pdf")
    # reader = PdfReader("//DS220/New WINZM7/New文書管理/職員個人用/森町/銀行解約手順/三菱UFJモルガン・スタンレー証券_相続資産受取依頼書.pdf")

    dt_now = datetime.now().strftime("%Y/%m/%d").split("/")

    pdf = PdfCreate(pagesize="A4")

    # pdf.draw_string(171, 168, dt_now[0])
    # pos = pdf.get_pos(dt_now[0])
    # print(dt_now[0], pos)
    #
    # pdf.draw_string(186, pos[1], dt_now[1])
    # pos = pdf.get_pos(dt_now[1])
    # print(dt_now[1], pos)
    #
    # pdf.draw_string(197, pos[1], dt_now[2])
    # pos = pdf.get_pos(dt_now[2])
    # print(dt_now[2], pos)

    pdf.draw_string(58, 253.5, "103-0028")
    pdf.draw_string(117, 253.5, "050      6864      7034")
    pdf.draw_string(58, 246.5, "東京都中央区八重洲一丁目7-20 八重洲口会館2階", 12)

    # print(os.path.join(Path.cwd().parent, "/pdf/SBI証券_残高証明書申請書.pdf"))
    # print(os.path.join(os.path.dirname(os.getcwd()), "/pdf/SBI証券_残高証明書申請書.pdf"))
    print(os.path.join(os.path.dirname(os.getcwd()), "pdf", "SBI証券_残高証明書申請書.pdf"))
    # print(f"{Path.cwd().parent}/pdf/SBI証券_残高証明書申請書.pdf")
    pdf.pdf_save(
        os.path.join(r"\\192.168.11.20\行政書士法人チェスター\08.その他\スキャン\森町", "111"),
        os.path.join(
            os.path.dirname(os.getcwd()), "pdf", "SBI証券_個人情報に関する開示等請求書.pdf"
        ),
        page=2,
        open_bool=True,
    )

    # pdf = PdfCreate(pagesize='A3')
    # pdf.pdf_save('222', "pdf/SBI証券_残高証明書申請書.pdf", page=2)
    #
    # path = os.path.dirname(__file__) + r'/pdf'
    # path1 = os.path.join(path, 'SBI証券_残高証明書申請書1.pdf')
    # path2 = os.path.join(path, 'SBI証券_残高証明書申請書2.pdf')
    # pdf.pdf_marge('SBI証券_残高証明書申請書.pdf', path1, path2)
