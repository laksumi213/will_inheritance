# src/views/editors.py
from flet import (
    AppBar,
    Colors,
    Column,
    Container,
    ElevatedButton,
    Icons,
    Page,
    SnackBar,
    Text,
    TextField,
    View,
    padding,
)


class DeceasedEditView(View):
    """被相続人情報の編集画面"""

    def __init__(self, page: Page, deceased_id: int):
        super().__init__(route=f"/deceased_edit/{deceased_id}")
        self.page = page
        self.deceased_id = deceased_id

        self.appbar = AppBar(
            title=Text(f"被相続人編集 (ID: {deceased_id})"),
            bgcolor=Colors.TEAL_500,
            color=Colors.WHITE,
        )

        self.name_field = TextField(label="氏名", value="山田 太郎")
        self.date_field = TextField(label="死亡日", hint_text="YYYY-MM-DD")

        self.controls = [
            Container(
                content=Column(
                    [
                        self.name_field,
                        self.date_field,
                        ElevatedButton(
                            "保存",
                            icon=Icons.SAVE,
                            on_click=self.save_data,
                            bgcolor=Colors.BLUE_500,
                            color=Colors.WHITE,
                        ),
                    ],
                    spacing=20,
                ),
                padding=padding.all(20),
            )
        ]

    def save_data(self, e):
        """データの保存処理と画面遷移"""
        # TODO: DB保存処理

        # 💡 修正箇所: page.open(SnackBar(...)) に変更
        self.page.open(SnackBar(Text("保存しました"), bgcolor=Colors.GREEN))

        self.page.update()
        self.page.views.pop()  # 前の画面に戻る
        self.page.go(self.page.views[-1].route)  # 画面更新のためにリロード


class HeirEditView(View):
    """相続人情報の編集・追加画面"""

    def __init__(self, page: Page, heir_id: int, deceased_id: int):
        route_path = f"/heir_edit/{heir_id}" if heir_id else "/heir_edit/new"
        super().__init__(route=route_path)

        self.page = page
        self.heir_id = heir_id
        self.deceased_id = deceased_id

        title_text = "新規相続人登録" if heir_id == 0 else f"相続人編集 (ID: {heir_id})"

        self.appbar = AppBar(title=Text(title_text), bgcolor=Colors.ORANGE_500, color=Colors.WHITE)

        self.name_field = TextField(label="相続人氏名")
        self.relation_field = TextField(label="続柄", hint_text="例: 長男")

        self.controls = [
            Container(
                content=Column(
                    [
                        Text(f"対象被相続人ID: {deceased_id}", color=Colors.GREY),
                        self.name_field,
                        self.relation_field,
                        ElevatedButton(
                            "保存",
                            icon=Icons.SAVE,
                            on_click=self.save_data,
                            bgcolor=Colors.BLUE_500,
                            color=Colors.WHITE,
                        ),
                    ],
                    spacing=20,
                ),
                padding=padding.all(20),
            )
        ]

    def save_data(self, e):
        """データの保存処理と画面遷移"""
        # TODO: DB保存処理

        # 💡 修正箇所: page.open(SnackBar(...)) に変更
        self.page.open(SnackBar(Text("保存しました"), bgcolor=Colors.GREEN))

        self.page.update()
        self.page.views.pop()
        self.page.go(self.page.views[-1].route)
