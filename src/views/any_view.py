# src/views/any_view.py
from flet import (
    Colors,
    Column,
    Container,
    ControlEvent,
    ElevatedButton,
    FontWeight,
    Page,
    SnackBar,
    Text,
    padding,
)

from src.services.pdf.pdf_factory import generate_pdf_for_bank
from src.utils.file_system import open_path


class AnyView(Column):
    """
    任意の銀行の書類作成機能を確認するための汎用ビュー（デバッグ・テスト用）。
    実際の資産登録状況に関わらず、ボタンを表示してPDF生成をテストできます。
    """

    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, scroll="auto", spacing=20)
        self.page = page
        self.case_id = case_id

        # ボタンのリストを作成
        buttons_column = Column(controls=self.create_bank_buttons(), spacing=10)

        self.controls = [
            Container(
                content=Text("銀行書類作成テスト (AnyView)", size=24, weight=FontWeight.BOLD),
                padding=padding.all(10),
            ),
            Container(
                content=Text(
                    "※ ここでは案件の資産登録状況に関わらず、強制的にボタンを表示します。",
                    size=14,
                    color=Colors.GREY,
                ),
                padding=padding.only(left=10, bottom=10),
            ),
            # ボタンリストを配置
            Container(content=buttons_column, padding=padding.all(10)),
        ]

    def _on_click_create_pdf(self, e: ControlEvent):
        """
        PDF作成ボタンが押されたときの汎用処理
        ボタンの data 属性にセットされた銀行コードを使用する
        """
        # ボタンの data 属性から銀行情報を取得
        bank_info = e.control.data  # 例: {"code": "0039", "name": "auじぶん銀行"}

        if not bank_info:
            return

        try:
            self.page.open(
                SnackBar(Text(f"{bank_info['name']} の書類を作成中..."), bgcolor=Colors.BLUE)
            )
            self.page.update()

            # ファクトリーを呼び出し（銀行コードや名称を動的に渡す）
            output_path = generate_pdf_for_bank(
                self.case_id, bank_code=bank_info.get("code"), bank_name=bank_info.get("name")
            )

            self.page.open(SnackBar(Text(f"作成完了: {output_path}"), bgcolor=Colors.GREEN))
            open_path(self.page, output_path)

        except ValueError as ve:
            # 対応していない銀行の場合など
            self.page.open(SnackBar(Text(f"未対応の銀行です: {ve}"), bgcolor=Colors.ORANGE))
        except Exception as ex:
            import traceback

            traceback.print_exc()
            self.page.open(SnackBar(Text(f"エラーが発生しました: {ex}"), bgcolor=Colors.RED))

        self.page.update()

    def create_bank_buttons(self):
        """銀行ごとのボタンを生成する"""
        # テストしたい銀行をここに定義します
        assets = [
            {"code": "0039", "name": "auじぶん銀行"},
            {"code": "0001", "name": "みずほ銀行"},
            {"code": "0009", "name": "三井住友銀行"},
        ]

        button_controls = []
        for asset in assets:
            btn = ElevatedButton(
                text=f"{asset['name']} 書類作成",
                # data属性に銀行情報を埋め込む
                data=asset,
                on_click=self._on_click_create_pdf,
            )
            button_controls.append(btn)

        return button_controls
