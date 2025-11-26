# /components/pages/home.py

import datetime
import threading

from flet import (
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    Dropdown,
    ElevatedButton,
    FilePicker,  # 追加
    FilePickerResultEvent,  # 追加
    Icon,
    Icons,
    ListTile,
    ListView,
    MainAxisAlignment,  # 追加
    Page,
    Row,
    SnackBar,  # 追加
    Text,
    TextField,
    TextStyle,
    border,
    dropdown,
)

from components.pages.client_register import reset_all_global_fields
from components.utils.file_system import open_case_folder
from services.db_setup import (
    get_all_case_statuses,
    get_all_users,
    get_case_folder_path,
    get_case_list,
    get_incomplete_tasks,
    get_my_cases,
    get_user_capacity_data,
)
from services.json_backup_service import export_database_to_json, import_database_from_json


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

        # 役割判定
        self.current_user_id = 1
        self.is_manager = True

        # --- 0. FilePickerの初期化 (CSV用) ---
        self.export_file_picker = FilePicker(on_result=self._on_export_result)
        self.import_file_picker = FilePicker(on_result=self._on_import_result)
        # ページにオーバーレイとして登録 (必須)
        self.page.overlay.extend([self.export_file_picker, self.import_file_picker])

        # --- 1. データベースからマスタ情報の取得 ---
        self.USER_MAP = get_all_users()
        self.STATUS_LIST = get_all_case_statuses()

        # --- 2. 検索・フィルタ用コントロールの作成 ---

        # (既存のコードと同じ)
        self.search_field = TextField(
            label="案件番号/依頼者名で検索",
            on_change=self._debounce_search,
            width=300,
            prefix_icon=Icons.SEARCH,
            label_style=TextStyle(color=Colors.BLACK),
            autofocus=True,
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
            label_style=TextStyle(color=Colors.BLACK),
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
            label_style=TextStyle(color=Colors.BLACK),
        )

        # --- 3. 各種ビューの初期化 ---
        if self.is_manager:
            self.capacity_view_container = self._create_manager_capacity_view()

        self.todo_list_container = self._create_todo_list_view()
        self.my_case_list_container = self._create_my_case_list_view()
        self.main_list_view_column = self._create_main_list_view_column()

        # --- 4. メインレイアウトの構築 ---
        self.controls = [
            Container(
                padding=15,
                expand=True,
                content=Row(
                    alignment="start",
                    vertical_alignment=CrossAxisAlignment.START,
                    spacing=20,
                    controls=[
                        # 左サイドバー
                        Column(
                            controls=self._get_left_sidebar_controls(),
                            width=400,
                            scroll="auto",
                        ),
                        # 右メインエリア
                        Column(
                            expand=True,
                            controls=[
                                self._create_top_action_area(),  # 💡 新規追加: CSVボタンエリア
                                Divider(),
                                self._create_control_area(),  # フィルタエリア
                                Divider(),
                                self.main_list_view_column,  # リストエリア
                            ],
                            spacing=15,
                        ),
                    ],
                ),
            )
        ]

    def _create_top_action_area(self):
        """画面上部のデータ管理ボタンエリア (JSON版)"""
        return Row(
            alignment=MainAxisAlignment.END,
            controls=[
                Text("データ管理: ", weight="bold", size=14),
                # エクスポートボタン
                ElevatedButton(
                    "全データ保存 (JSON)",
                    icon=Icons.SAVE,
                    bgcolor=Colors.INDIGO_600,
                    color=Colors.WHITE,
                    on_click=lambda _: self.export_file_picker.save_file(
                        allowed_extensions=["json"],
                        file_name=f"backup_{datetime.date.today()}.json",  # 日付入りのファイル名
                        dialog_title="バックアップファイルの保存先を選択",
                    ),
                ),
                Container(width=10),
                # インポートボタン
                ElevatedButton(
                    "データ復元/取込",
                    icon=Icons.RESTORE,
                    bgcolor=Colors.TEAL_700,
                    color=Colors.WHITE,
                    on_click=lambda _: self.import_file_picker.pick_files(
                        allow_multiple=False,
                        allowed_extensions=["json"],
                        dialog_title="復元するJSONファイルを選択 (既存データは上書きされます)",
                    ),
                ),
            ],
        )

    # コールバックメソッドの修正 (export_cases_to_csv -> export_database_to_json)
    def _on_export_result(self, e: FilePickerResultEvent):
        if e.path:
            # JSONエクスポートを実行
            success = export_database_to_json(e.path)

            if success:
                self._show_snack(f"データを保存しました: {e.path}", Colors.GREEN)
            else:
                self._show_snack("データの保存に失敗しました", Colors.RED)

    # コールバックメソッドの修正 (import_cases_from_csv -> import_database_from_json)
    def _on_import_result(self, e: FilePickerResultEvent):
        if e.files:
            file_path = e.files[0].path

            # JSONインポートを実行
            success, msg = import_database_from_json(file_path)

            self._show_snack(msg, Colors.GREEN if success else Colors.RED)
            if success:
                self._update_all_views()  # 画面を最新化

    def _show_snack(self, msg, color):
        self.page.open(
            SnackBar(
                content=Text(msg, color=Colors.WHITE),
                bgcolor=color,
                duration=3000,
            )
        )
        self.page.update()

    # --- 既存のメソッド群 ---

    def did_mount(self):
        self._update_all_views()

    def _get_left_sidebar_controls(self):
        if self.is_manager:
            return [
                Text("🔥 チーム負荷状況", size=16, weight="bold"),
                self.capacity_view_container,
                Divider(),
                Text("📋 自分のToDo", size=16, weight="bold"),
                self.todo_list_container,
            ]
        else:
            return [
                self.todo_list_container,
                Divider(),
                self.my_case_list_container,
            ]

    def _debounce_search(self, e):
        """入力停止後に検索を実行"""
        if self.search_timer:
            self.search_timer.cancel()
        self.search_timer = threading.Timer(0.3, self._run_search_action)
        self.search_timer.start()

    def _on_filter_change(self, e):
        """ドロップダウン変更時に即時検索実行"""
        self._run_search_action()

    def _run_search_action(self, *args):
        """現在の入力値（テキスト、ステータス、担当者）を取得してDB検索を実行"""
        search_term = self.search_field.value if self.search_field.value else ""

        status_id_val = self.status_filter.value
        status_id = None
        if status_id_val and status_id_val != "-1":
            try:
                status_id = int(status_id_val)
            except ValueError:
                status_id = None

        user_id_val = self.user_filter.value
        user_id = None

        if user_id_val and user_id_val != "-1":
            try:
                user_id = int(user_id_val)
            except ValueError:
                print(f"Warning: Invalid user_id value '{user_id_val}', defaulting to None.")
                user_id = None

        new_items = self._get_case_items(
            search_term=search_term, status_filter_id=status_id, user_filter_id=user_id
        )

        list_view = self.main_list_view_column.controls[-1]
        list_view.controls = new_items

        self.page.run_thread(self.update)

    def _update_all_views(self):
        """初期ロード時の全更新"""
        self.todo_list_container.content.controls = self._get_todo_items()
        if self.is_manager:
            self.capacity_view_container.content.controls = self._get_capacity_items()
        else:
            self.my_case_list_container.content.controls = self._get_my_case_items()

        self._run_search_action()

        self.update()

    # --- データ取得 & UI生成ヘルパー ---

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
                    content=Text(msg, color=Colors.BLACK), alignment=dict(x=0, y=0), padding=20
                )
            ]

        items = []
        for case in cases:
            case_id = case["case_id"]

            def open_detail(e, case_id=case_id):
                self.page.go(f"/detail/{case_id}")

            def open_folder(e, case_id=case_id):
                open_case_folder(
                    page=self.page,
                    case_id=case_id,
                    get_path_service=get_case_folder_path,
                )

            role_text = f"【{case['role_label']}】 " if case.get("role_label") else ""

            status_icon = Icons.CIRCLE_OUTLINED
            status_color = Colors.BLUE
            if case["status"] == "完了":
                status_icon = Icons.CHECK_CIRCLE
                status_color = Colors.GREEN
            elif case["status"] == "受託":
                status_icon = Icons.FLAG
                status_color = Colors.ORANGE

            items.append(
                Container(
                    content=ListTile(
                        leading=Icon(status_icon, color=status_color),
                        title=Row(
                            [
                                Text(
                                    f"{case['case_number']}",
                                    weight="bold",
                                    size=16,
                                    color=Colors.BLACK,
                                ),
                                Text(
                                    f"{case['client_name']} 様",
                                    size=16,
                                    color=Colors.BLACK,
                                ),
                                Container(
                                    content=Text(case["status"], color=Colors.WHITE, size=12),
                                    bgcolor=status_color,
                                    padding=5,
                                    border_radius=5,
                                ),
                            ],
                            spacing=10,
                            vertical_alignment=CrossAxisAlignment.CENTER,
                        ),
                        subtitle=Column(
                            [
                                Text(
                                    f"{role_text}被相続人: {case['deceased_name']}",
                                    color=Colors.BLACK,
                                ),
                                Text(
                                    f"最終更新: {case['last_updated_at']} | 次のアクション: {case['description'] or 'なし'}",
                                    size=12,
                                    color=Colors.BLACK,
                                ),
                            ],
                            spacing=2,
                        ),
                        trailing=ElevatedButton("📂 フォルダ", on_click=open_folder, height=30),
                        on_click=open_detail,
                    ),
                    bgcolor=Colors.WHITE,
                    border_radius=8,
                    padding=5,
                    border=border.only(bottom=border.BorderSide(1, color=Colors.GREY_200)),
                )
            )
        return items

    # --- Capacity View Helper ---
    def _get_capacity_items(self):
        data = get_user_capacity_data()
        items = []
        for d in data:
            color = Colors.RED_700 if d["total_incomplete_tasks"] > 5 else Colors.BLACK
            items.append(
                ListTile(
                    title=Text(f"{d['name']} ({d['role']})", weight="bold", color=color),
                    subtitle=Text(
                        f"未完了: {d['total_incomplete_tasks']} | 案件: {d['total_cases_handled']}",
                        color=Colors.BLACK,
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
        )

    # --- My Case View Helper ---
    def _get_my_case_items(self):
        cases = get_my_cases(user_id=1, limit=10)
        if not cases:
            return [Text("現在、担当案件はありません。", color=Colors.BLACK)]

        items = [Text("あなたの担当案件", weight="bold", color=Colors.BLACK)]
        for case in cases:

            def open_detail(e, cid=case["case_id"]):
                self.page.go(f"/detail/{cid}")

            items.append(
                ListTile(
                    title=Text(f"案件: {case['case_number']}", color=Colors.BLACK, size=14),
                    subtitle=Text(
                        f"依頼者: {case['client_name']} | 状態: {case['status']}",
                        color=Colors.BLACK,
                        size=12,
                    ),
                    dense=True,
                    on_click=open_detail,
                )
            )
        return items

    def _create_my_case_list_view(self):
        """todoリストエリアのUIを作成"""
        return Container(
            content=Column(controls=self._get_my_case_items(), spacing=5, scroll="auto"),
            padding=10,
            bgcolor=Colors.WHITE,
            border_radius=10,
            height=200,
        )

    # --- Todo View Helper ---
    def _get_todo_items(self):
        tasks = get_incomplete_tasks(user_id=1)
        if not tasks:
            return [Text("現在、未完了のタスクはありません。", color=Colors.BLACK)]

        items = [Text("期限が近いタスク", weight="bold", color=Colors.BLACK)]
        for task in tasks:

            def open_detail(e, cid=task["case_id"]):
                self.page.go(f"/detail/{cid}")

            items.append(
                ListTile(
                    title=Text(task["description"], color=Colors.BLACK, size=14),
                    subtitle=Text(
                        f"案件: {task['case_number']}({task['client_name']}) | 期限: {task['due_date']}",
                        color=Colors.BLACK,
                    ),
                    dense=True,
                    on_click=open_detail,
                )
            )
        return items

    def _create_todo_list_view(self):
        """todoリストエリアのUIを作成"""
        return Container(
            content=Column(controls=self._get_todo_items(), spacing=5, scroll="auto"),
            padding=10,
            bgcolor=Colors.WHITE,
            border_radius=10,
            height=300,
        )

    # --- Main Controls ---
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
                        on_click=lambda e: self._handle_new_case_register(),
                    ),
                ],
                alignment="start",
                vertical_alignment=CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            padding=10,
            bgcolor=Colors.BLUE_GREY_50,
            border_radius=8,
        )

    def _handle_new_case_register(self):
        reset_all_global_fields()
        self.page.go("/client_register")

    def _create_main_list_view_column(self):
        main_list_view = ListView(
            expand=True,
            spacing=5,
            padding=10,
            auto_scroll=False,
        )
        return Column(
            controls=[
                Container(
                    content=Row([Text("案件一覧", size=20, weight="bold")]), padding=dict(left=10)
                ),
                main_list_view,
            ],
            expand=True,
        )
