# /components/pages/mizuho_balance_doc_view.py
import os

from flet import Colors, Column, Divider, ElevatedButton, FontWeight, Page, Text

from components.utils.pdf_create import PdfCreate


def MizuhoBalanceDocView(page: Page, case_id: int, bank_code: str):
    # 💡 みずほ銀行専用のフォームコントロールを配置

    # 死亡日と異なる特定の日付での残高証明が必要な場合などに対応したフォーム...

    return Column(
        controls=[
            Text(
                "📝 みずほ銀行 (0001) 専用申請フォーム",
                size=24,
                weight=FontWeight.BOLD,
                color=Colors.BLUE,
            ),
            Divider(),
            Text(f"【案件ID: {case_id} / 銀行コード: {bank_code}】", size=16),
            # 💡 ここにみずほ銀行固有のフォーム（例：特殊な口座種別入力）を配置
            # ...
            ElevatedButton("作成", on_click=lambda e: balance_certificate()),
        ]
    )


def balance_certificate():
    if os.name == "nt":
        print("nt")
        # output_path = fr'\\192.168.11.20\行政書士法人チェスター\01.個別ＪＯＢ\{code}{heir_name.replace('　', '')}様（スタンダードプラン）\09.申請書類\01.残証申請書類'
    elif os.name == "posix":
        print("posix")
        output_path = os.path.dirname(os.path.dirname(__file__))
        # output_path = os.path.dirname(os.path.dirname(os.getcwd()))

    pdf = PdfCreate("A4")

    # pdf.draw_string(23, 193, f"相続人　{heir_name}　代理人", 10)
    pdf.draw_string(23, 188, "行政書士法人チェスター　代表社員　清水　茜作", 10)

    pdf.draw_string(63, 55, "東京都中央区八重洲1-7-20 八重洲口会館2階", 12)
    # pdf.draw_string(63, 37, f"行政書士法人チェスター　森町（{mojimoji.han_to_zen(code)}）", 12)

    path1 = os.path.join(
        output_path,
        "様_みずほ銀行_残高証明書.pdf",
        # output_path, f"{code}{heir[0]}様_SBI申請銀行_残高証明書依頼書.pdf"
    )

    pdf.pdf_save(
        path1,
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)) + "/assets/pdf",
            "みずほ銀行_残高証明書.pdf",
        ),
        page=1,
        open_bool=True,
    )
