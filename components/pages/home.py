# /components/pages/home.py

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

# サービス層をインポート
from services.db_setup import get_case_list, get_incomplete_tasks


class CaseDashboardView(Column):
    """
    メインダッシュボード画面 (Todoリスト、コントロール、案件一覧を統合)
    Columnを継承し、自身がルートの縦方向コンテナとなる
    """

    def __init__(self, page: Page):
        # Columnの初期化。外側のRowと結合するため、ここではコントロールは定義しない
        super().__init__(
            expand=True,
            scroll="auto",
            spacing=20,
            horizontal_alignment=CrossAxisAlignment.START,
        )
        self.page = page
        self.search_field = TextField(
            label="案件番号/依頼者名で検索",
            on_submit=self._run_search,
            width=250,
            label_style=TextStyle(color=Colors.BLACK),
            color=Colors.BLACK,
        )

        # 内部で利用するUIコンポーネントを属性として保持
        self.todo_list_container = self._create_todo_list_view()
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
                        # 1. Todoリストエリア (左側、固定幅)
                        self.todo_list_container,
                        # メインコンテンツエリア (右側)
                        Column(
                            expand=True,  # 残りの幅を全て使用
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

        # データをロード
        # self._update_all_views()
        self.on_mount = self._on_mount

    def _on_mount(self, e):
        """コントロールがページに追加された後にデータをロードする"""
        self._update_all_views()

    def _update_all_views(self):
        """全ての表示データを更新"""
        # Todoリストの更新
        self.todo_list_container.content.controls = self._get_todo_items()

        # メイン一覧の更新
        list_view = self.main_list_view_column.controls[-1]
        list_view.controls = self._get_case_items(self.search_field.value)

        self.update()

    def _run_search(self, e):
        """検索ボタンまたはEnterキーで案件一覧を更新"""
        list_view = self.main_list_view_column.controls[-1]
        list_view.controls = self._get_case_items(self.search_field.value)
        self.update()

    def _get_case_items(self, search_term=""):
        """案件データを取得し、ListTileのリストとして返す"""
        cases = get_case_list(search_term=search_term)

        if not cases:
            return [Text("該当する案件はありません。", color=Colors.GREY_600)]

        items = []
        for case in cases:
            # 各案件をクリックした際のルーティング
            def open_detail(e, case_id=case["case_id"]):
                self.page.go(f"/detail/{case_id}")

            items.append(
                ListTile(
                    title=Text(f"{case['case_number']} - {case['client_name']}"),
                    subtitle=Text(
                        f"被相続人: {case['deceased_name']} | ステータス: {case['status']} | 契約日: {case['contract_date']}"
                    ),
                    trailing=ElevatedButton("詳細", on_click=open_detail),
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
            items.append(
                ListTile(
                    title=Text(
                        task["description"],
                        color=Colors.BLACK,
                        size=14,
                    ),
                    subtitle=Text(
                        f"案件: {task['case_number']} | 期限: {task['due_date']}",
                        color=Colors.BLACK,
                    ),
                    dense=True,
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
            width=350,
            height=600,
        )

    def _create_control_area(self):
        """2. コントロールエリア（検索・フィルター）のUI"""
        return Container(
            content=Row(
                controls=[
                    self.search_field,
                    ElevatedButton("検索", on_click=self._run_search),
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

    def _create_main_list_view_column(self):
        """3. メイン一覧エリア（案件リスト表示）のUI"""

        # ListViewはColumnの最後の要素としてexpandさせる
        main_list_view = ListView(
            controls=[],  # 初期データは__init__で更新される
            expand=True,
            spacing=10,
            auto_scroll=False,
        )

        return Column(
            controls=[
                Text("案件一覧", size=20, weight="bold"),
                Divider(),
                main_list_view,
            ],
            expand=True,
            scroll="auto",
        )


# def DeceasedListView(page: Page):
#     # SnackBarの修正: page.open() に直接SnackBarインスタンスを渡す形に変更
#     def show_snackbar(text_to_copy):
#         page.open(
#             SnackBar(
#                 Text(f"'{text_to_copy}' をクリップボードにコピーしました。📋"),
#                 duration=1000,
#             )
#         )
#         page.update()

#     deceased_data_table = DataTable(
#         columns=[
#             DataColumn(Text("ID")),
#             DataColumn(Text("名前")),
#             DataColumn(Text("生年月日")),
#             DataColumn(Text("アクション")),
#         ],
#         rows=[],
#         data_text_style=TextStyle(color=Colors.BLACK),
#         heading_text_style=TextStyle(color=Colors.WHITE),
#         heading_row_color=Colors.BLUE_GREY_300,
#         bgcolor=Colors.WHITE,
#         border=border.all(1, Colors.BLACK12),
#         horizontal_lines=border.BorderSide(1, Colors.BLACK12),
#         vertical_lines=border.BorderSide(1, Colors.BLACK12),
#     )

#     new_deceased_name_field = CustomTextField(
#         label="新しい被相続人名 (姓 名)", width=250
#     )
#     new_deceased_dob_field = CustomTextField(label="生年月日(YYYY-MM-DD)", width=250)

#     # コピー処理と通知を行う共通関数
#     def copy_to_clipboard_and_notify(e):
#         clicked_text_control: Text = e.control.content
#         text_to_copy = clicked_text_control.value
#         page.set_clipboard(text_to_copy)
#         show_snackbar(text_to_copy)

#     # UIリストを更新する関数
#     def update_deceased_list_ui():
#         deceased_data_table.rows.clear()

#         for deceased in deceased_service.get_all_deceased():
#             # ★ 氏名と生年月日の取得方法を修正
#             full_name = f"{deceased.name_last} {deceased.name_first}"
#             dob_str = (
#                 str(deceased.date_of_birth) if deceased.date_of_birth else "未登録"
#             )

#             detail_button = IconButton(
#                 Icons.ARROW_RIGHT,
#                 tooltip="詳細へ",
#                 on_click=lambda e, d_id=deceased.id: page.go(f"/detail/{d_id}"),
#             )

#             delete_button = IconButton(
#                 Icons.DELETE,
#                 icon_color=Colors.RED_500,
#                 data=deceased.id,
#                 on_click=delete_deceased,
#             )

#             deceased_data_table.rows.append(
#                 DataRow(
#                     cells=[
#                         DataCell(
#                             GestureDetector(
#                                 content=Text(str(deceased.id)),
#                                 on_tap=copy_to_clipboard_and_notify,
#                             )
#                         ),
#                         DataCell(
#                             GestureDetector(
#                                 content=Text(full_name, weight=FontWeight.BOLD),
#                                 on_tap=copy_to_clipboard_and_notify,
#                             )
#                         ),
#                         DataCell(
#                             GestureDetector(
#                                 content=Text(dob_str),
#                                 on_tap=copy_to_clipboard_and_notify,
#                             )
#                         ),
#                         DataCell(Row([detail_button, delete_button], spacing=5)),
#                     ]
#                 )
#             )
#         page.update()

#     # 被相続人を追加する関数 (ロジックはサービス層へ)
#     def add_deceased(e):
#         name = new_deceased_name_field.value.strip()
#         dob = new_deceased_dob_field.value.strip()

#         if name and dob:
#             deceased_service.add_deceased(name, dob)
#             new_deceased_name_field.value = ""
#             new_deceased_dob_field.value = ""
#             update_deceased_list_ui()

#     # 被相続人を削除する関数 (ロジックはサービス層へ)
#     def delete_deceased(e):
#         deceased_id_to_delete = e.control.data
#         deceased_service.delete_deceased(deceased_id_to_delete)
#         update_deceased_list_ui()

#     update_deceased_list_ui()

#     return View(
#         "/",
#         [
#             AppBar(
#                 title=Text("顧客管理システム (被相続人一覧)"),
#                 bgcolor=Colors.BLUE_GREY_900,
#             ),
#             Container(
#                 content=Column(
#                     [
#                         Text("👨‍🦳 新しい被相続人を追加", size=16),
#                         Row(
#                             [
#                                 new_deceased_name_field,
#                                 new_deceased_dob_field,
#                                 CustomElevatedButton("追加", on_click=add_deceased),
#                             ]
#                         ),
#                         Divider(height=20),
#                         Text("📋 登録済み被相続人", size=16),
#                         Container(
#                             content=deceased_data_table,
#                             padding=10,
#                             width=page.width * 0.9,
#                         ),
#                     ],
#                     horizontal_alignment=CrossAxisAlignment.START,
#                 ),
#                 padding=20,
#             ),
#         ],
#         scroll=ScrollMode.AUTO,
#     )
