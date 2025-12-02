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
)

from src.services.deceased_service import (
    delete_task,
    get_all_tasks_for_case,
    get_all_users,
    save_task,
)


def TaskManagementView(page: Page, case_id: int):
    tasks = []
    editing_task_id = None

    dialog_desc_field = TextField(label="タスク内容", width=400, autofocus=True)
    dialog_date_field = TextField(label="期限 (YYYY-MM-DD)", width=150)

    user_map = get_all_users()
    user_options = [dropdown.Option("", "未割当")] + [
        dropdown.Option(str(uid), name) for uid, name in user_map.items()
    ]
    dialog_user_field = Dropdown(label="担当者", width=200, options=user_options)

    def on_date_change(e):
        if e.control.value:
            dialog_date_field.value = e.control.value.strftime("%Y-%m-%d")
            dialog_date_field.update()

    date_picker = DatePicker(on_change=on_date_change)

    def open_date_picker(e):
        page.open(date_picker)
        page.update()

    tasks_table = DataTable(
        columns=[
            DataColumn(Text("完了", color=Colors.BLACK)),
            DataColumn(Text("タスク内容", color=Colors.BLACK)),
            DataColumn(Text("期限", color=Colors.BLACK)),
            DataColumn(Text("担当者", color=Colors.BLACK)),
            DataColumn(Text("操作", color=Colors.BLACK)),
        ],
        rows=[],
        width=float("inf"),
    )

    def render_table(update_ui=True):
        rows = []
        for t in tasks:
            rows.append(
                DataRow(
                    cells=[
                        DataCell(
                            Checkbox(
                                value=t["is_completed"],
                                on_change=lambda e, tid=t["task_id"]: toggle_status(
                                    tid, e.control.value
                                ),
                            )
                        ),
                        DataCell(Text(t["description"], color=Colors.BLACK)),
                        DataCell(Text(t["due_date"] or "", color=Colors.BLACK)),
                        DataCell(Text(t["assigned_user_name"], color=Colors.BLACK)),
                        DataCell(
                            Row(
                                [
                                    IconButton(
                                        Icons.EDIT,
                                        icon_color=Colors.BLUE,
                                        on_click=lambda e, task=t: open_edit_dialog(task),
                                    ),
                                    IconButton(
                                        Icons.DELETE,
                                        icon_color=Colors.RED,
                                        on_click=lambda e, tid=t["task_id"]: delete_handler(tid),
                                    ),
                                ]
                            )
                        ),
                    ]
                )
            )
        tasks_table.rows = rows
        if update_ui:
            tasks_table.update()

    def toggle_status(tid, val):
        current = next((x for x in tasks if x["task_id"] == tid), None)
        if current:
            save_task(
                case_id,
                tid,
                current["description"],
                current["due_date"],
                current["assigned_user_id"],
                val,
            )
            load_tasks()

    def delete_handler(tid):
        if delete_task(tid):
            page.open(SnackBar(Text("削除しました"), bgcolor=Colors.RED))
            load_tasks()

    def load_tasks(update_ui=True):
        nonlocal tasks
        tasks = get_all_tasks_for_case(case_id)
        render_table(update_ui)

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
            TextButton(
                "キャンセル", on_click=lambda e: setattr(dialog, "open", False) or page.update()
            ),
            ElevatedButton("保存", on_click=lambda e: save_dialog()),
        ],
    )

    def open_edit_dialog(task=None):
        nonlocal editing_task_id
        if task:
            editing_task_id = task["task_id"]
            dialog_desc_field.value = task["description"]
            dialog_date_field.value = task["due_date"] or ""
            dialog_user_field.value = (
                str(task["assigned_user_id"]) if task["assigned_user_id"] else ""
            )
        else:
            editing_task_id = None
            dialog_desc_field.value = ""
            dialog_date_field.value = ""
            dialog_user_field.value = ""
        page.open(dialog)
        page.update()

    def save_dialog():
        uid = int(dialog_user_field.value) if dialog_user_field.value else None
        save_task(case_id, editing_task_id, dialog_desc_field.value, dialog_date_field.value, uid)
        dialog.open = False
        page.update()
        load_tasks()

    load_tasks(False)

    return Column(
        [
            Row(
                [
                    Text("📋 タスク管理", size=24, weight="bold"),
                    ElevatedButton(
                        "＋ 追加", icon=Icons.ADD, on_click=lambda e: open_edit_dialog()
                    ),
                ],
                alignment=MainAxisAlignment.SPACE_BETWEEN,
            ),
            Divider(),
            Container(content=tasks_table, padding=10, bgcolor=Colors.WHITE, border_radius=5),
        ],
        expand=True,
        scroll="auto",
    )
