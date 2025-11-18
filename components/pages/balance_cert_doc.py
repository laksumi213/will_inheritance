# /components/pages/balance_cert_doc.py
from flet import (
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    ElevatedButton,
    FontWeight,
    Icons,
    MainAxisAlignment,
    Page,
    Row,
    Text,
    border,
)

# 💡 既存の get_financial_asset_by_case 関数をインポート
from services.deceased_service import get_financial_asset_by_case


def BalanceCertDocView(page: Page, case_id: int):
    """
    残高証明申請書類作成の選択画面ビュー。
    案件に紐づく FinancialAsset (銀行) リストを銀行コードでグループ化して表示
    """

    # --- サービス層から金融資産リストを取得 ---
    financial_assets = get_financial_asset_by_case(case_id)

    # 💡【重要】銀行コードごとに口座情報をグループ化する
    grouped_banks = {}
    for asset in financial_assets:
        bank_code = asset.get("bank_code")
        bank_name = asset.get("bank_name")
        account_number = asset.get("account_number")

        if bank_code and bank_name:
            if bank_code not in grouped_banks:
                grouped_banks[bank_code] = {
                    "bank_name": bank_name,
                    # その銀行に紐づくすべての口座IDを格納
                    "asset_ids": [asset["id"]],
                    "account_numbers": [account_number],
                }
            else:
                grouped_banks[bank_code]["asset_ids"].append(asset["id"])
                grouped_banks[bank_code]["account_numbers"].append(account_number)

    # 案件に銀行が登録されていない場合のコントロール
    no_banks_content = Container(
        content=Column(
            [
                Text("⚠️ 銀行情報が登録されていません。", size=18, color=Colors.RED_700),
                Text(
                    "先に「銀行登録」画面で銀行口座情報を登録してください。",
                    size=14,
                    # 💡 文字色を黒に修正
                    color=Colors.BLACK,
                ),
            ],
            horizontal_alignment=CrossAxisAlignment.START,
        ),
        padding=20,
        border=border.all(1, Colors.RED_100),
        bgcolor=Colors.RED_50,
        width=500,
    )

    # 銀行リスト表示用のコントロールを生成
    bank_list_controls = Column(spacing=10)

    # 銀行ごとの編集ボタンを作成する関数 (グループ化されたボタン)
    def create_bank_group_button(
        bank_name: str, bank_code: str, asset_ids: list[int], account_numbers: list[str]
    ):
        # 💡 遷移先を銀行コードベースの新しいルートに変更
        # 例: /case/{case_id}/doc/balance_cert/bank_code/{bank_code}
        def go_to_edit_page(e):
            # 💡 銀行コードに基づいて遷移先のパスを決定
            if bank_code == "0001":
                # みずほ銀行専用ルート
                target_route = f"/case/{case_id}/doc/balance_cert/mizuho/{bank_code}"
            elif bank_code == "0009":
                # 三井住友銀行専用ルート
                target_route = f"/case/{case_id}/doc/balance_cert/smbc/{bank_code}"
            else:
                # 標準フォーム（現在の BankBalanceDocEditView を標準として流用）
                target_route = f"/case/{case_id}/doc/balance_cert/standard/{bank_code}"

            page.go(target_route)

        # 口座番号の表示を、複数の場合は「複数口座」などにする
        account_summary = (
            f"({len(asset_ids)}口座)" if len(asset_ids) > 1 else f"/ 口座番号: {account_numbers[0]}"
        )

        return Container(
            content=Row(
                [
                    Text(
                        # 💡 表示名を銀行名と口座数のサマリーに変更
                        f"🏦 {bank_name} {account_summary}",
                        size=14,
                        weight=FontWeight.W_500,
                        width=350,
                        color=Colors.BLACK,
                    ),
                    ElevatedButton(
                        "📄 申請書類を作成・編集",
                        icon=Icons.EDIT_DOCUMENT,
                        on_click=go_to_edit_page,
                        # # 💡 ButtonStyle を直接使用に修正
                        # style=ButtonStyle(
                        #     bgcolor=Colors.BLUE_500,
                        #     padding={"vertical": 15, "horizontal": 20},
                        #     shape={"borderRadius": 8},
                        # ),
                    ),
                ],
                alignment=MainAxisAlignment.START,
            ),
            padding=10,
            border=border.all(1, Colors.GREY_300),
            border_radius=5,
            bgcolor=Colors.WHITE,
            width=600,
        )

    if grouped_banks:
        # 💡 修正: グループ化された銀行データでボタンを生成
        for bank_code, bank_data in grouped_banks.items():
            bank_list_controls.controls.append(
                create_bank_group_button(
                    bank_data["bank_name"],
                    bank_code,
                    bank_data["asset_ids"],
                    bank_data["account_numbers"],
                )
            )
    else:
        # 銀行リストがない場合は、警告メッセージを表示
        bank_list_controls.controls.append(no_banks_content)

    # --- メインコンテンツの定義 ---
    return Column(
        controls=[
            # 💡 文字色を黒に修正 (App Barの背景色に合わせて)
            Text("📄 残証申請書類作成", size=24, weight=FontWeight.BOLD, color=Colors.WHITE),
            Divider(),
            Text(
                f"案件ID {case_id} に登録されている金融資産（銀行口座）を選択してください。",
                size=16,
                # 💡 文字色を黒に修正
                color=Colors.WHITE,
            ),
            Container(height=10),  # スペーサー
            bank_list_controls,  # 銀行ボタンリスト/警告メッセージ
        ],
        spacing=20,
        expand=True,
        horizontal_alignment=CrossAxisAlignment.START,
    )
