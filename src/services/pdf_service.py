# services/pdf_service.py
import asyncio
import shutil
import uuid
from pathlib import Path
from typing import List, NamedTuple, Optional

from pdf2image import convert_from_path


class PageImage(NamedTuple):
    """生成された画像のパスとサイズ情報を格納"""

    path: str
    width: int
    height: int


class PdfService:
    """
    PDFの画像変換および一時ファイル管理を行うサービスクラス
    プロジェクトルートの 'temp' ディレクトリを使用する
    """

    # このファイルは services/ にあるため、parent.parent がプロジェクトルート
    BASE_TEMP_DIR = Path(__file__).parent.parent / "temp"

    def __init__(self) -> None:
        self.session_dir: Optional[Path] = None
        self.page_images: List[PageImage] = []

        # 念のため初期化時にベースTEMPディレクトリを作成
        self.BASE_TEMP_DIR.mkdir(parents=True, exist_ok=True)

    async def convert_pdf_to_images(self, pdf_path: str) -> List[PageImage]:
        """
        PDFを画像に変換し、パスとサイズ情報を返す (非同期ラッパー)
        """
        return await asyncio.to_thread(self._convert_sync, pdf_path)

    def _convert_sync(self, pdf_path: str) -> List[PageImage]:
        # 以前のセッションがあればクリーンアップ
        self.cleanup()

        # 今回のセッション用の一意なフォルダを作成 (temp/session_uuid)
        session_id = str(uuid.uuid4())
        self.session_dir = self.BASE_TEMP_DIR / f"session_{session_id}"
        self.session_dir.mkdir(exist_ok=True)

        try:
            # pdf2image実行
            pil_images = convert_from_path(pdf_path)

            results = []
            for i, image in enumerate(pil_images):
                image_filename = f"page_{i + 1}.png"
                # pathlib.Path を str に変換して保存パスを作成
                save_path = self.session_dir / image_filename

                # 画像保存
                image.save(str(save_path), "PNG")

                # Fletで表示するために絶対パスの文字列として格納
                results.append(
                    PageImage(
                        path=str(save_path.absolute()), width=image.width, height=image.height
                    )
                )

            self.page_images = results
            return results

        except Exception as e:
            # エラー時は即座にクリーンアップして再送出
            self.cleanup()
            raise e

    def cleanup(self) -> None:
        """
        現在のセッションの一時ディレクトリと画像ファイルを削除する
        """
        if self.session_dir and self.session_dir.exists():
            try:
                shutil.rmtree(self.session_dir)
            except OSError as e:
                print(f"Error checking cleanup: {e}")
            finally:
                self.session_dir = None
                self.page_images = []
