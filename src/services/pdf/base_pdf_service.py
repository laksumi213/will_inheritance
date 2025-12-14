# src/services/pdf/base_pdf_service.py
import os
from abc import ABC, abstractmethod
from datetime import datetime

from src.config import settings
from src.services.deceased_service import (
    get_case_by_id,
    get_case_folder_path,
    get_deceased_by_case_id,
)
from src.utils.pdf_writer import PdfFormWriter


class BaseBankPdfService(ABC):
    """銀行書類作成の基底クラス"""

    def __init__(self, case_id: int):
        self.case_id = case_id
        self.case = get_case_by_id(case_id)
        self.deceased = get_deceased_by_case_id(case_id)

        if not self.case or not self.deceased:
            raise ValueError("案件情報または被相続人情報が見つかりません")

    @property
    @abstractmethod
    def template_filename(self) -> str:
        """テンプレートPDFファイル名（サブクラスで定義）"""
        pass

    @property
    @abstractmethod
    def output_filename_prefix(self) -> str:
        """出力ファイル名の接頭辞（例: 'auじぶん銀行_相続届'）"""
        pass

    @property
    @abstractmethod
    def ref_width(self) -> int:
        """座標取得時の基準幅 (ツールで取得したpx値)"""
        pass

    @abstractmethod
    def draw_content(self, writer: PdfFormWriter):
        """
        具体的な書き込みロジック（サブクラスで実装）
        writer.draw_text(...) をここに記述する
        """
        pass

    def execute(self) -> str:
        """
        実行メイン処理: パス解決 -> 書き込み -> 保存
        戻り値: 保存されたファイルのパス
        """
        # 1. パス解決
        input_pdf_path = settings.ASSETS_DIR / "pdf" / self.template_filename
        if not input_pdf_path.exists():
            raise FileNotFoundError(f"テンプレートが見つかりません: {input_pdf_path}")

        case_folder = get_case_folder_path(self.case_id)
        if case_folder and os.path.exists(case_folder):
            output_dir = case_folder
        else:
            output_dir = settings.BASE_DIR / "output"
            os.makedirs(output_dir, exist_ok=True)

        today_str = datetime.now().strftime("%Y%m%d")

        file_name = f"{self.case.case_number}{self.deceased.name_last}様_{self.output_filename_prefix}_{today_str}.pdf"
        output_pdf_path = os.path.join(output_dir, file_name)

        # 2. PDF生成
        try:
            with PdfFormWriter(str(input_pdf_path), output_pdf_path) as writer:
                self.draw_content(writer)
                writer.save()

            return output_pdf_path
        except Exception as e:
            raise RuntimeError(
                f"PDF作成中にエラーが発生しました ({self.output_filename_prefix}): {e}"
            )
