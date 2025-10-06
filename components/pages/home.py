# /components/pages/home.py

from flet import (
    AppBar,
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    DataCell,
    DataColumn,
    DataRow,
    DataTable,
    Divider,
    FontWeight,
    GestureDetector,
    IconButton,
    Icons,
    Page,
    Row,
    ScrollMode,
    SnackBar,
    Text,
    TextStyle,
    View,
    border,
)

# from components.common.custom_text import CustomText
from components.common.custom_elevatedbutton import CustomElevatedButton
from components.common.custom_textfield import CustomTextField
from services import deceased_service  # サービス層からデータ操作関数をインポート


# 被相続人一覧表示（メイン）ビュー
def DeceasedListView(page: Page):
    # UI要素の定義
    # deceased_list_container = Column()
    # データを表示するためのDataTableを定義
    deceased_data_table = DataTable(  # ★ 追加: DataTableコントロールを定義
        columns=[
            DataColumn(Text("ID")),
            DataColumn(Text("名前")),
            DataColumn(Text("生年月日")),
            DataColumn(Text("アクション")),  # 詳細/削除ボタン用
        ],
        rows=[],  # データは後で追加
        data_text_style=TextStyle(color=Colors.BLACK),
        heading_text_style=TextStyle(color=Colors.WHITE),
        heading_row_color=Colors.BLUE_GREY_300,
        bgcolor=Colors.WHITE,
        border=border.all(1, Colors.BLACK12),
        # heading_row_color=Colors.BLUE_GREY_100,
        # data_row_max_height=40,
        horizontal_lines=border.BorderSide(1, Colors.BLACK12),
        vertical_lines=border.BorderSide(1, Colors.BLACK12),
    )

    new_deceased_name_field = CustomTextField(label="新しい被相続人名", width=250)
    new_deceased_dob_field = CustomTextField(label="生年月日(YYYY-MM-DD)", width=250)

    # ★ コピー処理と通知を行う共通関数
    def copy_to_clipboard_and_notify(e):
        # クリックされたGestureDetector (e.control) の中にあるTextコントロールを取得
        # e.control.content が Text コントロールです
        clicked_text_control: Text = e.control.content

        # Textコントロールの値を取得
        text_to_copy = clicked_text_control.value

        # クリップボードにコピー
        page.set_clipboard(text_to_copy)

        page.open(
            SnackBar(Text(f"'{text_to_copy}' をクリップボードにコピーしました。📋"))
        )
        page.update()

    # UIリストを更新する関数
    def update_deceased_list_ui():
        # deceased_list_container.controls.clear()
        deceased_data_table.rows.clear()  # ★ DataTableの行をクリア

        # サービス層からデータを取得
        for deceased in deceased_service.get_all_deceased():
            # 詳細画面へ遷移するボタン
            detail_button = IconButton(
                Icons.ARROW_RIGHT,
                tooltip="詳細へ",
                on_click=lambda e, d_id=deceased.id: page.go(f"/detail/{d_id}"),
            )

            # 削除ボタン
            delete_button = IconButton(
                Icons.DELETE,
                icon_color=Colors.RED_500,
                data=deceased.id,
                on_click=delete_deceased,
            )

            # ★ データ行 (DataRow) の作成と追加
            deceased_data_table.rows.append(
                DataRow(
                    cells=[
                        DataCell(
                            GestureDetector(
                                content=Text(str(deceased.id)),
                                on_tap=copy_to_clipboard_and_notify,
                            )
                        ),
                        DataCell(
                            GestureDetector(
                                content=Text(deceased.name, weight=FontWeight.BOLD),
                                on_tap=copy_to_clipboard_and_notify,
                            )
                        ),
                        DataCell(
                            GestureDetector(
                                content=Text(deceased.date_of_birth),
                                on_tap=copy_to_clipboard_and_notify,
                            )
                        ),
                        DataCell(
                            Row(
                                [detail_button, delete_button], spacing=5
                            )  # アクションボタンをRowでまとめる
                        ),
                    ]
                )
            )

        # page.update() は add_deceased/delete_deceased の中で呼ばれるように、最後にまとめて実行
        page.update()

    # 被相続人を追加する関数 (ロジックはサービス層へ)
    def add_deceased(e):
        name = new_deceased_name_field.value.strip()
        dob = new_deceased_dob_field.value.strip()

        if name:
            deceased_service.add_deceased(name, dob)  # サービスを呼び出す

            new_deceased_name_field.value = ""
            new_deceased_dob_field.value = ""

            update_deceased_list_ui()

    # 被相続人を削除する関数 (ロジックはサービス層へ)
    def delete_deceased(e):
        deceased_id_to_delete = e.control.data
        deceased_service.delete_deceased(deceased_id_to_delete)  # サービスを呼び出す
        update_deceased_list_ui()

    # 初期リストの表示
    update_deceased_list_ui()

    # View の定義
    return View(
        "/",
        [
            AppBar(
                title=Text("顧客管理システム (被相続人一覧)"),
                bgcolor=Colors.BLUE_GREY_900,
            ),
            Container(
                content=Column(
                    [
                        Text("👨‍🦳 新しい被相続人を追加", size=16),
                        Row(
                            [
                                new_deceased_name_field,
                                new_deceased_dob_field,
                                CustomElevatedButton("追加", on_click=add_deceased),
                            ]
                        ),
                        Divider(height=20),
                        Text("📋 登録済み被相続人", size=16),
                        Container(
                            # content=deceased_list_container,
                            content=deceased_data_table,
                            # border=border.all(1, Colors.BLACK12),
                            padding=10,
                            width=page.width * 0.9,
                        ),
                    ],
                    horizontal_alignment=CrossAxisAlignment.START,
                ),
                padding=20,
            ),
        ],
        scroll=ScrollMode.AUTO,
    )
