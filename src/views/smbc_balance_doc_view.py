# src/views/smbc_balance_doc_view.py
import os

from flet import Colors, Column, Divider, ElevatedButton, Page, SnackBar, Text

from src.services.deceased_service import get_bank_cert_document_data, get_case_folder_path
from src.utils.pdf_writer import PdfWriter


def SmbcBalanceDocView(page: Page, case_id: int, bank_code: str):
    data = get_bank_cert_document_data(case_id, bank_code)

    if not data:
        return Text("データなし", color=Colors.RED)

    def create_pdf(e):
        folder = get_case_folder_path(case_id)
        if not folder:
            return

        try:
            writer = PdfWriter("assets/fonts/ipaexg.ttf")
            out_path = os.path.join(folder, "smbc_req.pdf")
            draw_data = [{"x": 100, "y": 600, "value": "SMBC Sample"}]
            writer.create_overlay_pdf(out_path, draw_data)
            page.open(SnackBar(Text("作成完了"), bgcolor=Colors.GREEN))
        except Exception as ex:
            page.open(SnackBar(Text(f"エラー: {ex}"), bgcolor=Colors.RED))

    return Column(
        [
            Text("三井住友銀行 残高証明書作成", size=24, weight="bold"),
            Divider(),
            ElevatedButton("作成", on_click=create_pdf),
        ]
    )
