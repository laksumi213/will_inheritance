# src/utils/pdf_writer.py
import os
from typing import Any, Dict, List

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


class PdfWriter:
    """
    PDFへの描画処理を担当するユーティリティクラス
    """

    def __init__(self, font_path: str):
        self.font_path = font_path
        self.font_name = "JapaneseFont"
        self._register_font()

    def _register_font(self) -> None:
        """日本語フォントの登録"""
        try:
            if os.path.exists(self.font_path):
                pdfmetrics.registerFont(TTFont(self.font_name, self.font_path))
            else:
                # フォントがない場合はデフォルトを使用（日本語は文字化けする可能性あり）
                print(f"Warning: Font file not found at {self.font_path}")
                self.font_name = "Helvetica"
        except Exception as e:
            print(f"Font registration error: {e}")
            self.font_name = "Helvetica"

    def create_overlay_pdf(self, output_path: str, data_list: List[Dict[str, Any]]) -> bool:
        """
        座標データに基づいてテキストを描画し、透明なPDFを生成する

        Args:
            output_path: 出力先ファイルパス
            data_list: 描画データのリスト [{'x': float, 'y': float, 'value': str}, ...]

        Returns:
            bool: 成功時 True
        """
        try:
            # ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            c = canvas.Canvas(output_path, pagesize=A4)
            c.setFont(self.font_name, 10)

            for data in data_list:
                x = data.get("x", 0.0)
                y = data.get("y", 0.0)
                text = str(data.get("value", ""))

                # 座標は左下が(0,0)基準。必要に応じて変換ロジックを入れる
                c.drawString(x, y, text)

            c.save()
            return True
        except Exception as e:
            print(f"PDF drawing error: {e}")
            raise e
