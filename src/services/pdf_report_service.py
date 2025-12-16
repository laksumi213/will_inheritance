# src/services/pdf_report_service.py
import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm

from src.config import settings
from src.models.tables import Case, Deceased, Heir

class PdfReportService:
    """
    ReportLabを使用した帳票PDF作成サービス
    """

    def __init__(self):
        self._register_font()

    def _register_font(self):
        """日本語フォントの登録"""
        font_path = settings.ASSETS_DIR / "fonts" / "ipaexg.ttf"
        if font_path.exists():
            try:
                pdfmetrics.registerFont(TTFont("IPAexGothic", str(font_path)))
                self.font_name = "IPAexGothic"
            except Exception as e:
                print(f"Font register error: {e}")
                self.font_name = "Helvetica"
        else:
            self.font_name = "Helvetica"

    def create_case_report(self, case: Case, deceased: Deceased, heirs: list[Heir], output_path: str) -> bool:
        """
        案件情報（被相続人・相続人一覧）をPDFに出力する
        """
        try:
            # フォルダ作成
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            c = canvas.Canvas(output_path, pagesize=landscape(A4))
            width, height = landscape(A4)

            # タイトル
            c.setFont(self.font_name, 18)
            c.drawString(20 * mm, 190 * mm, f"案件詳細レポート: {case.case_number}")
            
            # 作成日
            c.setFont(self.font_name, 10)
            today = datetime.now().strftime("%Y年%m月%d日")
            c.drawRightString(280 * mm, 190 * mm, f"作成日: {today}")

            # 被相続人情報
            c.setFont(self.font_name, 12)
            c.drawString(20 * mm, 170 * mm, "■ 被相続人情報")
            
            y_pos = 160 * mm
            line_height = 8 * mm
            
            d_name = f"{deceased.name_last} {deceased.name_first}"
            d_kana = f"{deceased.name_last_kana} {deceased.name_first_kana}"
            dob = deceased.date_of_birth.strftime("%Y/%m/%d") if deceased.date_of_birth else "-"
            dod = deceased.date_of_death.strftime("%Y/%m/%d") if deceased.date_of_death else "-"
            
            c.setFont(self.font_name, 10)
            c.drawString(25 * mm, y_pos, f"氏名: {d_name} ({d_kana})")
            y_pos -= line_height
            c.drawString(25 * mm, y_pos, f"生年月日: {dob}   死亡日: {dod}")
            y_pos -= line_height
            c.drawString(25 * mm, y_pos, f"本籍: {deceased.hometown or '-'}")
            
            y_pos -= (line_height * 2)

            # 相続人一覧
            c.setFont(self.font_name, 12)
            c.drawString(20 * mm, y_pos, "■ 相続人一覧")
            y_pos -= line_height * 1.5

            # ヘッダー
            c.setFont(self.font_name, 10)
            c.drawString(25 * mm, y_pos, "氏名")
            c.drawString(80 * mm, y_pos, "続柄")
            c.drawString(110 * mm, y_pos, "生年月日")
            c.drawString(150 * mm, y_pos, "住所")
            
            # 罫線
            c.line(20 * mm, y_pos - 2*mm, 280 * mm, y_pos - 2*mm)
            y_pos -= line_height

            for heir in heirs:
                if y_pos < 20 * mm: # 改ページ処理
                    c.showPage()
                    c.setFont(self.font_name, 10)
                    y_pos = 190 * mm
                
                h_name = f"{heir.name_last} {heir.name_first}"
                h_rel = heir.relationship_type or "-"
                h_dob = heir.date_of_birth.strftime("%Y/%m/%d") if heir.date_of_birth else "-"
                
                # 簡易的な住所表示（実際にはAddressモデルから引く必要があるが、ここでは省略または仮実装）
                h_addr = "-" 
                
                c.drawString(25 * mm, y_pos, h_name)
                c.drawString(80 * mm, y_pos, h_rel)
                c.drawString(110 * mm, y_pos, h_dob)
                c.drawString(150 * mm, y_pos, h_addr)
                
                y_pos -= line_height

            c.save()
            return True

        except Exception as e:
            print(f"PDF Create Error: {e}")
            raise e

pdf_report_service = PdfReportService()