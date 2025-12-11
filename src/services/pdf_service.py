# src/services/pdf_service.py
import asyncio
import base64
import io
import shutil
from typing import List, NamedTuple, Optional

# pdf2imageライブラリを使用 (pip install pdf2image)
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError


class PageImage(NamedTuple):
    """
    PDFの1ページを表す画像データとメタデータを保持する構造体。
    FletのImageコントロールに渡すBase64文字列、ページ番号、寸法を含む。
    """

    page_number: int
    base64_image: str
    width: int
    height: int


class PDFService:
    """PDF操作に関するビジネスロジックを扱うサービスクラス"""

    def _get_poppler_path(self) -> Optional[str]:
        """
        システムのPopplerパスを探索して返す。
        """
        # 一般的なパスをチェック
        possible_paths = [
            r"C:\Program Files\poppler\bin",  # Windows (Typical)
            r"C:\poppler\bin",  # Windows (Simple)
            "/opt/homebrew/bin",  # Apple Silicon Mac
            "/usr/local/bin",  # Intel Mac
            "/usr/bin",
        ]

        if shutil.which("pdfinfo"):
            return None  # PATHが通っている

        for path in possible_paths:
            if shutil.which("pdfinfo", path=path):
                return path

        return None

    async def convert_pdf_to_images(self, pdf_path: str) -> List[PageImage]:
        """
        PDFを画像のリストに変換する (非同期ラッパー)
        """
        return await asyncio.to_thread(self._convert_sync, pdf_path)

    def _convert_sync(self, pdf_path: str) -> List[PageImage]:
        """
        PDF変換の同期実行部
        """
        page_images_list: List[PageImage] = []
        poppler_path = self._get_poppler_path()

        try:
            # dpi=200 に固定して、座標計算の基準を安定させる
            pil_images = convert_from_path(
                pdf_path,
                dpi=200,  # 解像度を固定
                fmt="jpeg",
                poppler_path=poppler_path,
            )

            for idx, img in enumerate(pil_images):
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

                page_image = PageImage(
                    page_number=idx + 1, base64_image=img_str, width=img.width, height=img.height
                )
                page_images_list.append(page_image)

            return page_images_list

        except PDFInfoNotInstalledError:
            raise RuntimeError(
                "システムに 'poppler' が見つかりません。\n"
                "Windowsの場合: PopplerをインストールしてPATHを通してください。\n"
                "Macの場合: `brew install poppler` を実行してください。"
            )
        except PDFPageCountError:
            raise ValueError(
                "PDFファイルのページ数を取得できませんでした。破損の可能性があります。"
            )
        except Exception as e:
            raise RuntimeError(f"PDF変換エラー: {str(e)}")


# シングルトン
pdf_service = PDFService()
