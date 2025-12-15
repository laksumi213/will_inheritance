# src/views/inheritance_division_view.py
import datetime
import os
import platform

from flet import (
    Card,
    Colors,
    Column,
    Container,
    Divider,
    Dropdown,
    ElevatedButton,
    FontWeight,
    Icon,
    Icons,
    ListTile,
    Page,
    Row,
    SnackBar,
    Text,
    dropdown,
)

from src.config import settings
from src.services.deceased_service import (
    get_case_by_id,  # 💡 追加: 案件番号取得用
    get_case_folder_path,
    get_deceased_by_case_id,
    get_financial_asset_by_case,
)
from src.services.doc_generator import generate_division_agreement_doc
from src.utils.file_system import open_path


class InheritanceDivisionView(Column):
    """
    遺産分割協議書 作成・指定画面
    """

    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, scroll="auto", spacing=20)
        self.page = page
        self.case_id = case_id

        # 1. データのロード
        self.deceased = get_deceased_by_case_id(case_id)
        self.financial_assets = get_financial_asset_by_case(case_id)

        try:
            from src.services.real_estate_service import get_real_estates_by_case

            self.real_estates = get_real_estates_by_case(case_id)
        except ImportError:
            self.real_estates = []

        # 2. 状態管理用辞書 (AssetKey -> HeirID)
        self.allocations = {}

        # 3. 相続人選択肢の作成
        self.heir_options = []
        if self.deceased and self.deceased.heirs:
            for h in self.deceased.heirs:
                self.heir_options.append(
                    dropdown.Option(key=str(h.id), text=f"{h.name_last} {h.name_first}")
                )

        # 4. UI構築
        self.controls = [
            Text(
                "🤝 遺産分割協議書の作成",
                size=24,
                weight=FontWeight.BOLD,
                color="onSurface",
            ),
            Divider(),
            # 相続人確認
            Card(
                content=Container(
                    content=Column(
                        [
                            Row(
                                [
                                    Icon(Icons.PEOPLE),
                                    Text("対象となる相続人", weight=FontWeight.BOLD),
                                ]
                            ),
                            self._create_heir_list_text(),
                        ],
                        spacing=10,
                    ),
                    padding=15,
                )
            ),
            Text("財産の分割指定", size=18, weight=FontWeight.BOLD),
            Text("各財産を取得する相続人を選択してください。", size=14, color=Colors.GREY),
            self._create_asset_allocation_list(),
            Divider(),
            # アクションボタン
            Row(
                [
                    ElevatedButton(
                        "遺産分割協議書を出力 (Word)",
                        icon=Icons.DESCRIPTION,
                        bgcolor=Colors.INDIGO_600,
                        color=Colors.WHITE,
                        on_click=self._on_generate_click,
                    ),
                ],
                spacing=20,
            ),
        ]

    def _create_heir_list_text(self):
        if not self.deceased or not self.deceased.heirs:
            return Text("相続人が登録されていません", color=Colors.RED)
        names = [f"{h.name_last} {h.name_first}" for h in self.deceased.heirs]
        return Text("、".join(names), size=16)

    def _on_allocation_change(self, e, asset_key):
        """ドロップダウン変更時のハンドラ"""
        selected_heir_id = int(e.control.value)
        self.allocations[asset_key] = selected_heir_id

    def _create_asset_allocation_list(self):
        items = Column(spacing=10)

        # -- 金融資産 --
        if self.financial_assets:
            items.controls.append(
                Text("【金融資産】", weight=FontWeight.BOLD, color=Colors.BLUE_GREY)
            )
            for asset in self.financial_assets:
                asset_key = f"BANK_{asset['id']}"

                dd = Dropdown(
                    width=200,
                    label="取得者を選択",
                    options=self.heir_options,
                    on_change=lambda e, k=asset_key: self._on_allocation_change(e, k),
                    dense=True,
                )

                items.controls.append(
                    Card(
                        content=ListTile(
                            leading=Icon(Icons.ACCOUNT_BALANCE_WALLET, color=Colors.BLUE),
                            title=Text(f"{asset['bank_name']} {asset['branch_name']}"),
                            subtitle=Text(f"{asset['account_type']} : {asset['account_number']}"),
                            trailing=dd,
                        )
                    )
                )

        # -- 不動産 --
        if self.real_estates:
            items.controls.append(
                Text("【不動産】", weight=FontWeight.BOLD, color=Colors.BLUE_GREY)
            )
            for re in self.real_estates:
                asset_key = f"RE_{re.id}"

                dd = Dropdown(
                    width=200,
                    label="取得者を選択",
                    options=self.heir_options,
                    on_change=lambda e, k=asset_key: self._on_allocation_change(e, k),
                    dense=True,
                )

                # 画像有無アイコン
                has_pdf = re.registry_image_path and os.path.exists(re.registry_image_path)
                icon = Icons.IMAGE if has_pdf else Icons.IMAGE_NOT_SUPPORTED
                icon_col = Colors.GREEN if has_pdf else Colors.GREY

                items.controls.append(
                    Card(
                        content=ListTile(
                            leading=Icon(Icons.HOME, color=Colors.ORANGE),
                            title=Text(f"{re.location}"),
                            subtitle=Row(
                                [
                                    Icon(icon, size=16, color=icon_col),
                                    Text(
                                        f"{re.property_type} (画像: {'あり' if has_pdf else 'なし'})"
                                    ),
                                ]
                            ),
                            trailing=dd,
                        )
                    )
                )

        if not items.controls:
            return Container(
                content=Text("分割対象となる財産が登録されていません。", color=Colors.RED),
                padding=20,
            )

        return items

    def _on_generate_click(self, e):
        """作成ボタンクリック時"""
        self.page.open(SnackBar(Text("Wordファイルを生成しています..."), bgcolor=Colors.BLUE))
        self.page.update()

        try:
            # 1. 保存先フォルダの決定 (OS分岐)
            if platform.system() == "Darwin":  # macOSの場合
                folder_path = os.path.join(settings.BASE_DIR, "output")
                os.makedirs(folder_path, exist_ok=True)
                print(f"macOS detected: Saving to {folder_path}")
            else:
                # Windows (その他) の場合: DBの案件パスを使用
                folder_path = get_case_folder_path(self.case_id)
                if not folder_path:
                    folder_path = os.getcwd()  # フォールバック

            # 2. ファイル名生成ロジック変更
            # {案件番号}{被相続人氏名}様_遺産分割協議書_{今日の日付}
            case = get_case_by_id(self.case_id)
            case_num = case.case_number if case else str(self.case_id)
            d_name = (
                f"{self.deceased.name_last}{self.deceased.name_first}"
                if self.deceased
                else "未登録"
            )
            today_str = datetime.datetime.now().strftime("%Y%m%d")

            filename = f"{case_num}{d_name}様_遺産分割協議書_{today_str}.docx"
            output_path = os.path.join(folder_path, filename)

            # 3. 生成実行
            saved_path = generate_division_agreement_doc(
                self.case_id, self.allocations, output_path
            )

            self.page.open(
                SnackBar(
                    content=Text(f"作成完了: {os.path.basename(saved_path)}"),
                    action="フォルダを開く",
                    on_action=lambda _: self._open_folder(folder_path),
                    bgcolor=Colors.GREEN,
                )
            )

            # 自動的に開く
            open_path(self.page, saved_path)

        except Exception as ex:
            import traceback

            traceback.print_exc()
            self.page.open(SnackBar(Text(f"エラーが発生しました: {ex}"), bgcolor=Colors.RED))

        self.page.update()

    def _open_folder(self, path):
        from src.utils.file_system import open_path

        open_path(self.page, path)
