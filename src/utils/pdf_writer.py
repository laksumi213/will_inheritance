# src/utils/pdf_writer.py
import os
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF


class PdfFormWriter:
    """
    Fletツールで取得した座標をもとに、PDFへテキストや図形を書き込むクラス。
    """

    # プロジェクトルートからの相対パスでフォントディレクトリを指定
    DEFAULT_FONT_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"

    def __init__(self, input_pdf: str, output_pdf: str, font_path: Optional[str] = None):
        """
        Args:
            input_pdf: 読み込むPDFパス
            output_pdf: 保存するPDFパス
            font_path: フォントパス。Noneの場合は assets/fonts 内を探索、なければシステムフォントを使用。
        """
        self.doc = fitz.open(input_pdf)
        self.output_path = output_pdf
        self.font_name = "custom_font"

        # フォントパスの解決ロジック
        self.font_path = self._resolve_font_path(font_path)

        if not self.font_path:
            print("Warning: 有効なフォントが見つかりません。日本語は文字化けする可能性があります。")

    def _resolve_font_path(self, user_path: Optional[str]) -> Optional[str]:
        """フォントパスを決定する"""
        # 1. ユーザー指定がある場合
        if user_path and os.path.exists(user_path):
            return user_path

        # 2. assets/fonts 内の代表的な日本語フォントを探す
        candidates = [
            "msgothic.ttc",
            "msmincho.ttc",
            "meiryo.ttc",
            "YuGothR.ttc",
            "Harumart.ttf",
            "ipaexg.ttf",
        ]

        if self.DEFAULT_FONT_DIR.exists():
            for filename in candidates:
                fpath = self.DEFAULT_FONT_DIR / filename
                if fpath.exists():
                    print(f"Font loaded from assets: {fpath}")
                    return str(fpath)

            # フォルダ内の拡張子が .ttc, .ttf の最初のファイルをフォールバックとして採用
            for file in self.DEFAULT_FONT_DIR.iterdir():
                if file.suffix.lower() in [".ttc", ".ttf", ".otf"]:
                    print(f"Font loaded from assets (fallback): {file}")
                    return str(file)

        # 3. Windows標準フォント (フォールバック)
        win_font = Path("C:/Windows/Fonts/msgothic.ttc")
        if win_font.exists():
            return str(win_font)

        return None

    def _get_scale(self, page_obj, ref_width: int) -> float:
        """画像幅(px)とPDF幅(pt)の比率を計算"""
        pdf_width_pt = page_obj.rect.width
        return pdf_width_pt / ref_width

    def draw_text(
        self,
        page: int,
        x: int,
        y: int,
        text: str,
        ref_width: int = 800,  # ツール側のDISPLAY_WIDTHに合わせる
        font_size: int = 11,
        color: tuple = (0, 0, 0),
    ):
        """テキスト書き込み"""
        if not self.doc or self.doc.is_closed:
            return

        if not (1 <= page <= len(self.doc)):
            return

        page_obj = self.doc[page - 1]
        scale = self._get_scale(page_obj, ref_width)

        # フォント登録（初回のみ）
        if self.font_path:
            try:
                page_obj.insert_font(fontname=self.font_name, fontfile=self.font_path)
            except Exception:
                pass  # 既に登録されている場合などは無視

        args = {
            "point": fitz.Point(x * scale, y * scale),
            "text": str(text),
            "fontsize": font_size,
            "color": color,
        }

        if self.font_path:
            args["fontname"] = self.font_name

        try:
            page_obj.insert_text(**args, overlay=True)
        except Exception as e:
            print(f"Text Error: {e}")

    def draw_rect(
        self,
        page: int,
        x: int,
        y: int,
        w: int,
        h: int,
        ref_width: int = 800,
        border_color: tuple = (1, 0, 0),
        width: float = 2,
    ):
        """矩形描画"""
        if not self.doc or self.doc.is_closed:
            return

        if not (1 <= page <= len(self.doc)):
            return
        page_obj = self.doc[page - 1]
        scale = self._get_scale(page_obj, ref_width)

        rect = fitz.Rect(x * scale, y * scale, (x + w) * scale, (y + h) * scale)
        try:
            shape = page_obj.new_shape()
            shape.draw_rect(rect)
            shape.finish(color=border_color, width=width)
            shape.commit()
        except Exception as e:
            print(f"Rect Error: {e}")

    def draw_circle(
        self,
        page: int,
        x: int,
        y: int,
        ref_width: int = 800,
        radius: int = 15,
        border_color: tuple = (1, 0, 0),
        width: float = 2,
    ):
        """円描画"""
        if not self.doc or self.doc.is_closed:
            return

        if not (1 <= page <= len(self.doc)):
            return
        page_obj = self.doc[page - 1]
        scale = self._get_scale(page_obj, ref_width)

        r = radius * scale
        center = fitz.Point(x * scale, y * scale)

        try:
            shape = page_obj.new_shape()
            shape.draw_circle(center, r)
            shape.finish(color=border_color, width=width)
            shape.commit()
        except Exception as e:
            print(f"Circle Error: {e}")

    def draw_check(
        self,
        page: int,
        x: int,
        y: int,
        ref_width: int = 800,
        size: int = 20,
        color: tuple = (0, 0, 0),
    ):
        """チェックマーク(✔︎)を描画"""
        self.draw_text(page, x, y, "✔", ref_width, font_size=size, color=color)

    def close(self):
        """ドキュメントを安全に閉じる（多重呼び出し対応）"""
        # 修正箇所: if self.doc -> if self.doc is not None
        if self.doc is not None and not self.doc.is_closed:
            try:
                self.doc.close()
            except Exception as e:
                print(f"Close Error: {e}")

    def save(self):
        """保存処理"""
        # 修正箇所: if not self.doc -> if self.doc is None
        if self.doc is None or self.doc.is_closed:
            print("Document is already closed.")
            return

        try:
            self.doc.save(self.output_path)
            print(f"Saved: {self.output_path}")
            self.close()
        except Exception as e:
            print(f"Save Error: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
