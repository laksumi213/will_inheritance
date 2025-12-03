# src/views/components/contact_controls.py
from flet import (
    Colors,
    Column,
    IconButton,
    Icons,
    MainAxisAlignment,
    Row,
    TextField,
    ControlEvent
)

# 連絡先入力フォームの幅を統一
CONTACT_FIELD_WIDTH = 350

# 1. UI 行の作成
def create_contact_input_row(
    column_container: Column, initial_value: str = "", initial_sub_type: str = "", is_email: bool = False
) -> tuple[Row, TextField]:
    """電話またはメールの入力行と削除ボタンを作成する"""

    row = Row(alignment=MainAxisAlignment.START)

    def remove_row(e):
        if row in column_container.controls:
            column_container.controls.remove(row)
            column_container.update()
            if e.page:
                e.page.update()

    value_field = TextField(
        label="メールアドレス" if is_email else "電話番号",
        value=initial_value,
        width=500 if is_email else CONTACT_FIELD_WIDTH,
        data="contact_value",
    )

    row.controls = [
        value_field,
        IconButton(
            icon=Icons.DELETE,
            icon_color=Colors.RED_500,
            on_click=remove_row,
            tooltip="削除",
        ),
    ]

    return row, value_field


# 2. 新規行の追加 (ボタンクリックハンドラ)
def add_new_contact_row(e: ControlEvent, column_container: Column, is_email: bool):
    """ボタンクリックで新しい入力行を追加し、フォーカスを設定する"""
    new_row, new_field = create_contact_input_row(column_container, is_email=is_email)
    column_container.controls.append(new_row)
    column_container.update()
    new_field.focus()
    e.page.update()


# 3. 初期行の追加
def add_initial_contact_rows(column_container: Column, is_email: bool, count: int = 1):
    """初期表示用に指定された数の空行を追加する"""
    for _ in range(count):
        new_row, _ = create_contact_input_row(column_container, is_email=is_email)
        column_container.controls.append(new_row)


# 4. データ収集
def collect_contacts(column: Column) -> list[dict]:
    """動的フォームの Column から連絡先データを収集する"""
    contacts = []
    for row in column.controls:
        if (
            isinstance(row, Row)
            and row.controls
            and isinstance(row.controls[0], TextField)
        ):
            value = row.controls[0].value.strip()
            sub_type = "Primary" 

            if value:
                contacts.append({"value": value, "sub_type": sub_type})
    return contacts