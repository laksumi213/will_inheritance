# /components/pages/freeze_proc_view.py

from flet import (
    ButtonStyle,
    Colors,
    Column,
    Container,
    CrossAxisAlignment,  # 💡 追加
    Divider,
    ElevatedButton,
    FontWeight,
    Icon,
    Icons,
    MainAxisAlignment,  # 💡 追加
    Page,
    Row,  # 💡 追加
    Text,
    border,
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
            horizontal_alignment=CrossAxisAlignment.START,  # 💡 全体を左寄せ
        )
        self.page = page
        self.case_id = case_id

        self.controls = [
            Text(
                "🔒 口座凍結のご連絡",
                size=24,
                weight=FontWeight.BOLD,
                color=Colors.WHITE,
            ),
            Divider(),
            Text(
                "死亡の連絡（口座凍結）を行う金融機関を選択してください。\n※複数の支店・口座がある場合でも、金融機関ごとにまとめて表示しています。",
                size=16,
                color=Colors.WHITE,
            ),
            # リスト生成関数を呼び出し (Containerでラップせず直接Columnに追加)
            self._create_institution_list_controls(),
        ]

    def _create_institution_list_controls(self):
        """登録済みの金融機関リスト（重複排除済み）を生成する"""

        # 1. 案件の全金融資産リストを取得 (銀行・証券含む)
        assets = get_financial_asset_by_case(self.case_id)

        # 2. 金融機関コードをキーにしてユニークなリストを作成
        unique_institutions = {}

        for asset in assets:
            code = asset.get("bank_code")
            name = asset.get("bank_name")

            if code and code not in unique_institutions:
                unique_institutions[code] = name

        # 資産が一つもない場合
        if not unique_institutions:
            return Container(
                content=Text(
                    "現在、この案件に登録されている金融資産情報がありません。\n先に「銀行登録」または「証券登録」を行ってください。",
                    color=Colors.RED_700,
                ),
                padding=20,
                bgcolor=Colors.WHITE,
                border_radius=5,
                width=600,  # 幅を制限
            )

        # 銀行ごとのコントロールリストを作成
        bank_controls = Column(spacing=10)

        for code, name in unique_institutions.items():
            # ボタンを押した先の処理
            def go_to_freeze_detail(e, code=code, name=name):
                self.page.go(f"/case/{self.case_id}/proc/freeze/{code}")

            # 💡 銀行ごとのカードを作成
            bank_card = Container(
                content=Row(
                    controls=[
                        # アイコンと銀行名・コード
                        Row(
                            controls=[
                                Icon(Icons.ACCOUNT_BALANCE_WALLET, color=Colors.BLUE_GREY_700),
                                Column(
                                    controls=[
                                        Text(
                                            f"{name}",
                                            weight=FontWeight.W_600,
                                            size=16,
                                            color=Colors.BLACK,  # 💡 黒に指定
                                        ),
                                        Text(
                                            f"金融機関コード: {code}",
                                            size=12,
                                            color=Colors.BLACK,  # 💡 黒に指定 (グレー回避)
                                        ),
                                    ],
                                    spacing=2,
                                    alignment=MainAxisAlignment.CENTER,
                                ),
                            ],
                            spacing=15,
                        ),
                        # ボタン
                        ElevatedButton(
                            "凍結連絡へ",
                            icon=Icons.PHONE_CALLBACK,
                            style=ButtonStyle(
                                bgcolor=Colors.RED_600,
                                color=Colors.WHITE,
                            ),
                            on_click=go_to_freeze_detail,
                            data=code,
                        ),
                    ],
                    alignment=MainAxisAlignment.SPACE_BETWEEN,  # 左右に配置
                    vertical_alignment=CrossAxisAlignment.CENTER,
                ),
                width=600,  # 💡 幅を固定して右いっぱいになるのを防ぐ
                padding=15,
                border=border.all(1, Colors.GREY_300),  # 💡 枠線
                border_radius=5,
                bgcolor=Colors.WHITE,
            )

            bank_controls.controls.append(bank_card)

        return bank_controls
