# src/views/mizuho_balance_doc_view.py
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

# 💡 修正: PdfCreate は汎用ユーティリティのため src/utils からインポート
from src.utils.pdf_create import PdfCreate
from src.services.deceased_service import get_bank_cert_document_data, get_case_folder_path_service
from src.config import settings

def MizuhoBalanceDocView(page: Page, case_id: int, bank_code: str):
    # データベースから必要な全ての情報を取得
    data = get_bank_cert_document_data(case_id, bank_code)

    # デバッグ出力
    print("--- Mizuho Doc Data ---")
    pprint(data)
    print("-----------------------")

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
        case_number = data.get("case_number", "")
        
        deceased = data.get("deceased", {})
        d_name = f"{deceased.get('last_name', '')} {deceased.get('first_name', '')}".strip()
        
        contractor = data.get("contracting_party", {})
        c_name = f"{contractor.get('last_name', '')} {contractor.get('first_name', '')}".strip()

        # --- 保存先ディレクトリの決定 ---
        output_directory = ""
        db_path = get_case_folder_path_service(case_id)
        
        if db_path and os.path.exists(db_path):
            output_directory = db_path
            if not output_directory.endswith(os.sep):
                output_directory += os.sep
        else:
            # フォールバック: outputディレクトリ
            output_directory = os.path.join(settings.BASE_DIR, "output")
            os.makedirs(output_directory, exist_ok=True)
            output_directory += os.sep
            
            page.open(
                SnackBar(
                    Text(f"フォルダパス未設定のため、{output_directory} に保存します。"),
                    bgcolor=Colors.ORANGE_700,
                )
            )

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

            # 郵便番号 (固定値)
            pdf.draw_string(36.5, 258, "1  9  3")
            pdf.draw_string(53, 258, "0  0  2  8")

            # 電話番号 (固定値)
            pdf.draw_string(139, 258, "050")
            pdf.draw_string(159, 258, "6864")
            pdf.draw_string(182, 258, "7034")

            # 住所 (固定値)
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
                pdf.draw_string(47, 188, "〇", 18) # その他

            account_number_drow = "    ".join(list(str(account_number).zfill(7)))
            pdf.draw_string(72.5, 191, account_number_drow, 14)

            # 手数料支払い
            pdf.draw_string(117.5, 110, "✓", 16)
            pdf.draw_string(148, 110, "現金", 12)

            # --- ファイル名生成 ---
            today_str = datetime.now().strftime("%Y%m%d")
            filename = (
                f"{case_number}_{d_name}様_みずほ銀行_取引明細_{account_number}_{today_str}.pdf"
            )

            save_path = os.path.join(output_directory, filename)
            
            # テンプレートPDFのパス
            template_path = settings.ASSETS_DIR / "pdf" / "みずほ銀行_取引明細申請書.pdf"

            try:
                if not template_path.exists():
                    raise FileNotFoundError(f"Template not found: {template_path}")

                pdf.pdf_save(
                    save_path,
                    str(template_path),
                    page=1,
                    open_bool=True,
                )
                print(f"保存完了: {save_path}")
                created_count += 1

            except Exception as ex:
                print(f"保存エラー: {ex}")
                page.open(
                    SnackBar(
                        Text(f"保存に失敗しました ({account_number}): {ex}"),
                        bgcolor=Colors.RED,
                    )
                )

        if created_count > 0:
            page.open(
                SnackBar(
                    Text(f"{created_count}件の取引明細を作成しました"), bgcolor=Colors.GREEN_500
                )
            )
        page.update()

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
            ElevatedButton(
                "残高証明書 作成", on_click=lambda e: balance_certificate(page, data, bank_code, case_id)
            ),
            Divider(),
            account_selector,
            ElevatedButton("取引明細 作成", on_click=lambda e: trading_item(e)),
        ]
    )


def balance_certificate(page: Page, data: dict, bank_code: str, case_id: int):
    """残高証明書PDF作成ロジック"""
    case_number = data.get("case_number", "")
    
    # 契約者氏名
    contractor = data.get("contracting_party", {})
    c_name = f"{contractor.get('last_name', '')} {contractor.get('first_name', '')}".strip()

    # --- 2. ファイルパス構築 ---
    db_path = get_case_folder_path_service(case_id)
    if db_path and os.path.exists(db_path):
        output_directory = db_path
    else:
        output_directory = os.path.join(settings.BASE_DIR, "output")
        os.makedirs(output_directory, exist_ok=True)

    pdf = PdfCreate("A4")

    pdf.draw_string(23, 188, "行政書士法人チェスター　代表社員　清水　茜作", 10)
    pdf.draw_string(63, 55, "東京都中央区八重洲1-7-20 八重洲口会館2階", 12)

    path1 = os.path.join(
        output_directory,
        f"{case_number}_様_みずほ銀行_残高証明書.pdf",
    )
    
    template_path = settings.ASSETS_DIR / "pdf" / "みずほ銀行_残高証明書.pdf"

    try:
        if not template_path.exists():
             raise FileNotFoundError(f"Template not found: {template_path}")

        pdf.pdf_save(
            path1,
            str(template_path),
            page=1,
            open_bool=True,
        )
        page.open(SnackBar(Text("残高証明書を作成しました"), bgcolor=Colors.GREEN))
        page.update()
    except Exception as e:
        page.open(SnackBar(Text(f"エラー: {e}"), bgcolor=Colors.RED))
        page.update()