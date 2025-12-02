# /components/pages/mizuho_balance_doc_view.py
import os
from datetime import datetime
from pprint import pprint

from flet import (
    Colors,
    Column,
    Divider,
    Dropdown,
    ElevatedButton,
    FontWeight,
    Page,
    SnackBar,
    Text,
    dropdown,
)

from components.utils.pdf_create import PdfCreate
from services.deceased_service import get_bank_cert_document_data, get_case_folder_path_service


def MizuhoBalanceDocView(page: Page, case_id: int, bank_code: str):
    # 💡 データベースから必要な全ての情報を取得
    data = get_bank_cert_document_data(case_id, bank_code)

    # デバッグ出力
    print()
    pprint(data)
    print()

    # --- 口座選択用ドロップダウンの作成 ---
    bank_assets = data.get("bank_assets", [])

    # 選択肢の作成: 「すべて」を先頭に、以降は口座番号を追加
    account_options = [dropdown.Option("all", "すべて")]
    if bank_assets:
        for asset in bank_assets:
            acc_num = asset.get("account_number")
            if acc_num:
                account_options.append(dropdown.Option(acc_num, acc_num))

    account_selector = Dropdown(
        label="取引明細 対象口座",
        options=account_options,
        value="all",
        width=200,
    )

    # 取引明細作成処理
    def trading_item(e):
        case_number = data["case_number"]

        deceased = data["deceased"]
        d_name = f"{deceased['last_name']} {deceased['first_name']}"
        # d_kana = f"{deceased['last_kana']} {deceased['first_kana']}" # PDF描画で未使用であればコメントアウト
        # d_death_date = deceased.get("date_of_death") # 未使用

        contractor = data["contracting_party"]
        c_name = f"{contractor.get('last_name', '')} {contractor.get('first_name', '')}"

        # --- 保存先ディレクトリの決定 ---
        output_directory = ""
        if os.name == "nt":
            output_directory = get_case_folder_path_service(case_id)
            if not output_directory:
                page.open(
                    SnackBar(
                        Text("フォルダパスが保存されていないため作成できませんでした。"),
                        bgcolor=Colors.RED,
                    )
                )
                return
            # パスの末尾にセパレータがない場合は追加
            if not output_directory.endswith(os.sep):
                output_directory += os.sep
        elif os.name == "posix":
            output_path = os.path.dirname(os.path.dirname(__file__))
            output_directory = os.path.join(output_path, "generated_pdfs")
            os.makedirs(output_directory, exist_ok=True)
            output_directory += os.sep

        # --- 対象資産のフィルタリング ---
        selected_account = account_selector.value
        target_assets = []

        if selected_account == "all":
            target_assets = bank_assets
        else:
            # 選択された口座番号に一致するものだけ抽出
            target_assets = [a for a in bank_assets if a.get("account_number") == selected_account]

        if not target_assets:
            page.open(SnackBar(Text("対象となる口座情報がありません。"), bgcolor=Colors.RED))
            return

        created_count = 0

        # --- ループ処理: 各口座ごとにPDFを作成 ---
        for asset in target_assets:
            branch_code = asset.get("branch_code", "")
            account_type = asset.get("account_type", "")
            account_number = asset.get("account_number", "")

            if not account_number:
                print("スキップ: 口座番号がない資産があります")
                continue

            pdf = PdfCreate("A4")

            # 郵便番号
            pdf.draw_string(36.5, 258, "1  9  3")
            pdf.draw_string(53, 258, "0  0  2  8")

            # 電話番号
            pdf.draw_string(139, 258, "050")
            pdf.draw_string(159, 258, "6864")
            pdf.draw_string(182, 258, "7034")

            # 住所
            pdf.draw_string(35, 247, "東京都中央区八重洲一丁目7-20  八重洲口会館2階", 12)

            # 氏名
            pdf.draw_string(35, 233, f"被相続人  {d_name}  相続人 {c_name}", 12)
            pdf.draw_string(35, 227, "代理人  行政書士法人チェスター  代表社員  清水  茜作", 12)

            # 対象口座
            if branch_code:
                branch_code_drow = "    ".join(list(str(branch_code).zfill(3)))
                pdf.draw_string(20.2, 191, branch_code_drow, 14)

            if "普通" in account_type:
                pdf.draw_string(47, 194, "〇", 18)
            elif "当座" in account_type:
                pdf.draw_string(60, 194, "〇", 18)
            else:
                pdf.draw_string(47, 188, "〇", 18)

            account_number_drow = "    ".join(list(str(account_number).zfill(7)))
            pdf.draw_string(72.5, 191, account_number_drow, 14)

            # 手数料支払い
            pdf.draw_string(117.5, 110, "✓", 16)
            pdf.draw_string(148, 110, "現金", 12)

            # --- ファイル名生成 ---
            # 形式: {案件番号}_{被相続人}様_みずほ銀行_取引明細_{口座番号}_{年月日}.pdf
            today_str = datetime.now().strftime("%Y%m%d")
            filename = (
                f"{case_number}_{d_name}様_みずほ銀行_取引明細_{account_number}_{today_str}.pdf"
            )

            save_path = os.path.join(output_directory, filename)

            try:
                pdf.pdf_save(
                    save_path,
                    os.path.join(
                        os.path.dirname(os.path.dirname(__file__)) + "/assets/pdf",
                        "みずほ銀行_取引明細申請書.pdf",
                    ),
                    page=1,
                    open_bool=True,  # 最後の1枚だけ開く、または全て開くかはお好みで
                )
                print(f"保存完了: {save_path}")
                created_count += 1

            except Exception as ex:
                # フォルダ構成が異なる場合のフォールバック (Windows固有パス)
                print(f"保存エラー(初回): {ex}")
                try:
                    fallback_path = rf"{output_directory}09.申請書類\01.残証申請書類\{filename}"
                    pdf.pdf_save(
                        fallback_path,
                        os.path.join(
                            os.path.dirname(os.path.dirname(__file__)) + "/assets/pdf",
                            "みずほ銀行_取引明細申請書.pdf",
                        ),
                        page=1,
                        open_bool=True,
                    )
                    created_count += 1
                except Exception as ex2:
                    print(f"保存エラー(フォールバック): {ex2}")
                    page.open(
                        SnackBar(
                            Text(f"保存に失敗しました ({account_number}): {ex2}"),
                            bgcolor=Colors.RED,
                        )
                    )

        if created_count > 0:
            page.open(
                SnackBar(
                    Text(f"{created_count}件の取引明細を作成しました"), bgcolor=Colors.GREEN_500
                )
            )

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
            # 残高証明書作成ボタン (引数を正しく渡すよう修正)
            ElevatedButton(
                "残高証明書 作成", on_click=lambda e: balance_certificate(data, bank_code, case_id)
            ),
            Divider(),
            # 口座選択ドロップダウンを追加
            account_selector,
            ElevatedButton("取引明細 作成", on_click=lambda e: trading_item(e)),
        ]
    )


def balance_certificate(data: dict, bank_code: str, case_id: int):
    case_number = data["case_number"]

    deceased = data["deceased"]
    # d_name = f"{deceased['last_name']} {deceased['first_name']}" # PDF内で使用されていないためコメントアウト
    # d_kana = f"{deceased['last_kana']} {deceased['first_kana']}"
    # d_address = deceased["address"]

    contractor = data["contracting_party"]
    c_name = f"{contractor.get('last_name', '')} {contractor.get('first_name', '')}"
    c_kana = f"{contractor.get('last_kana', '')} {contractor.get('first_kana', '')}"
    # c_phone = contractor.get("phone", "")

    # 銀行情報 (ここでは最初の口座を使用すると仮定)
    bank_assets = data["bank_assets"]
    bank_name = bank_assets[0]["bank_name"] if bank_assets else "銀行名不明"
    # branch_name = bank_assets[0].get("branch_name", "") if bank_assets else ""

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
            # pageオブジェクトがないためprintで代替、または例外を投げる
            print("フォルダパスが設定されていません")
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

    # 残高証明書のファイル名設定 (ここも日付を入れるか検討できますが、今回は元のままにしています)
    path1 = os.path.join(
        output_directory,  # 変数名を統一
        f"{case_number}_様_みずほ銀行_残高証明書.pdf",
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
