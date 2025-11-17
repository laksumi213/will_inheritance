# /components/pages/smbc_balance_doc_view.py
import os

from flet import Colors, Column, Divider, ElevatedButton, FontWeight, Page, Text

from components.utils.pdf_create import PdfCreate

# 💡 汎用的な関数名に変更
from services.deceased_service import get_bank_cert_document_data


def SmbcBalanceDocView(page: Page, case_id: int, bank_code: str):
    # 💡 データベースから必要な全ての情報を取得 (bank_codeを引数に追加)
    data = get_bank_cert_document_data(case_id, bank_code)

    # データを取得できなかった場合のフォールバック
    if not data:
        return Column(
            controls=[
                Text(
                    "エラー: 案件情報または指定された銀行コードの口座情報が見つかりません。",
                    size=20,
                    color=Colors.RED_700,
                ),
                Divider(),
                ElevatedButton(
                    "戻る", on_click=lambda e: page.go(f"/case/{case_id}/doc/balance_cert")
                ),
            ]
        )

    # 💡 取得したデータからPDF作成に必要な変数を展開
    case_number = data["case_number"]

    d_name = f"{data['deceased']['last_name']} {data['deceased']['first_name']}"
    d_kana = f"{data['deceased']['last_kana']} {data['deceased']['first_kana']}"
    # 住所はそのまま PDF 関数に渡すか、必要に応じてここで整形
    d_address_info = data["deceased"]["address"]

    c_name = f"{data['contracting_party'].get('last_name', '')} {data['contracting_party'].get('first_name', '')}"
    c_phone = data["contracting_party"].get("phone", "N/A")

    # 銀行名を取得 (最初の口座から取得)
    bank_assets = data["bank_assets"]
    bank_name = bank_assets[0]["bank_name"] if bank_assets else "銀行名不明"

    # 申請書作成ボタンが押されたときのハンドラ
    def handle_balance_certificate(e):
        # 💡 PDF作成関数に展開した変数を渡す
        balance_certificate(
            case_number=case_number,
            deceased_name=d_name,
            contractor_name=c_name,
            bank_name=bank_name,
            # 必要に応じて他の情報も渡す
        )

    return Column(
        controls=[
            # 💡 表示する銀行名を動的に変更
            Text(
                f"📝 {bank_name} ({bank_code}) 残高証明書申請書作成フォーム",
                size=24,
                weight=FontWeight.BOLD,
                color=Colors.BLUE,
            ),
            Divider(),
            Text(f"【案件ID: {case_id} / 銀行コード: {bank_code}】", size=16),
            Text(f"被相続人: {d_name} / 契約者: {c_name}", size=14, color=Colors.BLACK87),
            Text(f"対象口座数: {len(bank_assets)}", size=14, color=Colors.BLACK87),
            # 💡 申請ボタンのハンドラを更新
            ElevatedButton("作成（郵送専用）", on_click=handle_balance_certificate),
            # ElevatedButton("作成（窓口用）", on_click=handle_balance_certificate),
        ]
    )


# 💡 PDF作成関数に引数を追加
def balance_certificate(case_number: str, deceased_name: str, contractor_name: str, bank_name: str):
    if os.name == "nt":
        print("Windows環境の処理")
    elif os.name == "posix":
        print("POSIX環境の処理 (Mac/Linux)")
        output_path = os.path.dirname(os.path.dirname(__file__))  # デバッグ用パス

    # 💡 実際の出力パスを構築
    output_directory = os.path.join(output_path, "generated_pdfs")
    os.makedirs(output_directory, exist_ok=True)

    pdf = PdfCreate("A4")

    # 💡 取得したデータを利用してPDFに情報を描画
    pdf.draw_string(23, 188, "行政書士法人チェスター　代表社員　清水　茜作", 10)
    pdf.draw_string(63, 55, "東京都中央区八重洲1-7-20 八重洲口会館2階", 12)
    # pdf.draw_string(23, 193, f"被相続人　{deceased_name}", 10)

    filename = f"{case_number}_{deceased_name}_{bank_name}_残高証明書依頼書_郵送専用.pdf"
    path1 = os.path.join(output_directory, filename)

    # 💡 PDFテンプレートも動的に変更する必要がありますが、ここでは三井住友銀行のものを流用します。
    pdf.pdf_save(
        path1,
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)) + "/assets/pdf",
            "三井住友銀行_残高証明書依頼書_郵送専用.pdf",
        ),
        page=1,
        open_bool=True,
    )
