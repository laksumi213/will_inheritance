# /components/pages/balance_cert_doc.py
from flet import (
    # 💡 ButtonStyleをインポート
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
    案件に紐づく FinancialAsset (銀行) リストを表示し、銀行ごとの詳細編集画面へ遷移させる。
    """

    # --- サービス層から銀行リスト (FinancialAssetリスト) を取得 ---
    # 💡 既存の get_financial_asset_by_case を呼び出す
    financial_assets = get_financial_asset_by_case(case_id)

    # 案件に銀行が登録されていない場合のコントロール
    no_banks_content = Container(
        content=Column(
            [
                Text("⚠️ 銀行情報が登録されていません。", size=18, color=Colors.RED_700),
                Text(
                    "先に「銀行登録」画面で銀行口座情報を登録してください。",
                    size=14,
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

    # 銀行ごとの編集ボタンを作成する関数
    # 💡 asset_id を bank_id として使用
    def create_bank_button(bank_name: str, branch_name: str, account_number: str, asset_id: int):
        # 💡 銀行ごとの残証申請書類編集画面への遷移関数
        # ルート例: /case/{case_id}/doc/balance_cert/{asset_id}
        def go_to_edit_page(e):
            page.go(f"/case/{case_id}/doc/balance_cert/{asset_id}")

        # 支店名がない場合は金融機関名のみを表示
        is_branch_info = branch_name and branch_name != "支店不明" and branch_name.strip()
        display_name = f"{bank_name} ({branch_name})" if is_branch_info else bank_name

        return Container(
            content=Row(
                [
                    Text(
                        f"{display_name} / 口座番号: {account_number}",
                        size=14,
                        weight=FontWeight.W_500,
                        width=350,
                        color=Colors.BLACK,
                    ),
                    ElevatedButton(
                        "📄 申請書類を作成・編集",
                        icon=Icons.EDIT_DOCUMENT,
                        on_click=go_to_edit_page,
                        # 💡 修正箇所: ButtonStyle を直接使用
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

    if financial_assets:
        # 銀行リストが存在する場合、ボタンを生成
        for asset in financial_assets:
            # asset は get_financial_asset_by_case の辞書形式
            bank_list_controls.controls.append(
                create_bank_button(
                    asset["bank_name"],
                    asset.get("branch_name") or "支店不明",
                    asset["account_number"],
                    asset["id"],  # asset_id
                )
            )
    else:
        # 銀行リストがない場合は、警告メッセージを表示
        bank_list_controls.controls.append(no_banks_content)

    # --- メインコンテンツの定義 ---
    return Column(
        controls=[
            Text("📄 残証申請書類作成", size=24, weight=FontWeight.BOLD, color=Colors.WHITE),
            Divider(),
            Text(
                f"案件ID {case_id} に登録されている金融資産（銀行口座）を選択してください。",
                size=16,
                color=Colors.WHITE,
            ),
            Container(height=10),  # スペーサー
            bank_list_controls,  # 銀行ボタンリスト/警告メッセージ
        ],
        spacing=20,
        expand=True,
        horizontal_alignment=CrossAxisAlignment.START,
    )
