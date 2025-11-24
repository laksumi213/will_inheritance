# /components/pages/freeze_proc_view.py

from flet import (
    ButtonStyle,
    Colors,
    Column,
    Container,
    Divider,
    ElevatedButton,
    FontWeight,
    Icon,
    Icons,
    ListTile,
    ListView,
    Page,
    Text,
)

from services.deceased_service import get_financial_asset_by_case


class FreezeProcView(Column):
    """
    口座凍結の連絡を行うための金融機関を選択するビュー。
    案件に登録されている資産から、金融機関ごとにまとめて表示する。
    """

    def __init__(self, page: Page, case_id: int):
        super().__init__(
            expand=True,
            scroll="auto",
            spacing=20,
        )
        self.page = page
        self.case_id = case_id

        self.controls = [
            Text(
                "🔒 口座凍結のご連絡",
                size=24,
                weight=FontWeight.BOLD,
            ),
            Divider(),
            Text(
                "死亡の連絡（口座凍結）を行う金融機関を選択してください。\n※複数の支店・口座がある場合でも、金融機関ごとにまとめて表示しています。",
                size=16,
                color=Colors.BLACK87,
            ),
            Container(
                content=self._create_institution_list_controls(),
                padding=10,
                border_radius=10,
                bgcolor=Colors.WHITE,
            ),
        ]

    def _create_institution_list_controls(self):
        """登録済みの金融機関リスト（重複排除済み）を生成する"""

        # 1. 案件の全金融資産リストを取得 (銀行・証券含む)
        assets = get_financial_asset_by_case(self.case_id)

        # 2. 金融機関コードをキーにしてユニークなリストを作成
        #    { "0001": "みずほ銀行", "0143": "SBI証券", ... }
        unique_institutions = {}

        for asset in assets:
            # BankMaster経由で取得した名称とコード
            code = asset.get("bank_code")
            name = asset.get("bank_name")

            # コードが存在し、まだリストになければ追加
            if code and code not in unique_institutions:
                unique_institutions[code] = name

        # 資産が一つもない場合
        if not unique_institutions:
            return ListView(
                controls=[
                    Container(
                        content=Text(
                            "現在、この案件に登録されている金融資産情報がありません。\n先に「銀行登録」または「証券登録」を行ってください。",
                            color=Colors.RED_700,
                        ),
                        padding=20,
                    )
                ]
            )

        controls = []
        for code, name in unique_institutions.items():
            # ボタンを押した先の処理（現在はプレースホルダーへ遷移）
            def go_to_freeze_detail(e, code=code, name=name):
                # 例: /case/1/proc/freeze/0001
                self.page.go(f"/case/{self.case_id}/proc/freeze/{code}")

            controls.append(
                ListTile(
                    leading=Icon(Icons.ACCOUNT_BALANCE_WALLET, color=Colors.BLUE_GREY),
                    title=Text(f"{name}", weight=FontWeight.W_600, color=Colors.BLACK),
                    subtitle=Text(f"金融機関コード: {code}"),
                    trailing=ElevatedButton(
                        "凍結連絡へ",
                        icon=Icons.PHONE_CALLBACK,
                        style=ButtonStyle(
                            bgcolor=Colors.RED_600,  # 凍結＝重要/停止アクションなので赤系
                            color=Colors.WHITE,
                        ),
                        on_click=go_to_freeze_detail,
                        data=code,
                    ),
                    on_click=go_to_freeze_detail,
                )
            )

        return ListView(controls=controls, spacing=5)
