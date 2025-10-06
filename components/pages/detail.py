# /components/pages/detail.py

from flet import (
    AppBar,
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    ElevatedButton,
    FontWeight,
    IconButton,
    Icons,
    MainAxisAlignment,
    Page,
    Row,
    ScrollMode,
    Text,
    TextField,
    View,
    border,
)

from services import deceased_service  # サービス層からデータ操作関数をインポート


def DeceasedDetailView(page: Page, deceased_id: int):
    # サービス層からデータを取得
    deceased = deceased_service.get_deceased_by_id(deceased_id)

    if not deceased:
        # ... エラー処理 (省略)
        return View(
            "/detail",
            [
                AppBar(title=Text("エラー"), bgcolor=Colors.BLUE_GREY_900),
                Text("指定された被相続人が見つかりません。", size=16),
                ElevatedButton("一覧に戻る", on_click=lambda e: page.go("/")),
            ],
        )

    # 被相続人情報のためのコントロール（初期値設定）
    deceased_name_field = TextField(
        value=deceased.name,
        label="被相続人名",
        read_only=True,
        border_color=Colors.TRANSPARENT,
    )
    deceased_dob_field = TextField(
        value=deceased.date_of_birth,
        label="生年月日(YYYY-MM-DD)",
        read_only=True,
        border_color=Colors.TRANSPARENT,
    )
    deceased_edit_button = IconButton(
        Icons.EDIT,
        icon_color=Colors.BLUE_500,
        on_click=lambda e: toggle_deceased_edit(e, True),
    )
    deceased_save_button = IconButton(
        Icons.SAVE,
        icon_color=Colors.GREEN_500,
        visible=False,
        on_click=lambda e: save_deceased_data(e),
    )

    # UI要素の準備
    heirs_controls = Column()
    new_heir_name_field = TextField(label="相続人名", width=200)
    new_heir_rel_field = TextField(label="続柄", width=150)

    # 1. 被相続人の編集モードを切り替える関数
    def toggle_deceased_edit(e, is_editing: bool):
        deceased_name_field.read_only = not is_editing
        deceased_dob_field.read_only = not is_editing
        deceased_name_field.border_color = (
            Colors.BLACK12 if is_editing else Colors.TRANSPARENT
        )
        deceased_dob_field.border_color = (
            Colors.BLACK12 if is_editing else Colors.TRANSPARENT
        )
        deceased_edit_button.visible = not is_editing
        deceased_save_button.visible = is_editing
        page.update()

    # 2. 被相続人データを保存する関数
    def save_deceased_data(e):
        name = deceased_name_field.value.strip()
        dob = deceased_dob_field.value.strip()

        if name and dob:
            # サービス層の更新関数を呼び出す
            deceased_service.update_deceased(deceased_id, name, dob)

            # 編集モードを終了
            toggle_deceased_edit(e, False)
            page.update()  # 変更が反映された状態で再描画
        else:
            # エラーメッセージ表示など (今回は省略)
            pass

    # 相続人リストを更新する関数
    def update_heirs_list():
        heirs_controls.controls.clear()

        # 詳細画面では再取得が必要なため、サービス層経由で最新のDeceasedオブジェクトを取得
        current_deceased = deceased_service.get_deceased_by_id(deceased_id)

        for heir in current_deceased.heirs:
            # 3. 相続人の編集用フィールドとボタン
            heir_name_field = TextField(
                value=heir.name,
                width=200,
                data=heir.id,
                read_only=True,
                border_color=Colors.TRANSPARENT,
            )
            heir_rel_field = TextField(
                value=heir.relationship_name,
                width=150,
                data=heir.id,
                read_only=True,
                border_color=Colors.TRANSPARENT,
            )

            # 編集ボタン (アイコンボタンの代わりにRowに入れて管理しやすくする)
            edit_save_row = Row(
                [
                    IconButton(
                        Icons.EDIT,
                        icon_color=Colors.BLUE_500,
                        data=heir.id,
                        on_click=lambda e: toggle_heir_edit(
                            e, True, heir_name_field, heir_rel_field, e.control.parent
                        ),
                    ),
                ],
                spacing=0,
            )

            heirs_controls.controls.append(
                Row(
                    [
                        heir_name_field,
                        heir_rel_field,
                        edit_save_row,
                        IconButton(
                            Icons.DELETE,
                            icon_color=Colors.RED_500,
                            data=heir.id,
                            on_click=delete_heir,
                        ),
                    ],
                    alignment=MainAxisAlignment.SPACE_BETWEEN,
                )
            )

            # 4. 相続人の編集モードを切り替える関数

    def toggle_heir_edit(
        e,
        is_editing: bool,
        name_field: TextField,
        rel_field: TextField,
        controls_row: Row,
    ):
        name_field.read_only = not is_editing
        rel_field.read_only = not is_editing
        name_field.border_color = Colors.BLACK12 if is_editing else Colors.TRANSPARENT
        rel_field.border_color = Colors.BLACK12 if is_editing else Colors.TRANSPARENT

        controls_row.controls.clear()

        if is_editing:
            # 編集モード: 保存ボタンを表示
            controls_row.controls.append(
                IconButton(
                    Icons.SAVE,
                    icon_color=Colors.GREEN_500,
                    data=e.control.data,
                    on_click=lambda event: save_heir_data(
                        event, name_field, rel_field, controls_row
                    ),
                )
            )
        else:
            # 表示モード: 編集ボタンを表示
            controls_row.controls.append(
                IconButton(
                    Icons.EDIT,
                    icon_color=Colors.BLUE_500,
                    data=e.control.data,
                    on_click=lambda event: toggle_heir_edit(
                        event, True, name_field, rel_field, controls_row
                    ),
                )
            )
        page.update()

    # 5. 相続人データを保存する関数
    def save_heir_data(
        e, name_field: TextField, rel_field: TextField, controls_row: Row
    ):
        heir_id = e.control.data
        name = name_field.value.strip()
        rel = rel_field.value.strip()

        if name:
            # サービス層の更新関数を呼び出す
            deceased_service.update_heir(heir_id, name, rel)

            # 編集モードを終了
            toggle_heir_edit(e, False, name_field, rel_field, controls_row)
        # エラー処理は省略

        # heirs_controls.controls.append(
        #     Row(
        #         [
        #             Text(f"名前: {heir.name}, 続柄: {heir.relationship_name}"),
        #             IconButton(
        #                 Icons.DELETE,
        #                 icon_color=Colors.RED_500,
        #                 data=heir.id,
        #                 on_click=delete_heir,
        #             ),
        #         ],
        #         alignment=MainAxisAlignment.SPACE_BETWEEN,
        #     )
        # )
        page.update()

    # 相続人を追加する関数 (ロジックはサービス層へ)
    def add_heir(e):
        name = new_heir_name_field.value.strip()
        rel = new_heir_rel_field.value.strip()

        if name:
            deceased_service.add_heir(deceased_id, name, rel)  # サービスを呼び出す

            new_heir_name_field.value = ""
            new_heir_rel_field.value = ""

            update_heirs_list()

    # 相続人を削除する関数 (ロジックはサービス層へ)
    def delete_heir(e):
        heir_id_to_delete = e.control.data
        deceased_service.delete_heir(heir_id_to_delete)  # サービスを呼び出す
        update_heirs_list()

    # 初期リストの表示
    update_heirs_list()

    # View の定義
    return View(
        f"/detail/{deceased_id}",
        [
            AppBar(
                title=Text("被相続人 詳細/相続人管理"),
                bgcolor=Colors.BLUE_GREY_700,
            ),
            Container(
                content=Column(
                    [
                        Text("👤 被相続人情報 ✏️", size=18, weight=FontWeight.BOLD),
                        Row(
                            [
                                deceased_name_field,
                                deceased_dob_field,
                                deceased_edit_button,
                                deceased_save_button,
                            ],
                            alignment=MainAxisAlignment.START,
                        ),
                        Divider(),
                        Text("👨‍👩‍👧‍👦 相続人リスト ✏️", size=16),
                        Container(
                            content=heirs_controls,
                            border=border.all(1, Colors.BLACK12),
                            padding=10,
                            width=page.width * 0.8,
                        ),
                        # Text(
                        #     f"被相続人名: {deceased.name}",
                        #     weight=FontWeight.BOLD,
                        #     size=18,
                        # ),
                        # Text(f"生年月日: {deceased.date_of_birth}"),
                        # Divider(),
                        # Text("👨‍👩‍👧‍👦 相続人リスト", size=16),
                        # Container(
                        #     content=heirs_controls,
                        #     border=border.all(1, Colors.BLACK12),
                        #     padding=10,
                        #     width=page.width * 0.8,
                        # ),
                        Divider(),
                        Text("新しい相続人の追加", size=16),
                        Row(
                            [
                                new_heir_name_field,
                                new_heir_rel_field,
                                ElevatedButton("追加", on_click=add_heir),
                            ]
                        ),
                        Divider(),
                        ElevatedButton(
                            "👈 一覧へ戻る", on_click=lambda e: page.go("/")
                        ),
                    ],
                    horizontal_alignment=CrossAxisAlignment.START,
                ),
                padding=20,
            ),
        ],
        scroll=ScrollMode.AUTO,
    )
