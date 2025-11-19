# /components/pages/home.py

import threading

from flet import (
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    ElevatedButton,
    ListTile,
    ListView,
    Page,
    Row,
    Text,
    TextField,
    TextStyle,
)

from components.pages.client_register import reset_all_global_fields
from components.utils.file_system import open_case_folder
from services.db_setup import (
    get_all_users,
    get_case_folder_path,
    get_case_list,
    get_incomplete_tasks,
    get_my_cases,
    get_user_capacity_data,
)


class CaseDashboardView(Column):
    """
    メインダッシュボード画面 (Todoリスト、コントロール、案件一覧を統合)
    Columnを継承し、自身がルートの縦方向コンテナとなる
    """

    # 💡 デバウンスタイマーをクラス変数として保持
    search_timer: threading.Timer = None

    def __init__(self, page: Page):
        # Columnの初期化。外側のRowと結合するため、ここではコントロールは定義しない
        super().__init__(
            expand=True,
            scroll="auto",
            spacing=20,
            horizontal_alignment=CrossAxisAlignment.START,
        )
        self.page = page

        # 役割判定 (実際は認証システムから取得)
        # 仮にユーザーID 1 を管理職（Manager）とします。
        self.current_user_id = 1
        self.is_manager = True  # 👈️ 役割判定の仮実装

        # ユーザーマップを初期化（UI表示で名前を解決するために使用）
        self.USER_MAP = get_all_users()

        self.search_field = TextField(
            label="案件番号/依頼者名で検索",
            on_change=self._debounce_search,
            width=500,
            label_style=TextStyle(color=Colors.BLACK),
            color=Colors.BLACK,
            autofocus=True,
        )

        # 内部で利用するUIコンポーネントを属性として保持
        # 💡 役割によって異なるコンテナを初期化
        if self.is_manager:
            self.capacity_view_container = self._create_manager_capacity_view()

        # 内部で利用するUIコンポーネントを属性として保持
        self.todo_list_container = self._create_todo_list_view()
        self.my_case_list_container = self._create_my_case_list_view()
        self.main_list_view_column = self._create_main_list_view_column()

        # 画面のルートとなるRowを構築し、それをcontrolsに設定
        self.controls = [
            Container(
                padding=15,  # 👈️ ここにpaddingを設定
                expand=True,
                content=Row(
                    alignment="start",
                    vertical_alignment=CrossAxisAlignment.START,
                    spacing=20,
                    controls=[
                        # 左側のエリアを役割によってコントロールを切り替える
                        Column(
                            controls=self._get_left_sidebar_controls(),  # 👈️ 新しいヘルパー関数を呼び出し
                            width=500,
                            scroll="auto",
                        ),
                        # メインコンテンツエリア (右側)
                        Column(
                            expand=True,
                            controls=[
                                # 2. コントロールエリア (上部)
                                self._create_control_area(),
                                # 3. メイン一覧エリア (下部、可変)
                                self.main_list_view_column,
                            ],
                            spacing=15,
                        ),
                    ],
                ),
            )
        ]

        self.on_mount = self._on_mount

    # 左側サイドバーのコントロールを役割に応じて取得
    def _get_left_sidebar_controls(self):
        if self.is_manager:
            return [
                Text(
                    "🔥 チーム業務負荷 (管理職ビュー)",
                    size=16,
                    weight="bold",
                    color=Colors.RED_700,
                ),
                self.capacity_view_container,
                Divider(),
                # 管理職でも自分のToDoは必要
                Text("📋 自分のToDo", size=16, weight="bold"),
                self.todo_list_container,
            ]
        else:
            return [
                # 一般担当者の場合: Todoリストと担当案件リスト
                self.todo_list_container,
                Divider(),
                self.my_case_list_container,
            ]

    # デバウンス関数を追加
    def _debounce_search(self, e):
        """入力停止後に検索を実行するためのデバウンス処理"""
        # 既存のタイマーがあればキャンセル
        if self.search_timer:
            self.search_timer.cancel()

        # 300ms後に _run_search_action を実行するタイマーを設定
        self.search_timer = threading.Timer(0.3, self._run_search_action, [e.control.value])
        self.search_timer.start()

    # デバウンスから呼ばれる実際の検索処理
    def _run_search_action(self, search_term):
        """デバウンス後に実行される検索処理"""
        list_view = self.main_list_view_column.controls[-1]
        list_view.controls = self._get_case_items(search_term)
        self.page.run_thread(self.update)  # FletのUI更新はメインスレッドで行う必要がある

    # on_submit 削除に伴い _run_search の定義を調整（デバウンス版を優先）
    # 元の on_submit 処理を、デバウンス版の _run_search_action に置き換えるか、
    # 既存の _run_search を以下のように調整します。
    def _run_search(self, e):
        """検索ボタン（残っている場合）のクリック処理"""
        # デバウンス版を直接呼び出すか、_run_search_actionを呼ぶ
        search_term = e.control.value if e.control and e.control.value else ""
        self._run_search_action(search_term)

    def _on_mount(self, e):
        """コントロールがページに追加された後にデータをロードする"""
        self._update_all_views()

    # 💡 担当案件リスト（左サイドバー）は、メイン一覧に統合するため、ここではリストビューの更新を削除します。
    # この部分が左サイドバーに残っていると冗長になるため、_update_all_views の内容を変更します。
    # 役割判定がFalseの場合の my_case_list_container の更新を削除します。

    def _update_all_views(self):
        """全ての表示データを更新"""
        # Todoリストの更新
        self.todo_list_container.content.controls = self._get_todo_items()

        # 💡 役割ごとの左サイドバーの更新
        if self.is_manager:
            self.capacity_view_container.content.controls = self._get_capacity_items()
        else:
            # 左側の担当案件リストはもう使わないため、ここは空のままにしておくか、削除する
            # ただし、UIが崩れるのを防ぐため、一旦そのままにしておきます。
            self.my_case_list_container.content.controls = self._get_my_case_items()
            # ↑ 担当者ビューの時は不要ですが、既存コードのロジック維持のため残します

        # メイン一覧の更新 (案件一覧)
        list_view = self.main_list_view_column.controls[-1]

        # 初期ロード時 (検索フィールドが空) は、自分の担当案件のみを表示
        search_term = self.search_field.value.strip()

        # if not search_term:
        #    # 💡 初期表示は自分のIDでフィルタ
        #    list_view.controls = self._get_case_items(
        #        search_term="", filter_by_user_id=self.current_user_id
        #    )
        # else:
        #    # 💡 検索時は全案件から検索 (ここではフィルタを無効)
        #    list_view.controls = self._get_case_items(search_term=search_term)

        self.update()

    # 管理職向けキャパシティビューのアイテム生成
    def _get_capacity_items(self):
        data = get_user_capacity_data()

        items = []
        for d in data:
            # 負荷が高い担当者を強調
            color = Colors.RED_700 if d["total_incomplete_tasks"] > 5 else Colors.BLACK

            items.append(
                ListTile(
                    title=Text(f"{d['name']} ({d['role']})", weight="bold", color=color),
                    subtitle=Text(
                        f"未完了タスク: {d['total_incomplete_tasks']} 件 | 担当案件数: {d['total_cases_handled']} 件"
                    ),
                    dense=True,
                )
            )
        return items

    # 管理職向けキャパシティビューのコンテナ
    def _create_manager_capacity_view(self):
        """管理職が業務量を把握するためのUI"""
        return Container(
            content=Column(
                controls=self._get_capacity_items(),
                spacing=5,
                scroll="auto",
            ),
            padding=10,
            bgcolor=Colors.WHITE,
            border_radius=10,
            width=500,
            height=300,  # 画面サイズに合わせて調整
        )

    def _get_my_case_items(self):
        """担当顧客（案件）のデータを取得し、ListTileのリストとして返す"""
        # ここではユーザーIDを固定値1としていますが、実際にはログインユーザーのIDを使用
        # 💡 get_my_cases を呼び出し
        cases = get_my_cases(user_id=1, limit=10)

        if not cases:
            return [Text("現在、担当案件はありません。", color=Colors.BLACK)]

        items = [Text("あなたの担当案件", weight="bold", color=Colors.BLACK)]

        for case in cases:
            case_id = case["case_id"]

            def open_detail(e, case_id=case["case_id"]):
                self.page.go(f"/detail/{case_id}")

            def open_folder(e, case_id=case_id):
                open_case_folder(
                    page=self.page,
                    case_id=case_id,
                    # 💡 サービスラッパーを渡す
                    get_path_service=get_case_folder_path,
                )

            # 担当ロールの表示 (user_idが設定されている場合のみ)
            role_text = ""
            if case.get("role_label"):
                role_text = f"【{case['role_label']}】"

            items.append(
                ListTile(
                    title=Text(
                        f"案件:{role_text} {case['case_number']}",
                        color=Colors.BLACK,
                        size=14,
                    ),
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
        """1.5. 担当顧客リストエリアのUI (Todoリストの下に配置)"""
        return Container(
            content=Column(
                controls=self._get_my_case_items(),  # 💡 初期ロードメッセージは _update_all_views で上書きされる
                spacing=5,
                scroll="auto",
            ),
            padding=10,
            bgcolor=Colors.WHITE,
            border_radius=10,
            width=500,
            height=200,  # 画面サイズに合わせて調整
        )

    # 案件リストの取得 (メイン一覧用) - filter_by_user_id パラメータを追加
    def _get_case_items(self, search_term="", filter_by_user_id=None):
        """案件データを取得し、ListTileのリストとして返す"""

        # 💡 サービス層の関数呼び出しに user_id パラメータを渡す
        cases = get_case_list(search_term=search_term, user_id=filter_by_user_id)

        if not cases:
            # 💡 フィルタリングされている場合はメッセージを変更
            if filter_by_user_id:
                return [
                    Text(
                        "担当案件、または該当する案件はありません。",
                        color=Colors.GREY_600,
                    )
                ]
            else:
                return [Text("該当する案件はありません。", color=Colors.GREY_600)]

        items = []
        for case in cases:
            case_id = case["case_id"]

            # 各案件をクリックした際のルーティング
            def open_detail(e, case_id=case_id):
                self.page.go(f"/detail/{case_id}")

            def open_folder(e, case_id=case_id):
                open_case_folder(
                    page=self.page,
                    case_id=case_id,
                    # 💡 サービスラッパーを渡す
                    get_path_service=get_case_folder_path,
                )

            # 担当ロールの表示 (user_idが設定されている場合のみ)
            role_text = ""
            if case.get("role_label"):
                role_text = f"【{case['role_label']}】"

            items.append(
                ListTile(
                    # 案件番号と依頼者名の前に担当ロールを表示
                    title=Text(
                        f"{role_text} {case['case_number']} - {case['client_name']}　　被相続人: {case['deceased_name'] if case['deceased_name'] != 'N/A' else '未設定'}　　ステータス: {case['status'] if case['status'] != 'N/A' else '未設定'} "
                    ),
                    subtitle=Text(
                        f" 更新日:{case['last_updated_at']}　　次アクション:{case['description']}"
                    ),
                    trailing=ElevatedButton("フォルダを開く", on_click=open_folder),
                    on_click=open_detail,
                )
            )
        return items

    def _get_todo_items(self):
        """Todoデータを取得し、ListTileのリストとして返す"""
        # ユーザーIDを固定値1としていますが、実際にはログインユーザーのIDを使用
        tasks = get_incomplete_tasks(user_id=1)

        if not tasks:
            return [Text("現在、未完了のタスクはありません。", color=Colors.GREY_600)]

        items = [Text("期限が近いタスク", weight="bold", color=Colors.BLACK)]

        for task in tasks:
            # タスククリックで案件詳細に遷移するロジック
            case_id = task["case_id"]  # 👈️ サービス関数から取得したID

            def open_detail(e, case_id=case_id):
                self.page.go(f"/detail/{case_id}")

            items.append(
                ListTile(
                    title=Text(
                        task["description"],
                        color=Colors.BLACK,
                        size=14,
                    ),
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
        """1. todoリストエリアのUI (Containerにラップ)"""
        return Container(
            content=Column(
                controls=self._get_todo_items(),  # 初期データは__init__で更新される
                spacing=5,
                scroll="auto",
            ),
            padding=10,
            bgcolor=Colors.WHITE,
            border_radius=10,
            width=500,
            height=300,
        )

    def _create_control_area(self):
        """2. コントロールエリア（検索・フィルター）のUI"""
        return Container(
            content=Row(
                controls=[
                    self.search_field,
                    ElevatedButton(
                        "➕ 新規案件登録",
                        # on_click=lambda e: self.page.go("/client_register"),
                        on_click=lambda e: self._handle_new_case_register(),
                        # "➕ 新規案件登録", on_click=lambda e: self.page.go("/detail/-1")
                    ),
                    # ここにステータスフィルターなどのドロップダウンを追加可能
                ],
                alignment="start",
                spacing=20,
            ),
            padding=10,
            bgcolor=Colors.BLUE_GREY_50,
            border_radius=5,
            width=None,
        )
    
    def _handle_new_case_register(self):
        """新規案件登録前にフィールドをリセットし、遷移する"""
        
        # 1. 遷移先（client_register.py）のグローバルフィールドをリセット
        reset_all_global_fields()
        
        # 2. 新規登録モードのルートに遷移
        self.page.go("/client_register") # /client_register は /detail/-1 と異なり、単独のルート

    def _create_main_list_view_column(self):
        """3. メイン一覧エリア（案件リスト表示）のUI"""

        # 初期ロード時に自分の案件データを取得して設定する
        initial_case_items = self._get_case_items(
            search_term="",
            filter_by_user_id=self.current_user_id,  # 自分のIDでフィルタ
        )

        # ListViewはColumnの最後の要素としてexpandさせる
        main_list_view = ListView(
            controls=initial_case_items,
            expand=True,
            spacing=10,
            auto_scroll=False,
        )

        return Column(
            controls=[
                # 自分の案件であることを強調
                Text("案件一覧 (初期表示: 自分の担当案件)", size=20, weight="bold"),
                Divider(),
                main_list_view,
            ],
            expand=True,
            scroll="auto",
        )
