# src/views/home.py
import threading
import datetime
from typing import List, Optional, Dict, Any

from flet import (
    AppBar,
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    Dropdown,
    ElevatedButton,
    Icon,
    IconButton,
    Icons,
    ListTile,
    ListView,
    MainAxisAlignment,
    Page,
    Row,
    SnackBar,
    Text,
    TextField,
    View,
    border,
    dropdown,
    FilePicker,
    FilePickerResultEvent,
    FontWeight,
    ButtonStyle,
    padding,
    ControlEvent,
)

from src.services.deceased_service import (
    get_all_case_statuses,
    get_all_users,
    get_case_list,
    get_incomplete_tasks,
    get_my_cases,
    get_user_capacity_data,
    get_case_folder_path,
)

from src.utils.file_system import open_case_folder
from src.services.json_backup_service import export_database_to_json, import_database_from_json
from src.views.client_register import reset_all_global_fields

# 💡 重要: DB自動修復のためのinit_dbをインポート
# （もしsrc.utils.databaseが存在しない場合は、前回の回答を参考に作成してください）
try:
    from src.utils.database import init_db
except ImportError:
    # 既存環境への配慮: ファイルがない場合はダミー関数にするが、エラー解消にはファイル作成が必須
    print("Warning: src.utils.database not found. Auto-migration disabled.")
    def init_db(): pass

class CaseDashboardView(Column):
    """
    メインダッシュボード画面 (Todoリスト、コントロール、案件一覧を統合)
    """

    search_timer: Optional[threading.Timer] = None

    def __init__(self, page: Page):
        super().__init__(
            expand=True,
            scroll="auto",
            spacing=20,
            horizontal_alignment=CrossAxisAlignment.START,
        )
        self.page: Page = page
        self.current_user_id: int = 1
        self.is_manager: bool = True
        
        # 💡 初期化時にDBスキーマチェックを実行 (OperationalErrorの防止)
        try:
            init_db()
        except Exception as e:
            print(f"DB Init Error: {e}")
            if self.page:
                self.page.open(SnackBar(content=Text(f"DB初期化エラー: {e}")))

        self.USER_MAP: Dict[int, str] = get_all_users()
        self.STATUS_LIST = get_all_case_statuses()

        self.export_file_picker = FilePicker(on_result=self._on_export_result)
        self.import_file_picker = FilePicker(on_result=self._on_import_result)
        
        if self.export_file_picker not in self.page.overlay:
            self.page.overlay.extend([self.export_file_picker, self.import_file_picker])

        self.search_field = TextField(
            label="案件No/依頼者/被相続人/相続人で検索",
            on_change=self._debounce_search,
            width=400,
            prefix_icon=Icons.SEARCH,
            autofocus=True,
        )

        self.status_filter = Dropdown(
            label="ステータス",
            width=150,
            options=[dropdown.Option(key="-1", text="全て")]
            + [dropdown.Option(key=str(s.id), text=s.name) for s in self.STATUS_LIST],
            value="-1",
            on_change=self._on_filter_change,
        )

        self.manager_filter_options = [dropdown.Option(key="-1", text="担当者: 全て")]
        for uid, uname in self.USER_MAP.items():
            self.manager_filter_options.append(dropdown.Option(key=str(uid), text=uname))

        self.user_filter = Dropdown(
            label="担当者絞り込み",
            width=180,
            options=self.manager_filter_options,
            value="-1",
            disabled=not self.is_manager,
            on_change=self._on_filter_change,
        )

        if self.is_manager:
            self.capacity_view_container = self._create_manager_capacity_view()
        
        self.todo_list_container = self._create_todo_list_view()
        self.my_case_list_container = self._create_my_case_list_view()
        self.main_list_view_column = self._create_main_list_view_column()

        self.controls = [
            Container(
                padding=15,
                expand=True,
                content=Row(
                    alignment=MainAxisAlignment.START,
                    vertical_alignment=CrossAxisAlignment.START,
                    spacing=20,
                    controls=[
                        Column(
                            controls=self._get_left_sidebar_controls(),
                            width=350,
                            scroll="auto",
                        ),
                        Column(
                            expand=True,
                            controls=[
                                self._create_top_action_area(),
                                Divider(),
                                self._create_control_area(),
                                Divider(),
                                self.main_list_view_column,
                            ],
                            spacing=15,
                        ),
                    ],
                ),
            )
        ]

    def did_mount(self):
        self._update_all_views()

    def _show_snack(self, msg: str, color: str):
        self.page.open(
            SnackBar(content=Text(msg, color=Colors.WHITE), bgcolor=color, duration=3000)
        )
        self.page.update()

    def _create_top_action_area(self) -> Row:
        return Row(
            alignment=MainAxisAlignment.END,
            controls=[
                Text("データ管理: ", weight=FontWeight.BOLD, size=14),
                ElevatedButton(
                    "全データ保存 (JSON)",
                    icon=Icons.SAVE,
                    bgcolor=Colors.INDIGO_600,
                    color=Colors.WHITE,
                    on_click=lambda _: self.export_file_picker.save_file(
                        allowed_extensions=["json"],
                        file_name=f"backup_{datetime.date.today()}.json",
                        dialog_title="バックアップファイルの保存先を選択",
                    ),
                ),
                Container(width=10),
                ElevatedButton(
                    "データ復元/取込",
                    icon=Icons.RESTORE,
                    bgcolor=Colors.TEAL_700,
                    color=Colors.WHITE,
                    on_click=lambda _: self.import_file_picker.pick_files(
                        allow_multiple=False,
                        allowed_extensions=["json"],
                        dialog_title="復元するJSONファイルを選択",
                    ),
                ),
            ],
        )

    def _on_export_result(self, e: FilePickerResultEvent):
        if e.path:
            try:
                success = export_database_to_json(e.path)
                msg = f"保存{'成功' if success else '失敗'}: {e.path}"
                color = Colors.GREEN if success else Colors.ERROR
                self._show_snack(msg, color)
            except Exception as ex:
                self._show_snack(f"保存エラー: {str(ex)}", Colors.ERROR)

    def _on_import_result(self, e: FilePickerResultEvent):
        if e.files:
            try:
                success, msg = import_database_from_json(e.files[0].path)
                self._show_snack(msg, Colors.GREEN if success else Colors.ERROR)
                if success:
                    self._update_all_views()
            except Exception as ex:
                self._show_snack(f"復元エラー: {str(ex)}", Colors.ERROR)

    def _get_left_sidebar_controls(self) -> List[Any]:
        base_controls = []
        tool_links = Container(
            content=Column(
                [
                    Text("🛠️ ツール", size=16, weight=FontWeight.BOLD),
                    ListTile(
                        leading=Icon(Icons.PICTURE_AS_PDF, color=Colors.RED_400),
                        title=Text("PDF座標設定ツール"),
                        on_click=lambda e: self.page.go("/pdf_tool"),
                    ),
                ]
            ),
            padding=10,
            border_radius=10,
            border=border.all(1, Colors.OUTLINE_VARIANT),
        )

        if self.is_manager:
            base_controls = [
                Text("🔥 チーム負荷状況", size=16, weight=FontWeight.BOLD),
                self.capacity_view_container,
                Divider(),
                Text("📋 自分のToDo", size=16, weight=FontWeight.BOLD),
                self.todo_list_container,
                Divider(),
                tool_links,
            ]
        else:
            base_controls = [
                Text("📋 自分のToDo", size=16, weight=FontWeight.BOLD),
                self.todo_list_container,
                Divider(),
                Text("📂 担当案件", size=16, weight=FontWeight.BOLD),
                self.my_case_list_container,
                Divider(),
                tool_links,
            ]
        return base_controls

    def _debounce_search(self, e: ControlEvent):
        if self.search_timer:
            self.search_timer.cancel()
        self.search_timer = threading.Timer(0.3, self._run_search_action)
        self.search_timer.start()

    def _on_filter_change(self, e: ControlEvent):
        self._run_search_action()

    def _run_search_action(self, *args):
        search_term = self.search_field.value or ""
        status_id = int(self.status_filter.value) if self.status_filter.value != "-1" else None
        user_id = int(self.user_filter.value) if self.user_filter.value != "-1" else None

        new_items = self._get_case_items(search_term, status_id, user_id)
        self.main_list_view_column.controls[1].controls = new_items
        self.update()

    def _update_all_views(self):
        self.todo_list_container.content.controls = self._get_todo_items()
        if self.is_manager:
            self.capacity_view_container.content.controls = self._get_capacity_items()
        else:
            self.my_case_list_container.content.controls = self._get_my_case_items()
        
        self._run_search_action()

    def _get_case_items(self, search_term: str = "", status_filter_id: Optional[int] = None, user_filter_id: Optional[int] = None) -> List[Container]:
        cases = get_case_list(search_term, status_filter_id, user_filter_id)
        if not cases:
            msg = "条件に一致する案件はありません。" if (user_filter_id or status_filter_id or search_term) else "案件がまだ登録されていません。"
            return [Container(content=Text(msg, color=Colors.ON_SURFACE_VARIANT), padding=20)]

        items = []
        for case in cases:
            case_id = case["case_id"]
            
            status_badge = Container(
                content=Text(case["status"], color=Colors.ON_PRIMARY, size=12),
                bgcolor=Colors.PRIMARY,
                padding=padding.symmetric(horizontal=8, vertical=4),
                border_radius=4,
            )

            folder_button = ElevatedButton(
                "📂 案件フォルダを開く",
                on_click=lambda e, cid=case_id: open_case_folder(self.page, cid, get_case_folder_path),
                style=ButtonStyle(
                    bgcolor="tertiaryContainer",
                    color="onTertiaryContainer",
                ),
            )

            # 💡 SOL番号を取得して表示
            sol_number = case.get("sol_case_number", "---")

            items.append(
                Container(
                    content=ListTile(
                        leading=Icon(Icons.FOLDER, color=Colors.PRIMARY),
                        title=Row(
                            [
                                Text(f"{case['case_number']}", weight=FontWeight.BOLD, size=16),
                                Text(f"{case['client_name']} 様", size=16),
                                status_badge,
                            ],
                            spacing=10,
                        ),
                        subtitle=Column(
                            [
                                # 💡 SOL番号をサブタイトルに表示
                                Text(f"SOL番号: {sol_number} | 被相続人: {case['deceased_name']}", color=Colors.ON_SURFACE_VARIANT),
                                Text(f"更新: {case['last_updated_at']} | 次: {case['description'] or 'なし'}", size=12, color=Colors.OUTLINE),
                            ],
                            spacing=2,
                        ),
                        trailing=folder_button,
                        on_click=lambda e, cid=case_id: self.page.go(f"/detail/{cid}"),
                    ),
                    border_radius=8,
                    padding=5,
                    border=border.only(bottom=border.BorderSide(1, color=Colors.OUTLINE_VARIANT)),
                )
            )
        return items

    def _get_capacity_items(self) -> List[ListTile]:
        data = get_user_capacity_data()
        items = []
        for d in data:
            text_color = Colors.ERROR if d["total_incomplete_tasks"] > 5 else None
            items.append(
                ListTile(
                    title=Text(f"{d['name']} ({d['role']})", weight=FontWeight.BOLD, color=text_color, size=14),
                    subtitle=Text(f"未完了: {d['total_incomplete_tasks']} | 案件: {d['total_cases_handled']}", size=12),
                    dense=True,
                )
            )
        return items

    def _create_manager_capacity_view(self) -> Container:
        return Container(
            content=Column(controls=self._get_capacity_items(), spacing=5, scroll="auto"),
            padding=10,
            border_radius=10,
            height=300,
            border=border.all(1, Colors.OUTLINE_VARIANT),
        )

    def _get_my_case_items(self) -> List[Any]:
        cases = get_my_cases(user_id=self.current_user_id, limit=10)
        if not cases:
            return [Text("現在、担当案件はありません。", color=Colors.ON_SURFACE_VARIANT)]
        items = []
        for case in cases:
            # 💡 SOL番号を取得
            sol_number = case.get("sol_case_number", "---")
            items.append(
                ListTile(
                    title=Text(f"案件: {case['case_number']}", size=14),
                    subtitle=Text(f"SOL: {sol_number} | 依頼者: {case['client_name']} | 状態: {case['status']}", size=12),
                    dense=True,
                    on_click=lambda e, cid=case["case_id"]: self.page.go(f"/detail/{cid}"),
                )
            )
        return items

    def _create_my_case_list_view(self) -> Container:
        return Container(
            content=Column(controls=self._get_my_case_items(), spacing=5, scroll="auto"),
            padding=10,
            border_radius=10,
            height=200,
            border=border.all(1, Colors.OUTLINE_VARIANT),
        )

    def _get_todo_items(self) -> List[Any]:
        tasks = get_incomplete_tasks(user_id=self.current_user_id)
        if not tasks:
            return [Text("現在、未完了のタスクはありません。", color=Colors.ON_SURFACE_VARIANT)]
        items = []
        for task in tasks:
            items.append(
                ListTile(
                    title=Text(task["description"], size=14),
                    subtitle=Text(f"案件: {task['case_number']} | 期限: {task['due_date']}"),
                    dense=True,
                    on_click=lambda e, cid=task["case_id"]: self.page.go(f"/detail/{cid}"),
                )
            )
        return items

    def _create_todo_list_view(self) -> Container:
        return Container(
            content=Column(controls=self._get_todo_items(), spacing=5, scroll="auto"),
            padding=10,
            border_radius=10,
            height=300,
            border=border.all(1, Colors.OUTLINE_VARIANT),
        )

    def _create_control_area(self) -> Container:
        return Container(
            content=Row(
                controls=[
                    self.search_field,
                    self.status_filter,
                    self.user_filter,
                    Container(width=20),
                    ElevatedButton(
                        "新規案件登録",
                        icon=Icons.ADD,
                        bgcolor=Colors.PRIMARY,
                        color=Colors.ON_PRIMARY,
                        on_click=self._handle_new_case_register,
                    ),
                ],
                alignment=MainAxisAlignment.START,
                vertical_alignment=CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            padding=10,
            border_radius=8,
        )

    def _handle_new_case_register(self, e: ControlEvent):
        try:
            reset_all_global_fields()
        except Exception as ex:
            print(f"Warning: Failed to reset global fields: {ex}")

        if e.page:
            e.page.go("/client_register")
        elif self.page:
            self.page.go("/client_register")
        else:
            print("Error: Page object is not available for navigation.")

    def _create_main_list_view_column(self) -> Column:
        return Column(
            controls=[
                Container(
                    content=Row([Text("案件一覧", size=20, weight=FontWeight.BOLD)]),
                    padding=padding.only(left=10)
                ),
                ListView(expand=True, spacing=5, padding=10, auto_scroll=False),
            ],
            expand=True,
        )


def HomeView(page: Page) -> View:
    """
    ホーム画面全体を構築して返す関数。
    AppBarとコンテンツエリア（CaseDashboardView）を結合する。
    """
    
    app_bar = AppBar(
        title=Text("遺産整理・相続業務システム", weight=FontWeight.BOLD),
        bgcolor=Colors.SURFACE_VARIANT,
        actions=[
            IconButton(
                icon=Icons.REFRESH,
                tooltip="画面を更新",
                on_click=lambda e: page.go("/")
            ),
        ]
    )

    dashboard = CaseDashboardView(page)

    return View(
        route="/",
        controls=[dashboard],
        appbar=app_bar,
        padding=0,
        spacing=0
    )