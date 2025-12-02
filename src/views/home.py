# src/views/home.py
import threading

from flet import (
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    Dropdown,
    ElevatedButton,
    Icon,
    Icons,
    ListTile,
    ListView,
    MainAxisAlignment,
    Page,
    Row,
    SnackBar,
    Text,
    TextField,
    TextStyle,
    border,
    dropdown,
)

from src.services.deceased_service import (
    get_all_case_statuses,
    get_all_users,
    get_case_folder_path,
    get_case_list,
    get_incomplete_tasks,
    get_my_cases,
    get_user_capacity_data,
)

# ユーティリティとサービスのインポート
from src.utils.file_system import open_case_folder


class CaseDashboardView(Column):
    """
    メインダッシュボード画面 (Todoリスト、コントロール、案件一覧を統合)
    """

    search_timer: threading.Timer = None

    def __init__(self, page: Page):
        super().__init__(
            expand=True,
            scroll="auto",
            spacing=20,
            horizontal_alignment=CrossAxisAlignment.START,
        )
        self.page = page
        self.current_user_id = 1
        self.is_manager = True

        self.USER_MAP = get_all_users()
        self.STATUS_LIST = get_all_case_statuses()

        # --- 検索・フィルタ用コントロール ---
        self.search_field = TextField(
            label="案件番号/依頼者名で検索",
            on_change=self._debounce_search,
            width=300,
            prefix_icon=Icons.SEARCH,
            label_style=TextStyle(color=Colors.BLUE_GREY_700),
            color=Colors.BLACK,
        )

        self.status_filter = Dropdown(
            label="ステータス",
            width=150,
            options=[dropdown.Option(key="-1", text="全て")]
            + [dropdown.Option(key=str(s.id), text=s.name) for s in self.STATUS_LIST],
            value="-1",
            on_change=self._on_filter_change,
            color=Colors.BLACK,
            label_style=TextStyle(color=Colors.BLUE_GREY_700),
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
            color=Colors.BLACK,
            label_style=TextStyle(color=Colors.BLUE_GREY_700),
        )

        # --- 各種ビューの初期化 ---
        if self.is_manager:
            self.capacity_view_container = self._create_manager_capacity_view()
        self.todo_list_container = self._create_todo_list_view()
        self.my_case_list_container = self._create_my_case_list_view()
        self.main_list_view_column = self._create_main_list_view_column()

        # --- メインレイアウトの構築 ---
        self.controls = [
            Container(
                padding=15,
                expand=True,
                content=Row(
                    alignment=MainAxisAlignment.START,
                    vertical_alignment=CrossAxisAlignment.START,
                    spacing=20,
                    controls=[
                        # 左サイドバー
                        Column(
                            controls=self._get_left_sidebar_controls(),
                            width=350,
                            scroll="auto",
                        ),
                        # 右メインエリア
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

    def _show_snack(self, msg, color):
        self.page.open(
            SnackBar(
                content=Text(msg, color=Colors.WHITE),
                bgcolor=color,
                duration=3000,
            )
        )
        self.page.update()

    def _create_top_action_area(self):
        return Row(
            alignment=MainAxisAlignment.END,
            controls=[
                Text("データ管理: ", weight="bold", size=14, color=Colors.GREY_700),
                ElevatedButton(
                    "全データ保存 (JSON)",
                    icon=Icons.SAVE,
                    bgcolor=Colors.INDIGO_600,
                    color=Colors.WHITE,
                    on_click=lambda _: self._show_snack("準備中", Colors.ORANGE),
                ),
                Container(width=10),
                ElevatedButton(
                    "データ復元/取込",
                    icon=Icons.RESTORE,
                    bgcolor=Colors.TEAL_700,
                    color=Colors.WHITE,
                    on_click=lambda _: self._show_snack("準備中", Colors.ORANGE),
                ),
            ],
        )

    def _get_left_sidebar_controls(self):
        """サイドバー構成 (PDFツールへのリンクを追加)"""
        base_controls = []

        # 💡 追加: ツールリンク
        tool_links = Container(
            content=Column(
                [
                    Text("🛠️ ツール", size=16, weight="bold", color=Colors.BLUE_GREY_800),
                    ListTile(
                        leading=Icon(Icons.PICTURE_AS_PDF, color=Colors.RED_600),
                        title=Text("PDF座標設定ツール", color=Colors.BLACK),
                        on_click=lambda e: self.page.go("/pdf_tool"),
                    ),
                ]
            ),
            padding=10,
            bgcolor=Colors.WHITE,
            border_radius=10,
            border=border.all(1, Colors.GREY_300),
        )

        if self.is_manager:
            base_controls = [
                Text("🔥 チーム負荷状況", size=16, weight="bold", color=Colors.BLUE_GREY_800),
                self.capacity_view_container,
                Divider(),
                Text("📋 自分のToDo", size=16, weight="bold", color=Colors.BLUE_GREY_800),
                self.todo_list_container,
                Divider(),
                tool_links,
            ]
        else:
            base_controls = [
                Text("📋 自分のToDo", size=16, weight="bold", color=Colors.BLUE_GREY_800),
                self.todo_list_container,
                Divider(),
                Text("📂 担当案件", size=16, weight="bold", color=Colors.BLUE_GREY_800),
                self.my_case_list_container,
                Divider(),
                tool_links,
            ]
        return base_controls

    def _debounce_search(self, e):
        if self.search_timer:
            self.search_timer.cancel()
        self.search_timer = threading.Timer(0.3, self._run_search_action)
        self.search_timer.start()

    def _on_filter_change(self, e):
        self._run_search_action()

    def _run_search_action(self, *args):
        search_term = self.search_field.value if self.search_field.value else ""
        status_id_val = self.status_filter.value
        status_id = int(status_id_val) if (status_id_val and status_id_val != "-1") else None
        user_id_val = self.user_filter.value
        user_id = int(user_id_val) if (user_id_val and user_id_val != "-1") else None

        new_items = self._get_case_items(
            search_term=search_term, status_filter_id=status_id, user_filter_id=user_id
        )

        list_view = self.main_list_view_column.controls[1]
        list_view.controls = new_items
        self.page.update()

    def _update_all_views(self):
        self.todo_list_container.content.controls = self._get_todo_items()
        if self.is_manager:
            self.capacity_view_container.content.controls = self._get_capacity_items()
        else:
            self.my_case_list_container.content.controls = self._get_my_case_items()
        self._run_search_action()
        self.update()

    # --- ヘルパーメソッド群 ---
    def _get_case_items(self, search_term="", status_filter_id=None, user_filter_id=None):
        cases = get_case_list(
            search_term=search_term, status_id=status_filter_id, user_id=user_filter_id
        )
        if not cases:
            msg = (
                "条件に一致する案件はありません。"
                if (user_filter_id or status_filter_id or search_term)
                else "案件がまだ登録されていません。"
            )
            return [
                Container(
                    content=Text(msg, color=Colors.GREY_600), alignment=dict(x=0, y=0), padding=20
                )
            ]

        items = []
        for case in cases:
            case_id = case["case_id"]
            items.append(
                Container(
                    content=ListTile(
                        leading=Icon(Icons.FOLDER, color=Colors.BLUE),
                        title=Row(
                            [
                                Text(
                                    f"{case['case_number']}",
                                    weight="bold",
                                    size=16,
                                    color=Colors.BLACK,
                                ),
                                Text(f"{case['client_name']} 様", size=16, color=Colors.BLACK),
                                Container(
                                    content=Text(case["status"], color=Colors.WHITE, size=12),
                                    bgcolor=Colors.BLUE,
                                    padding=5,
                                    border_radius=5,
                                ),
                            ],
                            spacing=10,
                        ),
                        subtitle=Column(
                            [
                                Text(f"被相続人: {case['deceased_name']}", color=Colors.GREY_700),
                                Text(
                                    f"更新: {case['last_updated_at']} | 次: {case['description'] or 'なし'}",
                                    size=12,
                                    color=Colors.GREY_600,
                                ),
                            ],
                            spacing=2,
                        ),
                        trailing=ElevatedButton(
                            "📂",
                            on_click=lambda e, cid=case_id: open_case_folder(
                                self.page, cid, get_case_folder_path
                            ),
                            height=30,
                        ),
                        on_click=lambda e, cid=case_id: self.page.go(f"/detail/{cid}/dashboard"),
                    ),
                    bgcolor=Colors.WHITE,
                    border_radius=8,
                    padding=5,
                    border=border.only(bottom=border.BorderSide(1, color=Colors.GREY_200)),
                )
            )
        return items

    def _get_capacity_items(self):
        data = get_user_capacity_data()
        items = []
        for d in data:
            color = Colors.RED_700 if d["total_incomplete_tasks"] > 5 else Colors.BLACK
            items.append(
                ListTile(
                    title=Text(f"{d['name']} ({d['role']})", weight="bold", color=color, size=14),
                    subtitle=Text(
                        f"未完了: {d['total_incomplete_tasks']} | 案件: {d['total_cases_handled']}",
                        color=Colors.GREY_700,
                        size=12,
                    ),
                    dense=True,
                )
            )
        return items

    def _create_manager_capacity_view(self):
        return Container(
            content=Column(controls=self._get_capacity_items(), spacing=5, scroll="auto"),
            padding=10,
            bgcolor=Colors.WHITE,
            border_radius=10,
            height=300,
            border=border.all(1, Colors.GREY_300),
        )

    def _get_my_case_items(self):
        cases = get_my_cases(user_id=self.current_user_id, limit=10)
        if not cases:
            return [Text("現在、担当案件はありません。", color=Colors.GREY_600)]
        items = []
        for case in cases:
            items.append(
                ListTile(
                    title=Text(f"案件: {case['case_number']}", color=Colors.BLACK, size=14),
                    subtitle=Text(
                        f"依頼者: {case['client_name']} | 状態: {case['status']}",
                        color=Colors.GREY_700,
                        size=12,
                    ),
                    dense=True,
                    on_click=lambda e, cid=case["case_id"]: self.page.go(
                        f"/detail/{cid}/dashboard"
                    ),
                )
            )
        return items

    def _create_my_case_list_view(self):
        return Container(
            content=Column(controls=self._get_my_case_items(), spacing=5, scroll="auto"),
            padding=10,
            bgcolor=Colors.WHITE,
            border_radius=10,
            height=200,
            border=border.all(1, Colors.GREY_300),
        )

    def _get_todo_items(self):
        tasks = get_incomplete_tasks(user_id=self.current_user_id)
        if not tasks:
            return [Text("現在、未完了のタスクはありません。", color=Colors.GREY_600)]
        items = []
        for task in tasks:
            items.append(
                ListTile(
                    title=Text(task["description"], color=Colors.BLACK, size=14),
                    subtitle=Text(
                        f"案件: {task['case_number']} | 期限: {task['due_date']}",
                        color=Colors.GREY_700,
                    ),
                    dense=True,
                    on_click=lambda e, cid=task["case_id"]: self.page.go(
                        f"/detail/{cid}/dashboard"
                    ),
                )
            )
        return items

    def _create_todo_list_view(self):
        return Container(
            content=Column(controls=self._get_todo_items(), spacing=5, scroll="auto"),
            padding=10,
            bgcolor=Colors.WHITE,
            border_radius=10,
            height=300,
            border=border.all(1, Colors.GREY_300),
        )

    def _create_control_area(self):
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
                        bgcolor=Colors.BLUE_700,
                        color=Colors.WHITE,
                        on_click=lambda e: self.page.go("/client_register"),
                    ),
                ],
                alignment=MainAxisAlignment.START,
                vertical_alignment=CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            padding=10,
            bgcolor=Colors.BLUE_GREY_50,
            border_radius=8,
        )

    def _create_main_list_view_column(self):
        return Column(
            controls=[
                Container(
                    content=Row(
                        [Text("案件一覧", size=20, weight="bold", color=Colors.BLUE_GREY_800)]
                    ),
                    padding=dict(left=10),
                ),
                ListView(expand=True, spacing=5, padding=10, auto_scroll=False),
            ],
            expand=True,
        )
