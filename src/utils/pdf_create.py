# src/utils/pdf_create.py
import io
import os
import subprocess
from datetime import datetime

# 外部ライブラリ
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3, A4, landscape, portrait
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# 設定ファイルからパスを取得
from src.config import settings

class PdfCreate:
    def __del__(self):
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

    def build(self):
        return self.cc

    def init_set(self, obj):
        self.output = PdfWriter()
        cc = canvas.Canvas(obj, pagesize=self.vertical_and_horizontal(self.pagesize))
        
        # フォントパス: src/config.py の ASSETS_DIR を使用
        font_path = settings.ASSETS_DIR / "fonts" / "ipaexg.ttf"
        
        if not font_path.exists():
            print(f"Warning: Font file not found at {font_path}. Using default font.")
        else:
            try:
                pdfmetrics.registerFont(TTFont("IPAexGothic", str(font_path)))
            except Exception as e:
                print(f"Font registration error: {e}")

        cc.setFillColorRGB(0, 0, 0)
        return cc

    def set_font(self, size):
        try:
            self.cc.setFont("IPAexGothic", size)
        except:
            self.cc.setFont("Helvetica", size)

    def draw_string(self, tx, ty, s, size=10, colors="#000000"):
        self.obj_write = None
        self.obj_write = io.BytesIO()
        self.cc_obj_write = self.init_set(self.obj_write)
        
        try:
            self.cc_obj_write.setFont("IPAexGothic", size)
        except:
            self.cc_obj_write.setFont("Helvetica", size)
            
        self.cc_obj_write.setFillColor(HexColor(colors))
        self.cc_obj_write.drawString(tx * mm, ty * mm, str(s))
        self.obj_write.seek(0)
        self.cc_obj_write.save()
        
        pdf = PdfReader(self.obj_write)
        if self.reader_page is None:
            self.reader_page = pdf.pages[0]
        else:
            self.reader_page.merge_page(pdf.pages[0])

    def pdf_save(self, output_name, marge_pdf=None, page=1, open_bool=False):
        self.output = PdfWriter()
        if os.path.splitext(output_name)[1] != ".pdf":
            output_name += ".pdf"
            
        os.makedirs(os.path.dirname(output_name), exist_ok=True)

        if marge_pdf is not None:
            try:
                marge_pdf_reader = PdfReader(marge_pdf)
                if self.reader_page is not None:
                    marge_pdf_reader.pages[page - 1].merge_page(self.reader_page)
                self.output.add_page(marge_pdf_reader.pages[page - 1])
            except Exception as e:
                print(f"Error reading template PDF: {e}")
                return
        else:
            if self.reader_page:
                self.output.add_page(self.reader_page)
            else:
                print("No content to save.")
                return

        with open(output_name, "wb") as f:
            self.output.write(f)
            
        if open_bool:
            try:
                if os.name == "nt":
                    subprocess.Popen(["explorer", output_name.replace("/", "\\")])
                elif os.name == "posix":
                    subprocess.Popen(["open", output_name])
            except Exception as e:
                print(f"Error opening PDF: {e}")

        self.obj_write = None
        self.reader_page = None
        self.output = None