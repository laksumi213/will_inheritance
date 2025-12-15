# src/services/pdf/banks/au_jibun.py
from src.services.pdf.base_pdf_service import BaseBankPdfService
from src.utils.pdf_writer import PdfFormWriter


class AuJibunBankService(BaseBankPdfService):
    """auじぶん銀行 相続届 作成サービス"""

    @property
    def template_filename(self) -> str:
        # assets/pdf/auじぶん銀行_相続届.pdf が存在することを前提
        return "auじぶん銀行_相続届.pdf"

    @property
    def output_filename_prefix(self) -> str:
        return "auじぶん銀行_相続届"

    @property
    def ref_width(self) -> int:
        # ツールで取得した画像の横幅 (FletのImageサイズではなく、PDF変換時のpx幅)
        # 200dpiなら通常 1654 px 程度です
        return 1654

    def draw_content(self, writer: PdfFormWriter):
        """
        ここに generate_pdf_test.py で確認した draw_text コードを移植します。
        'value_0' などの仮の値を、self.deceased や self.case の実データに置き換えます。
        """

        # 1. 被相続人氏名 (value_0 に相当)
        full_name = f"{self.deceased.name_last} {self.deceased.name_first}"
        writer.draw_text(
            page=1, x=733, y=412, text=full_name, font_size=11, ref_width=self.ref_width
        )

        # 2. 死亡日 (value_1, value_2 に相当)
        if self.deceased.date_of_death:
            # 年
            writer.draw_text(
                page=1,
                x=846,
                y=407,
                text=str(self.deceased.date_of_death.year),
                font_size=11,
                ref_width=self.ref_width,
            )
            # 月
            writer.draw_text(
                page=1,
                x=971,
                y=407,
                text=str(self.deceased.date_of_death.month),
                font_size=11,
                ref_width=self.ref_width,
            )
            # 日 (もしあれば)
            writer.draw_text(
                page=1,
                x=1050,  # 仮の座標
                y=407,
                text=str(self.deceased.date_of_death.day),
                font_size=11,
                ref_width=self.ref_width,
            )

        # 3. 依頼者（契約者）名
        # 必要であれば追加
        writer.draw_text(
            page=1,
            x=500,  # 仮
            y=600,  # 仮
            text=self.case.client_name,
            font_size=11,
            ref_width=self.ref_width,
        )
