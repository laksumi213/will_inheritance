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

from components.common.custom_elevatedbutton import CustomElevatedButton
from components.common.custom_textfield import CustomTextField
from services import deceased_service


def DeceasedListView(page: Page):
    # SnackBarの修正: page.open() に直接SnackBarインスタンスを渡す形に変更
    def show_snackbar(text_to_copy):
        page.open(
            SnackBar(
                Text(f"'{text_to_copy}' をクリップボードにコピーしました。📋"),
                duration=1000,
            )
        )
        page.update()

    deceased_data_table = DataTable(
        columns=[
            DataColumn(Text("ID")),
            DataColumn(Text("名前")),
            DataColumn(Text("生年月日")),
            DataColumn(Text("アクション")),
        ],
        rows=[],
        data_text_style=TextStyle(color=Colors.BLACK),
        heading_text_style=TextStyle(color=Colors.WHITE),
        heading_row_color=Colors.BLUE_GREY_300,
        bgcolor=Colors.WHITE,
        border=border.all(1, Colors.BLACK12),
        horizontal_lines=border.BorderSide(1, Colors.BLACK12),
        vertical_lines=border.BorderSide(1, Colors.BLACK12),
    )

    new_deceased_name_field = CustomTextField(
        label="新しい被相続人名 (姓 名)", width=250
    )
    new_deceased_dob_field = CustomTextField(label="生年月日(YYYY-MM-DD)", width=250)

    # コピー処理と通知を行う共通関数
    def copy_to_clipboard_and_notify(e):
        clicked_text_control: Text = e.control.content
        text_to_copy = clicked_text_control.value
        page.set_clipboard(text_to_copy)
        show_snackbar(text_to_copy)

    # UIリストを更新する関数
    def update_deceased_list_ui():
        deceased_data_table.rows.clear()

        for deceased in deceased_service.get_all_deceased():
            # ★ 氏名と生年月日の取得方法を修正
            full_name = f"{deceased.name_last} {deceased.name_first}"
            dob_str = (
                str(deceased.date_of_birth) if deceased.date_of_birth else "未登録"
            )

            detail_button = IconButton(
                Icons.ARROW_RIGHT,
                tooltip="詳細へ",
                on_click=lambda e, d_id=deceased.id: page.go(f"/detail/{d_id}"),
            )

            delete_button = IconButton(
                Icons.DELETE,
                icon_color=Colors.RED_500,
                data=deceased.id,
                on_click=delete_deceased,
            )

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
                                content=Text(full_name, weight=FontWeight.BOLD),
                                on_tap=copy_to_clipboard_and_notify,
                            )
                        ),
                        DataCell(
                            GestureDetector(
                                content=Text(dob_str),
                                on_tap=copy_to_clipboard_and_notify,
                            )
                        ),
                        DataCell(Row([detail_button, delete_button], spacing=5)),
                    ]
                )
            )
        page.update()

    # 被相続人を追加する関数 (ロジックはサービス層へ)
    def add_deceased(e):
        name = new_deceased_name_field.value.strip()
        dob = new_deceased_dob_field.value.strip()

        if name and dob:
            deceased_service.add_deceased(name, dob)
            new_deceased_name_field.value = ""
            new_deceased_dob_field.value = ""
            update_deceased_list_ui()

    # 被相続人を削除する関数 (ロジックはサービス層へ)
    def delete_deceased(e):
        deceased_id_to_delete = e.control.data
        deceased_service.delete_deceased(deceased_id_to_delete)
        update_deceased_list_ui()

    update_deceased_list_ui()

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
                            content=deceased_data_table,
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
