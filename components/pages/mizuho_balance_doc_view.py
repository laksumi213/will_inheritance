# /components/pages/mizuho_balance_doc_view.py
import os
from pprint import pprint
import jaconv
import mojimoji
from flet import Colors, Column, Divider, ElevatedButton, FontWeight, Page, Text, SnackBar

from components.utils.pdf_create import PdfCreate
from services.deceased_service import get_bank_cert_document_data, get_case_folder_path_service


def MizuhoBalanceDocView(page: Page, case_id: int, bank_code: str):

    # 取引明細
    def trading_item(e):
        print()
        pprint(data)
        print()
        case_number = data["case_number"]

        deceased = data["deceased"]
        d_name = f"{deceased['last_name']} {deceased['first_name']}"
        d_kana = f"{deceased['last_kana']} {deceased['first_kana']}"
        d_death_date = deceased.get("date_of_death")
        # d_address = deceased["address"] # 未使用

        contractor = data["contracting_party"]
        c_name = f"{contractor.get('last_name', '')} {contractor.get('first_name', '')}"
        c_kana = f"{contractor.get('last_kana', '')} {contractor.get('first_kana', '')}"
        # c_phone = contractor.get("phone", "") # 未使用

        # 銀行情報
        bank_assets = data["bank_assets"]
        bank_name = bank_assets[0]["bank_name"] if bank_assets else ""
        branch_name = bank_assets[0]["branch_name"] if bank_assets else ""
        branch_code = bank_assets[0]["branch_code"] if bank_assets else ""
        account_type = bank_assets[0]["account_type"] if bank_assets else ""
        account_number = bank_assets[0]["account_number"] if bank_assets else ""

        # --- 2. ファイルパス構築 ---
        if os.name == "nt":
            output_directory = get_case_folder_path_service(case_id)
            if not output_directory:
                page.open(SnackBar(Text("フォルダパスが保存されていないため作成できませんでした。"), bgcolor=Colors.RED))
                return

        if not account_number:
            page.open(SnackBar(Text("銀行口座が登録されていません。"), bgcolor=Colors.RED))
            return

        pdf = PdfCreate("A4")
        
        # 郵便番号
        pdf.draw_string(36.5, 258, '1  9  3')
        pdf.draw_string(53, 258, '0  0  2  8')
        
        # 電話番号
        pdf.draw_string(139, 258, '050')
        pdf.draw_string(159, 258, '6864')
        pdf.draw_string(182, 258, '7034')

        # 住所
        pdf.draw_string(35, 247, '東京都中央区八重洲一丁目7-20  八重洲口会館2階', 12)

        # 氏名
        pdf.draw_string(35, 233, f'被相続人  {d_name}  相続人 {c_name}', 12)
        pdf.draw_string(35, 227, f'代理人  行政書士法人チェスター  代表社員  清水  茜作', 12)

        # 対象口座
        if branch_code:
            branch_code_drow = "    ".join(list(str(branch_code).zfill(3)))
            pdf.draw_string(20.2, 191, branch_code_drow, 14)

        if '普通' in account_type:
            pdf.draw_string(47, 194, '〇', 18)
        elif '当座' in account_type:
            pdf.draw_string(60, 194, '〇', 18)
        else:
            pdf.draw_string(47, 188, '〇', 18)

        account_number_drow = "    ".join(list(str(account_number).zfill(7)))
        pdf.draw_string(72.5, 191, account_number_drow, 14)
        
        # 手数料支払い
        pdf.draw_string(117.5, 110, '✓', 16)
        pdf.draw_string(148, 110, '現金', 12)

        try:
            pdf.pdf_save(
                f"{output_directory}{case_number}_{d_name}様_みずほ銀行_残高証明書.pdf",
                os.path.join(
                    os.path.dirname(os.path.dirname(__file__)) + "/assets/pdf",
                    "みずほ銀行_取引明細申請書.pdf",
                ),
                page=1,
                open_bool=True,
            )
            page.open(SnackBar(Text(f"{output_directory}に保存しました"), bgcolor=Colors.GREEN_500, duration=600000))

        except e:
            pdf.pdf_save(
                rf"{output_directory}\09.申請書類\01.残証申請書類\{case_number}_{d_name}様_みずほ銀行_残高証明書.pdf",
                os.path.join(
                    os.path.dirname(os.path.dirname(__file__)) + "/assets/pdf",
                    "みずほ銀行_取引明細申請書.pdf",
                ),
                page=1,
                open_bool=True,
            )
            page.open(SnackBar(Text(f"09.申請書類\01.残証申請書類のフォルダがないため、{output_directory}に保存しました"), bgcolor=Colors.RED, duration=600000))
            

    # 💡 データベースから必要な全ての情報を取得 (bank_codeを引数に追加)
    data = get_bank_cert_document_data(case_id, bank_code)
    print()
    pprint(data)
    print()

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
            ElevatedButton("残高証明書 作成", on_click=lambda e: balance_certificate()),
            Divider(),
            ElevatedButton("取引明細 作成", on_click=lambda e: trading_item(e)),
        ]
    )

def balance_certificate(data: dict, bank_code: str, case_id: int):
    case_number = data["case_number"]

    deceased = data["deceased"]
    d_name = f"{deceased['last_name']} {deceased['first_name']}"
    d_kana = f"{deceased['last_kana']} {deceased['first_kana']}"
    d_address = deceased["address"]

    contractor = data["contracting_party"]
    c_name = f"{contractor.get('last_name', '')} {contractor.get('first_name', '')}"
    c_kana = f"{contractor.get('last_kana', '')} {contractor.get('first_kana', '')}"
    c_phone = contractor.get("phone", "")

    # 銀行情報 (ここでは最初の口座を使用すると仮定)
    bank_assets = data["bank_assets"]
    bank_name = bank_assets[0]["bank_name"] if bank_assets else "銀行名不明"
    branch_name = bank_assets[0].get("branch_name", "") if bank_assets else ""

    # 契約者氏名（スペースなし）をフォルダパスに使用
    contractor_name_for_path = c_name.replace(" ", "").replace("　", "")

    # --- 2. ファイルパス構築 ---
    if os.name == "nt":
        print("Windows環境の処理")
        # 💡 データベースからパスを取得
        db_path = get_case_folder_path_service(case_id)
        if db_path:
            output_directory = db_path
            print(f"DBから取得したパスを使用: {output_directory}")
        else:
            page.open()
            return

    elif os.name == "posix":
        print("POSIX環境の処理 (Mac/Linux)")
        output_path = os.path.dirname(os.path.dirname(__file__))  # デバッグ用パス

        # 💡 実際の出力パスを構築
        output_directory = os.path.join(output_path, "generated_pdfs")
        os.makedirs(output_directory, exist_ok=True)

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



    