# src/views/task_management_view.py
from flet import (
    AlertDialog,
    Checkbox,
    Colors,
    Column,
    Container,
    DataCell,
    DataColumn,
    DataRow,
    DataTable,
    DatePicker,
    Divider,
    Dropdown,
    ElevatedButton,
    IconButton,
    Icons,
    MainAxisAlignment,
    Page,
    Row,
    SnackBar,
    Text,
    TextButton,
    TextField,
    dropdown,
    border,
)

# deceased_service から必要な関数を全てインポート
from src.services.deceased_service import (
    delete_task,
    get_all_tasks_for_case,
    get_all_users,
    save_task,
)


def TaskManagementView(page: Page, case_id: int):
    # --- 状態変数 ---
    tasks = []
    editing_task_id = None

    # --- UIコンポーネント定義 ---

    # タスク編集モーダル用フィールド
    dialog_desc_field = TextField(label="タスク内容", width=400, autofocus=True)
    dialog_date_field = TextField(label="期限 (YYYY-MM-DD)", width=150)

    # 担当者ドロップダウン
    user_map = get_all_users()
    user_options = [dropdown.Option("", "未割当")] + [
        dropdown.Option(str(uid), name) for uid, name in user_map.items()
    ]
    dialog_user_field = Dropdown(label="担当者", width=200, options=user_options)

    # DatePicker
    def on_date_change(e):
        if e.control.value:
            dialog_date_field.value = e.control.value.strftime("%Y-%m-%d")
            dialog_date_field.update()

    date_picker = DatePicker(
        on_change=on_date_change,
    )

    def open_date_picker(e):
        page.open(date_picker)
        page.update()

    # テーブル
    # 💡 修正: color指定を削除し、テーマに従わせる
    tasks_table = DataTable(
        columns=[
            DataColumn(Text("完了")),
            DataColumn(Text("タスク内容")),
            DataColumn(Text("期限")),
            DataColumn(Text("担当者")),
            DataColumn(Text("操作")),
        ],
        rows=[],
        width=float("inf"),
        # 💡 行の色などを調整したい場合はここで行うが、デフォルトで見やすくなるはず
        # heading_row_color=Colors.SURFACE_VARIANT,
    )

    # --- ロジック ---

    def load_tasks(update_ui=True):
        nonlocal tasks
        tasks = get_all_tasks_for_case(case_id)
        render_table(update_ui)

    def render_table(update_ui=True):
        rows = []
        for t in tasks:
            # 完了状態の切り替え
            def on_check_change(e, task_id=t["task_id"]):
                current_task = next((x for x in tasks if x["task_id"] == task_id), None)
                if current_task:
                    new_status = e.control.value
                    save_task(
                        case_id,
                        task_id,
                        current_task["description"],
                        current_task["due_date"],
                        current_task["assigned_user_id"],
                        new_status,
                    )
                    load_tasks()

            rows.append(
                DataRow(
                    cells=[
                        DataCell(
                            Checkbox(
                                value=t["is_completed"],
                                on_change=on_check_change,
                            )
                        ),
                        # 💡 修正: color指定を削除
                        DataCell(Text(t["description"])),
                        DataCell(Text(t["due_date"] or "")),
                        DataCell(Text(t["assigned_user_name"])),
                        DataCell(
                            Row(
                                [
                                    IconButton(
                                        icon=Icons.EDIT,
                                        icon_color=Colors.BLUE,
                                        on_click=lambda e, task=t: open_edit_dialog(task),
                                    ),
                                    IconButton(
                                        icon=Icons.DELETE,
                                        icon_color=Colors.RED,
                                        on_click=lambda e, tid=t["task_id"]: delete_task_handler(
                                            tid
                                        ),
                                    ),
                                ]
                            )
                        ),
                    ],
                )
            )
        tasks_table.rows = rows

        if update_ui:
            tasks_table.update()

    def delete_task_handler(task_id):
        if delete_task(task_id):
            page.open(SnackBar(Text("タスクを削除しました"), bgcolor=Colors.RED_700))
            load_tasks()

    # --- ダイアログ制御 ---

    dialog = AlertDialog(
        modal=True,
        title=Text("タスク編集"),
        content=Container(
            content=Column(
                [
                    dialog_desc_field,
                    Row(
                        [
                            dialog_date_field,
                            IconButton(Icons.CALENDAR_MONTH, on_click=open_date_picker),
                        ]
                    ),
                    dialog_user_field,
                ],
                tight=True,
                spacing=15,
            ),
            width=450,
            height=250,
        ),
        actions=[
            TextButton("キャンセル", on_click=lambda e: close_dialog()),
            ElevatedButton("保存", on_click=lambda e: save_dialog_data()),
        ],
    )

    def open_edit_dialog(task=None):
        nonlocal editing_task_id
        if task:
            # 編集モード
            editing_task_id = task["task_id"]
            dialog.title.value = "タスク編集"
            dialog_desc_field.value = task["description"]
            dialog_date_field.value = task["due_date"] or ""
            dialog_user_field.value = (
                str(task["assigned_user_id"]) if task["assigned_user_id"] else ""
            )
        else:
            # 新規モード
            editing_task_id = None
            dialog.title.value = "新規タスク登録"
            dialog_desc_field.value = ""
            dialog_date_field.value = ""
            dialog_user_field.value = ""

        page.open(dialog)
        page.update()

    def close_dialog():
        dialog.open = False
        page.update()

    def save_dialog_data():
        desc = dialog_desc_field.value
        if not desc:
            page.open(SnackBar(Text("タスク内容は必須です"), bgcolor=Colors.RED))
            return

        due = dialog_date_field.value or None
        uid_str = dialog_user_field.value
        uid = int(uid_str) if uid_str else None

        is_comp = False
        if editing_task_id:
            current = next((t for t in tasks if t["task_id"] == editing_task_id), None)
            if current:
                is_comp = current["is_completed"]

        success = save_task(case_id, editing_task_id, desc, due, uid, is_comp)
        if success:
            close_dialog()
            load_tasks()
            page.open(SnackBar(Text("保存しました"), bgcolor=Colors.GREEN))
        else:
            page.open(SnackBar(Text("保存に失敗しました"), bgcolor=Colors.RED))

    # --- メインレイアウト ---

    load_tasks(update_ui=False)

    return Column(
        controls=[
            Row(
                [
                    # 💡 修正: color=Colors.BLACK を削除し、デフォルト色（ダークモードなら白）にする
                    Text("📋 タスク管理", size=24, weight="bold"),
                    ElevatedButton(
                        "＋ タスク追加",
                        icon=Icons.ADD,
                        on_click=lambda e: open_edit_dialog(None),
                        bgcolor=Colors.BLUE_600,
                        color=Colors.WHITE,
                    ),
                ],
                alignment=MainAxisAlignment.SPACE_BETWEEN,
            ),
            Divider(),
            Container(
                content=tasks_table,
                padding=10,
                border=border.all(1, Colors.OUTLINE_VARIANT),
                border_radius=5,
                # 💡 修正: bgcolor=Colors.WHITE を削除し、ダークモードに適応させる
                # bgcolor=Colors.WHITE, 
            ),
        ],
        expand=True,
        scroll="auto",
    )