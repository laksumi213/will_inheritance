# src/views/pdf_tool.py
from flet import (
    Colors,
    Column,
    Container,
    DataColumn,
    DataTable,
    ElevatedButton,
    Icons,
    MainAxisAlignment,
    Page,
    Row,
    SnackBar,
    Text,
    TextField,
    padding,
)

# 実際の操作は coordinate_view.py を使用するため、ここは管理用モックアップ
# または DB連携を行う場所


class PdfToolView(Column):
    """
    座標データ管理テーブル表示画面
    """

    def __init__(self, page: Page):
        super().__init__(expand=True, scroll="auto")
        self.page = page

        # 入力フィールド
        self.label_field = TextField(label="項目名 (例: 氏名)", width=200)
        self.x_field = TextField(label="X座標 (mm)", width=100, keyboard_type="number")
        self.y_field = TextField(label="Y座標 (mm)", width=100, keyboard_type="number")
        self.value_field = TextField(label="テスト値 (任意)", width=200)

        # データテーブル
        self.data_table = DataTable(
            columns=[
                DataColumn(Text("ID")),
                DataColumn(Text("項目名")),
                DataColumn(Text("X座標")),
                DataColumn(Text("Y座標")),
                DataColumn(Text("値")),
                DataColumn(Text("操作")),
            ],
            rows=[],
        )

        self.controls = [
            Container(
                content=Text("PDF座標設定管理", size=24, weight="bold"), padding=padding.all(10)
            ),
            Container(
                content=Row(
                    controls=[
                        self.label_field,
                        self.x_field,
                        self.y_field,
                        self.value_field,
                        ElevatedButton(
                            "追加",
                            icon=Icons.ADD,
                            on_click=self._add_coordinate,
                            bgcolor=Colors.BLUE_600,
                            color=Colors.WHITE,
                        ),
                    ],
                    alignment=MainAxisAlignment.START,
                ),
                padding=padding.all(10),
                bgcolor=Colors.BLUE_GREY_50,
                border_radius=8,
            ),
            Container(height=20),
            Text("登録済み座標一覧", size=18, weight="bold"),
            self.data_table,
        ]

    def _add_coordinate(self, e):
        self.page.open(SnackBar(Text("デモ: 座標を追加しました"), bgcolor=Colors.GREEN))
        self.page.update()
