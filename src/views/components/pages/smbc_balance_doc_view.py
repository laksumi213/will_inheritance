# /components/pages/smbc_balance_doc_view.py
import os
from pprint import pprint

import jaconv
import mojimoji
from flet import Colors, Column, Divider, ElevatedButton, FontWeight, Page, Text

from components.utils.pdf_create import PdfCreate

# 💡 汎用的な関数名に変更
from services.deceased_service import get_bank_cert_document_data, get_case_folder_path_service


def SmbcBalanceDocView(page: Page, case_id: int, bank_code: str):
    # 💡 データベースから必要な全ての情報を取得 (bank_codeを引数に追加)
    data = get_bank_cert_document_data(case_id, bank_code)
    print()
    pprint(data)
    print()

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
    d_name = f"{data['deceased']['last_name']} {data['deceased']['first_name']}"
    c_name = f"{data['contracting_party'].get('last_name', '')} {data['contracting_party'].get('first_name', '')}"

    bank_assets = data.get("bank_assets", [])
    bank_name = bank_assets[0]["bank_name"] if bank_assets else "銀行名不明"

    # 申請書作成ボタンが押されたときのハンドラ
    def handle_balance_certificate(e, mailing=False):
        if mailing:
            balance_certificate_mailing(
                data=data,
                bank_code=bank_code,
                case_id=case_id, # 💡 case_id を渡す
            )
        else:
            balance_certificate(
                data=data,
                bank_code=bank_code,
                case_id=case_id, # 💡 case_id を渡す
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
            ElevatedButton(
                "作成（郵送専用）", on_click=lambda e: handle_balance_certificate(e, mailing=True)
            ),
            ElevatedButton("作成（窓口用）", on_click=lambda e: handle_balance_certificate(e)),
        ]
    )


def balance_certificate(data: dict, bank_code: str, case_id: int): # 💡 case_id 引数を追加
    # --- 1. データ展開 ---

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

    # 契約者氏名（スペースなし）をフォルダパスに使用（フォールバック用）
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
            # DBにパスがない場合のフォールバック
            output_directory = rf"\\192.168.11.20\行政書士法人チェスター\01.個別ＪＯＢ\{case_number}{contractor_name_for_path}"
            print(f"DBにパスがないためフォールバックパスを使用: {output_directory}")

    elif os.name == "posix":
        print("POSIX環境の処理 (Mac/Linux)")
        output_path = os.path.dirname(os.path.dirname(__file__))  # デバッグ用パス

        # 💡 実際の出力パスを構築
        output_directory = os.path.join(output_path, "generated_pdfs")
        os.makedirs(output_directory, exist_ok=True)

    pdf = PdfCreate("A4")

    pdf.draw_string(62, 264, d_name)
    pdf.draw_string(62, 257, c_name)

    # 電話番号
    pdf.draw_string(125, 254, "050-6864-7034", 12)

    pdf.draw_string(50, 233, branch_name, 12)
    pdf.draw_string(88, 233, branch_code[0], 12)
    pdf.draw_string(92.5, 233, branch_code[1], 12)
    pdf.draw_string(97, 233, branch_code[2], 12)

    if '普通' in account_type:
        pdf.draw_string(101.5, 232.5, '〇', 12)
    elif '当座' in account_type:
        pdf.draw_string(109, 232.5, '〇', 12)
    else:
        pdf.draw_string(118, 232.5, account_type, 8)

    pdf.draw_string(130, 232, account_number[0], 12)
    pdf.draw_string(134, 232, account_number[1], 12)
    pdf.draw_string(138.5, 232, account_number[2], 12)
    pdf.draw_string(143, 232, account_number[3], 12)
    pdf.draw_string(147.3, 232, account_number[4], 12)
    pdf.draw_string(152, 232, account_number[5], 12)
    pdf.draw_string(156.5, 232, account_number[6], 12)

    pdf.draw_string(110, 189, f'担当：森町({case_number})', 10)

    if d_death_date:
        year_str = str(d_death_date.year)[2:]
        year_draw = "     ".join(list(year_str))
        pdf.draw_string(63, 142, year_draw, 12)

        month_str = str(d_death_date.month).zfill(2)
        month_draw = "     ".join(list(month_str))
        pdf.draw_string(85, 142, month_draw, 12)

        day_str = str(d_death_date.day).zfill(2)
        day_draw = "     ".join(list(day_str))
        pdf.draw_string(109, 142, day_draw, 12)

    filename = f"{case_number}_{d_name}_{bank_name}_残高証明書依頼書.pdf"
    path1 = os.path.join(output_directory, filename)

    pdf.pdf_save(
        path1,
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)) + "/assets/pdf",
            "三井住友銀行_残高証明書依頼書.pdf",
        ),
        page=1,
        open_bool=True,
    )


def balance_certificate_mailing(data: dict, bank_code: str, case_id: int):
    # --- 1. データ展開 ---

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
            # DBにパスがない場合のフォールバック
            output_directory = rf"\\192.168.11.20\行政書士法人チェスター\01.個別ＪＯＢ\{case_number}{contractor_name_for_path}"
            print(f"DBにパスがないためフォールバックパスを使用: {output_directory}")

    elif os.name == "posix":
        print("POSIX環境の処理 (Mac/Linux)")
        output_path = os.path.dirname(os.path.dirname(__file__))  # デバッグ用パス

        # 💡 実際の出力パスを構築
        output_directory = os.path.join(output_path, "generated_pdfs")
        os.makedirs(output_directory, exist_ok=True)

    pdf = PdfCreate("A4")

    pdf.draw_string(52, 259, "103-0028")
    pdf.draw_string(52, 249, "東京", 12)
    pdf.draw_string(73, 251.5, "〇", 14)
    pdf.draw_string(84, 249, "東京都中央区八重洲一丁目7-20 八重洲口会館2階", 12)

    # 氏名
    pdf.draw_string(57, 240, f"ｿｳｿﾞｸﾆﾝ　{mojimoji.zen_to_han(jaconv.hira2kata(c_kana))}")
    pdf.draw_string(57, 236.5, "ﾀﾞｲﾘﾆﾝ　ｷﾞｮｳｾｲｼｮｼﾎｳｼﾞﾝﾁｪｽﾀｰ　ﾀﾞｲﾋｮｳｼｬｲﾝ　ｼﾐｽﾞ ｾﾝｻｸ")
    pdf.draw_string(57, 232, f"相続人　{c_name}")
    pdf.draw_string(57, 228, "代理人　行政書士法人チェスター　代表社員　清水　茜作")

    # 電話番号
    pdf.draw_string(54, 221, "050　　　6864　　　7034", 12)

    # 被相続人
    pdf.draw_string(57, 187, mojimoji.zen_to_han(jaconv.hira2kata(d_kana)))
    pdf.draw_string(57, 174, d_name, 14)
    pdf.draw_string(173, 180.5, "〇", 18)

    filename = f"{case_number}_{d_name}_{bank_name}_残高証明書依頼書_郵送専用.pdf"
    path1 = os.path.join(output_directory, filename)

    pdf.pdf_save(
        path1,
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)) + "/assets/pdf",
            "三井住友銀行_残高証明書依頼書_郵送専用.pdf",
        ),
        page=1,
        open_bool=True,
    )
