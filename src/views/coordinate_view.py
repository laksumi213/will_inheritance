# views/coordinate_view.py
import os

from flet import (
    Card,
    Colors,
    Column,
    Container,
    ControlEvent,
    DataCell,
    DataColumn,
    DataRow,
    DataTable,
    ElevatedButton,
    IconButton,
    Icons,
    Page,
    Row,
    SnackBar,
    Text,
    TextField,
    UserControl,
    padding,
)

from services.pdf_service import PdfService


class CoordinateView(UserControl):
    """
    座標登録・管理およびPDF生成を行うメイン画面
    """

    def __init__(self, page: Page):
        super().__init__()
        self.page = page
        self.service = PdfService()

        # 入力フィールド
        self.label_field = TextField(label="項目名 (例: 氏名)", width=200)
        self.x_field = TextField(label="X座標", width=100, keyboard_type="NUMBER")
        self.y_field = TextField(label="Y座標", width=100, keyboard_type="NUMBER")
        self.val_field = TextField(label="テスト値", width=150)

        # データテーブル
        self.data_table = DataTable(
            columns=[
                DataColumn(Text("ID")),
                DataColumn(Text("項目名")),
                DataColumn(Text("X")),
                DataColumn(Text("Y")),
                DataColumn(Text("値")),
                DataColumn(Text("操作")),
            ],
            border=import_border(Colors.OUTLINE),
            vertical_lines=import_border(Colors.OUTLINE_VARIANT),
            heading_row_color=Colors.SURFACE_VARIANT,
        )

    def did_mount(self):
        """画面表示時にデータをロード"""
        self.load_data()

    def load_data(self):
        """DBからデータを読み込みテーブルを更新"""
        try:
            coordinates = self.service.get_all_coordinates()
            self.data_table.rows.clear()

            for coord in coordinates:
                self.data_table.rows.append(
                    DataRow(
                        cells=[
                            DataCell(Text(str(coord.id))),
                            DataCell(Text(coord.label)),
                            DataCell(Text(str(coord.x_point))),
                            DataCell(Text(str(coord.y_point))),
                            DataCell(Text(coord.value if coord.value else "-")),
                            DataCell(
                                IconButton(
                                    icon=Icons.DELETE,
                                    icon_color=Colors.ERROR,
                                    data=coord.id,
                                    on_click=self.delete_clicked,
                                )
                            ),
                        ]
                    )
                )
            self.update()
        except Exception as e:
            self.show_snack_bar(f"データ読み込みエラー: {e}", is_error=True)

    def add_clicked(self, e: ControlEvent) -> None:
        """追加ボタンクリック時の処理"""
        if not all([self.label_field.value, self.x_field.value, self.y_field.value]):
            self.show_snack_bar("項目名、X座標、Y座標は必須です", is_error=True)
            return

        try:
            x_val = float(self.x_field.value)
            y_val = float(self.y_field.value)

            self.service.add_coordinate(
                label=self.label_field.value, x=x_val, y=y_val, value=self.val_field.value
            )

            # 入力クリア
            self.label_field.value = ""
            self.x_field.value = ""
            self.y_field.value = ""
            self.val_field.value = ""

            self.show_snack_bar("座標データを保存しました", is_error=False)
            self.load_data()

        except ValueError:
            self.show_snack_bar("座標には数値を入力してください", is_error=True)
        except Exception as ex:
            self.show_snack_bar(f"保存エラー: {ex}", is_error=True)

    def delete_clicked(self, e: ControlEvent) -> None:
        """削除ボタンクリック時の処理"""
        try:
            coord_id = e.control.data
            self.service.delete_coordinate(coord_id)
            self.show_snack_bar("データを削除しました", is_error=False)
            self.load_data()
        except Exception as ex:
            self.show_snack_bar(f"削除エラー: {ex}", is_error=True)

    def generate_clicked(self, e: ControlEvent) -> None:
        """PDF生成ボタンクリック時の処理"""
        try:
            # outputフォルダの確保
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "preview.pdf")

            generated_path = self.service.generate_preview_pdf(output_path)
            self.show_snack_bar(f"PDFを出力しました: {generated_path}", is_error=False)
        except Exception as ex:
            self.show_snack_bar(f"PDF生成エラー: {ex}", is_error=True)

    def show_snack_bar(self, message: str, is_error: bool = False) -> None:
        """スナックバーによる通知"""
        color = Colors.ERROR if is_error else Colors.GREEN
        self.page.open(SnackBar(content=Text(message, color=Colors.WHITE), bgcolor=color))

    def build(self):
        """UI構築"""
        input_form = Card(
            content=Container(
                content=Row(
                    controls=[
                        self.label_field,
                        self.x_field,
                        self.y_field,
                        self.val_field,
                        ElevatedButton(
                            text="追加",
                            icon=Icons.ADD,
                            on_click=self.add_clicked,
                            bgcolor=Colors.PRIMARY,
                            color=Colors.ON_PRIMARY,
                        ),
                    ],
                    alignment="center",
                ),
                padding=padding.all(20),
            )
        )

        return Column(
            controls=[
                Text("座標定義ツール", size=24, weight="bold", color=Colors.ON_SURFACE),
                input_form,
                Container(height=20),  # Spacer
                Row(
                    controls=[
                        ElevatedButton(
                            text="PDFプレビュー生成",
                            icon=Icons.PICTURE_AS_PDF,
                            on_click=self.generate_clicked,
                            bgcolor=Colors.SECONDARY,
                            color=Colors.ON_SECONDARY,
                        )
                    ],
                    alignment="end",
                ),
                Text("登録済み座標一覧", size=18, weight="bold", color=Colors.ON_SURFACE),
                self.data_table,
            ],
            scroll="auto",
            expand=True,
            spacing=10,
        )


# Borderのヘルパー (Fletのバージョンによってはborder.allなどが使えるが、安全のためimport不要な記述で対応)
def import_border(color):
    from flet import border

    return border.all(1, color)
