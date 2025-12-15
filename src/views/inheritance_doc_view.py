# src/views/inheritance_doc_view.py
from flet import (
    Colors,
    Column,
    Container,
    ControlEvent,
    Divider,
    ElevatedButton,
    FontWeight,
    Icon,
    Icons,
    ListTile,
    Page,
    RoundedRectangleBorder,
    SnackBar,
    Text,
)

from src.services.deceased_service import get_financial_asset_by_case
from src.services.pdf.pdf_factory import generate_pdf_for_bank
from src.utils.file_system import open_path


class InheritanceDocView(Column):
    """
    相続届・遺産分割協議書作成画面（各銀行の書類作成メニュー）
    """

    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, scroll="auto", spacing=20)
        self.page = page
        self.case_id = case_id

        # 銀行リストコンテナ
        self.bank_list_container = Column(spacing=10)

        self.controls = [
            Text(
                "📑 相続届・解約書類作成",
                size=24,
                weight=FontWeight.BOLD,
                color="onSurface",
            ),
            Divider(),
            Text("書類を作成する金融機関を選択してください。", size=16),
            self.bank_list_container,
        ]

    def did_mount(self):
        self._load_bank_list()

    def _load_bank_list(self):
        # 案件の資産から銀行リストを取得
        assets = get_financial_asset_by_case(self.case_id)

        # 重複排除
        unique_banks = {}
        for a in assets:
            if a.get("bank_code"):
                unique_banks[a["bank_code"]] = a.get("bank_name")

        self.bank_list_container.controls.clear()

        if unique_banks:
            for code, name in unique_banks.items():
                # 共通のデータ（クリックイベント用）
                bank_data = {"code": code, "name": name}

                self.bank_list_container.controls.append(
                    ListTile(
                        leading=Icon(Icons.DESCRIPTION, color="primary"),
                        title=Text(f"{name} (Code: {code})", weight=FontWeight.W_500),
                        subtitle=Text("相続届 / 解約依頼書"),
                        # 右側のボタン
                        trailing=ElevatedButton(
                            "作成",
                            icon=Icons.PICTURE_AS_PDF,
                            bgcolor="primaryContainer",
                            color="onPrimaryContainer",
                            data=bank_data,
                            on_click=self._on_create_pdf,
                        ),
                        bgcolor="surfaceVariant",
                        shape=RoundedRectangleBorder(radius=5),
                        data=bank_data,
                        on_click=self._on_create_pdf,
                    )
                )
        else:
            self.bank_list_container.controls.append(
                Container(Text("登録された金融機関がありません。", color=Colors.ERROR), padding=10)
            )
        self.page.update()

    def _on_create_pdf(self, e: ControlEvent):
        # ボタンクリック時は e.control は ElevatedButton
        # リストクリック時は e.control は ListTile
        bank_info = e.control.data
        if not bank_info:
            return

        try:
            # Factory経由でPDF作成を実行
            output_path = generate_pdf_for_bank(
                self.case_id, bank_code=bank_info["code"], bank_name=bank_info["name"]
            )

            self.page.open(SnackBar(Text(f"作成完了: {output_path}"), bgcolor=Colors.GREEN))
            open_path(self.page, output_path)

        except ValueError as ve:
            self.page.open(
                SnackBar(
                    Text(f"この銀行の書類フォーマットは未対応です: {ve}"), bgcolor=Colors.ORANGE
                )
            )
        except Exception as ex:
            self.page.open(SnackBar(Text(f"エラー: {ex}"), bgcolor=Colors.RED))

        self.page.update()
