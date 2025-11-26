# /components/pages/visit_reserve_select_bank_view.py

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

from services.deceased_service import get_financial_asset_by_case


class VisitReserveSelectBankView(Column):
    """
    来店予約を行うための銀行を選択するビュー。
    案件に登録されている銀行資産の一覧を表示する。
    (balance_cert_doc.py と同じUIスタイル)
    """

    def __init__(self, page: Page, case_id: int):
        super().__init__(
            expand=True,
            scroll="auto",
            spacing=20,
            horizontal_alignment=CrossAxisAlignment.START,
        )
        self.page = page
        self.case_id = case_id

        # --- サービス層から金融資産リストを取得 ---
        financial_assets = get_financial_asset_by_case(case_id)

        # 💡 銀行コードごとに口座情報をグループ化 (balance_cert_doc.pyと同じロジック)
        grouped_banks = {}
        for asset in financial_assets:
            bank_code = asset.get("bank_code")
            bank_name = asset.get("bank_name")
            account_number = asset.get("account_number")

            if bank_code and bank_name:
                if bank_code not in grouped_banks:
                    grouped_banks[bank_code] = {
                        "bank_name": bank_name,
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

        # 銀行ごとの予約ボタンを作成する関数
        def create_bank_group_button(
            bank_name: str, bank_code: str, asset_ids: list[int], account_numbers: list[str]
        ):
            def go_to_reserve_page(e):
                # 銀行コードに基づいて遷移先のパスを決定
                if bank_code == "0001":
                    # みずほ銀行専用ルート
                    self.page.go(f"/case/{self.case_id}/reserve/mizuho")
                elif bank_code == "0009":
                    # 三井住友銀行専用ルート (仮)
                    self.page.go(f"/case/{self.case_id}/reserve/smbc")
                else:
                    # 標準フォーム
                    self.page.go(f"/case/{self.case_id}/reserve/standard/{bank_code}")

            # 口座番号のサマリー表示
            account_summary = (
                f"({len(asset_ids)}口座)"
                if len(asset_ids) > 1
                else f"/ 口座番号: {account_numbers[0]}"
            )

            return Container(
                content=Row(
                    [
                        Text(
                            f"🏦 {bank_name} {account_summary}",
                            size=14,
                            weight=FontWeight.W_500,
                            width=350,
                            color=Colors.BLACK,
                        ),
                        ElevatedButton(
                            "来店予約へ進む",
                            icon=Icons.CALENDAR_MONTH,
                            on_click=go_to_reserve_page,
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
            bank_list_controls.controls.append(no_banks_content)

        # --- メインコンテンツの定義 ---
        self.controls = [
            Text("📅 来店予約 - 銀行選択", size=24, weight=FontWeight.BOLD, color=Colors.WHITE),
            Divider(),
            Text(
                "来店予約を行う金融機関を、案件に登録されているリストから選択してください。",
                size=16,
                color=Colors.WHITE,
            ),
            Container(height=10),  # スペーサー
            bank_list_controls,  # 銀行ボタンリスト/警告メッセージ
        ]
