# src/services/pdf_service.py
import asyncio
import base64
import io
import shutil
import os
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional

# pdf2imageライブラリを使用
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
    """
    PDF操作に関するビジネスロジックを扱うサービスクラス。
    Popplerのパス解決と画像変換を担当します。
    """

    def get_poppler_path(self) -> Optional[str]:
        """
        Popplerのbinディレクトリパスを解決して返します。
        
        優先順位:
        1. プロジェクト内: project_root/libs/poppler/bin
        2. プロジェクト内: project_root/libs/poppler/**/bin (Library/binなど)
        3. システムPATH: 環境変数PATHに通っている場合
        """
        # 現在のファイル (src/services/pdf_service.py) から見たプロジェクトルート
        base_dir = Path(__file__).resolve().parent.parent.parent
        libs_dir = base_dir / "libs"

        # 1. libs/poppler/bin を直接チェック
        direct_path = libs_dir / "poppler" / "bin"
        if direct_path.exists() and (direct_path / "pdfinfo.exe").exists():
            return str(direct_path)

        # 2. libs/poppler 配下を探索 (Library/bin などのパターン対応)
        poppler_root = libs_dir / "poppler"
        if poppler_root.exists():
            for path in poppler_root.rglob("bin"):
                if (path / "pdfinfo.exe").exists():
                    return str(path)

        # 3. システムPATHのチェック
        if shutil.which("pdfinfo"):
            return None  # pdf2imageはNoneを渡すとPATHを使用します

        # 見つからない場合
        return None

    async def convert_pdf_to_images(self, pdf_path: str) -> List[PageImage]:
        """
        PDFを画像のリストに変換する (非同期ラッパー)
        """
        return await asyncio.to_thread(self._convert_sync, pdf_path)

    def convert_pdf_to_images_sync(self, pdf_path: str) -> List[PageImage]:
        """
        PDFを画像のリストに変換する (同期版 - run_thread用)
        """
        return self._convert_sync(pdf_path)

    def _convert_sync(self, pdf_path: str) -> List[PageImage]:
        """
        PDF変換の同期実行部
        """
        page_images_list: List[PageImage] = []
        
        # パスの解決
        poppler_path = self.get_poppler_path()
        
        # 解決できなかった場合に例外を投げる準備
        if poppler_path is None and not shutil.which("pdfinfo"):
             raise RuntimeError(
                "システムに 'Poppler' が見つかりません。\n"
                "以下の手順で配置してください：\n"
                "1. プロジェクトルートに 'libs' フォルダを作成\n"
                "2. ダウンロードしたPopplerを 'libs/poppler' に配置\n"
                "3. 'libs/poppler/bin/pdfinfo.exe' が存在することを確認"
            )

        try:
            # dpi=200 に固定して、座標計算の基準を安定させる
            pil_images = convert_from_path(
                pdf_path,
                dpi=200,
                fmt="jpeg",
                poppler_path=poppler_path,
            )

            for idx, img in enumerate(pil_images):
                buffered = io.BytesIO()
                # JPEG形式で軽量化
                img.save(buffered, format="JPEG", quality=85)
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

                page_image = PageImage(
                    page_number=idx + 1, 
                    base64_image=img_str, 
                    width=img.width, 
                    height=img.height
                )
                page_images_list.append(page_image)

            return page_images_list

        except PDFInfoNotInstalledError:
            raise RuntimeError(
                "Popplerの実行ファイルが見つかりません。\n"
                f"検索パス: {poppler_path if poppler_path else 'System PATH'}\n"
                "libs/poppler/bin フォルダの中身を確認してください。"
            )
        except PDFPageCountError:
            raise ValueError(
                "PDFファイルのページ数を取得できませんでした。\n"
                "ファイルが破損しているか、パスが間違っている可能性があります。"
            )
        except Exception as e:
            raise RuntimeError(f"PDF変換中にエラーが発生しました: {str(e)}")


# シングルトンインスタンス
pdf_service = PDFService()