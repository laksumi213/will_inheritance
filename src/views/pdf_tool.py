# src/views/pdf_tool.py
from flet import (
    Colors,
    Column,
    Container,
    DataCell,
    DataColumn,
    DataRow,
    DataTable,
    ElevatedButton,
    IconButton,
    Icons,
    MainAxisAlignment,
    Page,
    Row,
    SnackBar,
    Text,
    TextField,
    padding,
)

from src.services.pdf_service import pdf_service
from src.utils.file_system import open_path


class PdfToolView(Column):
    """
    PDF座標管理およびプレビュー生成ツール画面
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

        # 画面構成
        self.controls = [
            Container(
                content=Text("PDF座標設定ツール", size=24, weight="bold"), padding=padding.all(10)
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
            Container(height=20),
            Row(
                controls=[
                    ElevatedButton(
                        "プレビューPDF生成",
                        icon=Icons.PICTURE_AS_PDF,
                        bgcolor=Colors.GREEN_600,
                        color=Colors.WHITE,
                        on_click=self._generate_pdf,
                    )
                ]
            ),
        ]

    def did_mount(self):
        """画面表示時にデータをロード"""
        self._load_data()

    def _load_data(self):
        """DBから座標データを読み込んでテーブルを更新"""
        try:
            coords = pdf_service.get_all_coordinates()
            self.data_table.rows.clear()

            for c in coords:
                self.data_table.rows.append(
                    DataRow(
                        cells=[
                            DataCell(Text(str(c.id))),
                            DataCell(Text(c.label)),
                            DataCell(Text(str(c.x_point))),
                            DataCell(Text(str(c.y_point))),
                            DataCell(Text(c.value or "")),
                            DataCell(
                                IconButton(
                                    icon=Icons.DELETE,
                                    icon_color=Colors.RED,
                                    on_click=lambda e, cid=c.id: self._delete_coordinate(cid),
                                )
                            ),
                        ]
                    )
                )
            self.update()

        except Exception as e:
            self._show_error(f"データ読み込みエラー: {e}")

    def _add_coordinate(self, e):
        """座標を追加"""
        try:
            label = self.label_field.value
            x_val = float(self.x_field.value)
            y_val = float(self.y_field.value)
            val = self.value_field.value

            if not label:
                raise ValueError("項目名は必須です")

            pdf_service.add_coordinate(label, x_val, y_val, val)

            # 入力クリア
            self.label_field.value = ""
            self.x_field.value = ""
            self.y_field.value = ""
            self.value_field.value = ""

            self._load_data()
            self._show_success("座標を追加しました")

        except ValueError:
            self._show_error("X, Y座標には数値を入力してください")
        except Exception as ex:
            self._show_error(f"追加エラー: {ex}")

    def _delete_coordinate(self, coord_id: int):
        """座標を削除"""
        try:
            pdf_service.delete_coordinate(coord_id)
            self._load_data()
            self._show_success("削除しました")
        except Exception as e:
            self._show_error(f"削除エラー: {e}")

    def _generate_pdf(self, e):
        """PDFを生成して開く"""
        try:
            path = pdf_service.generate_preview_pdf()
            self._show_success(f"PDF生成完了: {path}")

            # フォルダを開く
            import os

            folder = os.path.dirname(path)
            open_path(self.page, folder)

        except Exception as ex:
            self._show_error(f"PDF生成エラー: {ex}")

    def _show_error(self, msg: str):
        self.page.open(
            SnackBar(
                content=Text(msg, color=Colors.WHITE),
                bgcolor=Colors.RED,
            )
        )
        self.page.update()

    def _show_success(self, msg: str):
        self.page.open(
            SnackBar(
                content=Text(msg, color=Colors.WHITE),
                bgcolor=Colors.GREEN,
            )
        )
        self.page.update()
