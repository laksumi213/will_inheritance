# /components/pages/detail.py

import requests
from flet import (
    AlertDialog,
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
    TextButton,
    TextField,
    View,
    border,
)

from services import deceased_service
from services.deceased_service import get_address_info

# --- 1. モーダル編集で使用するフィールド定義 (DeceasedDetailView関数の外で定義) ---

# 氏名・基本情報
dialog_name_last_field = TextField(label="氏名 (姓)", width=150)
dialog_name_first_field = TextField(label="氏名 (名)", width=150)
dialog_kana_last_field = TextField(label="ふりがな (姓)", width=150)
dialog_kana_first_field = TextField(label="ふりがな (名)", width=150)
dialog_rel_field = TextField(label="続柄", width=200)

# 住所・本籍地
dialog_hometown_field = TextField(label="本籍地 (全体)")
dialog_zip_field = TextField(label="郵便番号", width=150)
dialog_pref_field = TextField(label="都道府県", width=150)
dialog_city_field = TextField(label="市区町村", width=200)
dialog_street_field = TextField(label="番地", width=150)
dialog_building_field = TextField(label="建物名・部屋番号")

# 日付
dialog_dob_field = TextField(label="生年月日 (YYYY-MM-DD)", width=180)
dialog_dod_field = TextField(label="死亡日 (YYYY-MM-DD)", width=180)

# タイトルコントロール
dialog_title_control = Text("情報編集", weight=FontWeight.BOLD)


def DeceasedDetailView(page: Page, deceased_id: int):
    # --- サービス層からデータを取得 ---
    deceased = deceased_service.get_deceased_by_id(deceased_id)

    if deceased:
        full_name = f"{deceased.name_last} {deceased.name_first}"
        dob_str = str(deceased.date_of_birth) if deceased.date_of_birth else ""
        dod_str = str(deceased.date_of_death) if deceased.date_of_death else "未登録"
        is_new_deceased = False
    else:
        # 新規登録の場合のデフォルト値
        full_name = "【未登録】新規登録が必要です"
        dob_str = "N/A"
        dod_str = "N/A"
        is_new_deceased = True  # 新規フラグ
        # モーダルを開くためにダミーのオブジェクトを使用（モーダル内でデータは空でロードされる）
        deceased = type(
            "DummyDeceased",
            (object,),
            {
                "name_last": "",
                "name_first": "",
                "name_last_kana": "",
                "name_first_kana": "",
                "date_of_birth": None,
                "date_of_death": None,
                "relationship_type": "本人",
                "hometown": "",
                "heirs": [],  # 相続人リストは空にしておく
            },
        )()

    # # ★ スコープ修正: 表示用変数を最初に定義
    # full_name = f"{deceased.name_last} {deceased.name_first}" if deceased else ""
    # # dob_str = str(deceased.date_of_birth) if deceased.date_of_birth else ""
    # dob_str = str(deceased.date_of_birth) if deceased else ""
    # # dod_str = str(deceased.date_of_death) if deceased.date_of_death else "未登録"
    # dod_str = str(deceased.date_of_death) if deceased else ""

    heirs_controls = Column()
    new_heir_name_field = TextField(label="相続人名 (姓 名)", width=200)
    new_heir_rel_field = TextField(label="続柄", width=150)

    # --- 共通モーダル定義 ---
    def create_edit_dialog(is_deceased: bool):
        # 続柄フィールドは被相続人（本人）の場合は表示しない (簡易的なUI制御)
        rel_row = Row([dialog_rel_field])
        if is_deceased:
            rel_row.visible = False

        date_rows = [Row([dialog_dob_field])]
        if is_deceased:
            date_rows.append(Row([dialog_dod_field]))

        return AlertDialog(
            modal=True,
            title=dialog_title_control,
            content=Container(
                content=Column(
                    [
                        Text("基本情報", weight=FontWeight.BOLD),
                        Row([dialog_name_last_field, dialog_name_first_field]),
                        Row([dialog_kana_last_field, dialog_kana_first_field]),
                        rel_row,
                        *date_rows,
                        Divider(),
                        Text("住所情報", weight=FontWeight.BOLD),
                        Row([dialog_zip_field, dialog_pref_field, dialog_city_field]),
                        Row([dialog_street_field, dialog_building_field]),
                        Divider(),
                        dialog_hometown_field,
                        Text(
                            f"【タイプ: {'被相続人' if is_deceased else '相続人'}】",
                            color=Colors.BLUE_500,
                        ),
                    ],
                    scroll=ScrollMode.AUTO,
                    tight=True,
                    spacing=10,
                ),
                width=650,
                height=550,
            ),
            actions=[
                TextButton("キャンセル", on_click=lambda e: close_dialog()),
                ElevatedButton("保存", on_click=lambda e: save_dialog(is_deceased)),
            ],
            actions_alignment=MainAxisAlignment.END,
        )

    # モーダルインスタンスを生成
    heir_edit_dialog = create_edit_dialog(is_deceased=False)
    deceased_edit_dialog = create_edit_dialog(is_deceased=True)

    # --- モーダル制御関数 ---
    def close_dialog():
        # if page.dialog:
        if deceased_edit_dialog.open:
            deceased_edit_dialog.open = False
        elif heir_edit_dialog.open:
            heir_edit_dialog.open = False
        page.update()

    def save_dialog(is_deceased: bool):
        # 画面上のフィールドから値を取得 (簡易)
        name = f"{dialog_name_last_field.value.strip()} {dialog_name_first_field.value.strip()}"
        kana_last = dialog_kana_last_field.value.strip()
        kana_first = dialog_kana_first_field.value.strip()
        zip_code = dialog_zip_field.value.strip()
        pref = dialog_pref_field.value.strip()
        city = dialog_city_field.value.strip()
        street = dialog_street_field.value.strip()
        building = dialog_building_field.value.strip()

        if is_deceased:
            # 被相続人の保存
            deceased_service.update_deceased(
                deceased_id,
                name,
                dob=dialog_dob_field.value.strip(),
                dod=dialog_dod_field.value.strip(),
                kana_last=kana_last,
                kana_first=kana_first,
                zip_code=zip_code,
                pref=pref,
                city=city,
                street=street,
                building=building,
            )
        else:
            # 相続人の保存
            heir_id = heir_edit_dialog.data
            rel = dialog_rel_field.value.strip()
            deceased_service.update_heir(
                heir_id,
                name,
                rel,
                kana_last=kana_last,
                kana_first=kana_first,
                zip_code=zip_code,
                pref=pref,
                city=city,
                street=street,
                building=building,
            )

        close_dialog()

        # メイン画面の被相続人情報表示を更新するため、画面全体を再読み込み (または page.go(page.route))
        page.go(f"/detail/{deceased_id}")

    def open_deceased_dialog(e):
        # 被相続人データをロード
        dialog_title_control.value = "被相続人情報 編集"

        dialog_name_last_field.value = deceased.name_last
        dialog_name_first_field.value = deceased.name_first
        dialog_kana_last_field.value = getattr(deceased, "name_last_kana", "") or ""
        dialog_kana_first_field.value = getattr(deceased, "name_first_kana", "") or ""
        dialog_dob_field.value = (
            str(deceased.date_of_birth) if deceased.date_of_birth else ""
        )
        dialog_dod_field.value = (
            str(deceased.date_of_death) if deceased.date_of_death else ""
        )
        dialog_rel_field.value = getattr(deceased, "relationship_type", "本人")
        dialog_hometown_field.value = getattr(deceased, "hometown", "") or ""

        # ★ 住所データを取得し、フィールドを更新 ★
        address_info = (
            get_address_info("deceased", deceased_id) if not is_new_deceased else {}
        )
        dialog_zip_field.value = address_info.get("zip_code", "")
        dialog_pref_field.value = address_info.get("prefecture", "")
        dialog_city_field.value = address_info.get("city_ward_town", "")
        dialog_street_field.value = address_info.get("street_address", "")
        dialog_building_field.value = address_info.get("building_name", "")

        page.open(deceased_edit_dialog)
        page.update()

    def _on_mount(e):
        if is_new_deceased:
            # ページがマウントされた後にモーダルを開く
            open_deceased_dialog(None)

    def open_heir_dialog(e, heir_id: int):
        current_deceased = deceased_service.get_deceased_by_id(deceased_id)
        heir_to_edit = next(
            (h for h in current_deceased.heirs if h.id == heir_id), None
        )

        if heir_to_edit:
            heir_edit_dialog.data = heir_id
            dialog_title_control.value = (
                f"相続人情報 編集 ({heir_to_edit.name_last} {heir_to_edit.name_first})"
            )

            dialog_name_last_field.value = heir_to_edit.name_last
            dialog_name_first_field.value = heir_to_edit.name_first
            dialog_kana_last_field.value = heir_to_edit.name_last_kana or ""
            dialog_kana_first_field.value = heir_to_edit.name_first_kana or ""
            dialog_rel_field.value = heir_to_edit.relationship_type
            dialog_dob_field.value = (
                str(heir_to_edit.date_of_birth) if heir_to_edit.date_of_birth else ""
            )
            dialog_hometown_field.value = heir_to_edit.hometown or ""

            # ★ 住所データを取得し、フィールドを更新 ★
            address_info = get_address_info("heir", heir_id)
            dialog_zip_field.value = address_info.get("zip_code", "")
            dialog_pref_field.value = address_info.get("prefecture", "")
            dialog_city_field.value = address_info.get("city_ward_town", "")
            dialog_street_field.value = address_info.get("street_address", "")
            dialog_building_field.value = address_info.get("building_name", "")

            page.open(heir_edit_dialog)
            # page.dialog = heir_edit_dialog
            # heir_edit_dialog.open = True
            page.update()

    # --- 住所自動入力ロジック ---
    def search_address_by_zip(e):
        zip_code = dialog_zip_field.value.replace("-", "").strip()
        if len(zip_code) == 7 and zip_code.isdigit():
            try:
                api_url = f"https://zipcloud.ibsnet.co.jp/api/search?zipcode={zip_code}"
                response = requests.get(api_url)
                data = response.json()
                if data and data.get("results"):
                    address_data = data["results"][0]
                    dialog_pref_field.value = address_data["address1"]
                    dialog_city_field.value = address_data["address2"]
                    dialog_street_field.value = address_data["address3"]
                    page.update()
                else:
                    dialog_pref_field.value = "住所が見つかりません"
                    dialog_city_field.value = ""
                    dialog_street_field.value = ""
                    page.update()
            except Exception as ex:
                print(f"APIエラー: {ex}")
        dialog_street_field.focus()

    dialog_zip_field.on_blur = search_address_by_zip

    # --- 3. 相続人リストの表示ロジック ---
    def update_heirs_list():
        heirs_controls.controls.clear()
        current_deceased = deceased_service.get_deceased_by_id(deceased_id)

        if current_deceased is None:
            # 被相続人が存在しない（新規モード）場合、相続人リストは更新せずに終了
            page.update()
            return

        for heir in current_deceased.heirs:
            heir_full_name = f"{heir.name_last} {heir.name_first}"

            heirs_controls.controls.append(
                Row(
                    [
                        Text(f"ID:{heir.id}", width=50),
                        Text(f"名前: {heir_full_name}", width=200),
                        Text(f"続柄: {heir.relationship_type}", width=150),
                        IconButton(
                            Icons.EDIT,
                            icon_color=Colors.BLUE_500,
                            data=heir.id,
                            on_click=lambda e, h_id=heir.id: open_heir_dialog(e, h_id),
                        ),
                        IconButton(
                            Icons.DELETE,
                            icon_color=Colors.RED_500,
                            data=heir.id,
                            on_click=delete_heir,
                        ),
                    ],
                    alignment=MainAxisAlignment.START,
                )
            )
        page.update()

    # --- 4. 追加/削除ロジック ---
    def add_heir(e):
        name = new_heir_name_field.value.strip()
        rel = new_heir_rel_field.value.strip()
        if name:
            deceased_service.add_heir(deceased_id, name, rel)
            new_heir_name_field.value = ""
            new_heir_rel_field.value = ""
            update_heirs_list()

    def delete_heir(e):
        heir_id_to_delete = e.control.data
        deceased_service.delete_heir(heir_id_to_delete)
        update_heirs_list()

    # 初期リストの表示
    update_heirs_list()

    # View の定義
    view_controls = [
        AppBar(title=Text("被相続人 詳細/相続人管理"), bgcolor=Colors.BLUE_GREY_700),
        Container(
            content=Column(
                [
                    Row(
                        [
                            Text(
                                "👤 被相続人情報 ✏️ ",
                                size=18,
                                weight=FontWeight.BOLD,
                            ),
                            Text(
                                "【新規登録モード】",
                                size=16,
                                color=Colors.RED_500,
                                visible=is_new_deceased,
                            ),
                        ]
                    ),
                    Row(
                        [
                            Text(
                                f"名前: {full_name}",
                                weight=FontWeight.BOLD,
                                size=16,
                                width=200,
                            ),
                            Text(f"生年月日: {dob_str}", size=14, width=150),
                            Text(f"死亡日: {dod_str}", size=14, width=150),
                            IconButton(
                                Icons.EDIT,
                                icon_color=Colors.BLUE_500,
                                tooltip="被相続人を編集",
                                on_click=open_deceased_dialog,
                            ),
                        ],
                        alignment=MainAxisAlignment.START,
                    ),
                    Divider(),
                    # 💡 修正5: 被相続人未登録の場合は相続人セクションを非表示にする
                    Column(
                        [
                            Text(
                                "👨‍👩‍👧‍👦 相続人リスト (編集ボタンで全詳細情報モーダルが開きます)",
                                size=16,
                            ),
                            Container(
                                content=heirs_controls,
                                border=border.all(1, Colors.BLACK12),
                                padding=10,
                                width=page.width * 0.8,
                            ),
                            Divider(),
                            Text("新しい相続人の追加", size=16),
                            Row(
                                [
                                    new_heir_name_field,
                                    new_heir_rel_field,
                                    ElevatedButton(
                                        "追加", on_click=lambda e: add_heir(e)
                                    ),
                                ]
                            ),
                        ],
                        visible=not is_new_deceased,  # 新規登録時は非表示
                    ),
                    Divider(),
                    ElevatedButton("👈 一覧へ戻る", on_click=lambda e: page.go("/")),
                ],
                horizontal_alignment=CrossAxisAlignment.START,
            ),
            padding=20,
        ),
    ]

    view = View(
        f"/detail/{deceased_id}",
        view_controls,
        scroll=ScrollMode.AUTO,
    )

    # ページがマウントされた時に自動でモーダルを開く設定
    view.on_view_show = _on_mount

    # 初期リストの表示 (新規の場合、heirs_controlsは空のまま)
    if not is_new_deceased:
        update_heirs_list()

    return view

    # # View の定義
    # return View(
    #     f"/detail/{deceased_id}",
    #     [
    #         AppBar(
    #             title=Text("被相続人 詳細/相続人管理"), bgcolor=Colors.BLUE_GREY_700
    #         ),
    #         Container(
    #             content=Column(
    #                 [
    #                     Text(
    #                         "👤 被相続人情報 ✏️ (クリックでモーダル編集)",
    #                         size=18,
    #                         weight=FontWeight.BOLD,
    #                     ),
    #                     Row(
    #                         [
    #                             Text(
    #                                 f"名前: {full_name}",
    #                                 weight=FontWeight.BOLD,
    #                                 size=16,
    #                                 width=200,
    #                             ),
    #                             Text(f"生年月日: {dob_str}", size=14, width=150),
    #                             Text(f"死亡日: {dod_str}", size=14, width=150),
    #                             IconButton(
    #                                 Icons.EDIT,
    #                                 icon_color=Colors.BLUE_500,
    #                                 tooltip="被相続人を編集",
    #                                 on_click=open_deceased_dialog,
    #                             ),
    #                         ],
    #                         alignment=MainAxisAlignment.START,
    #                     ),
    #                     Divider(),
    #                     Text(
    #                         "👨‍👩‍👧‍👦 相続人リスト (編集ボタンで全詳細情報モーダルが開きます)",
    #                         size=16,
    #                     ),
    #                     Container(
    #                         content=heirs_controls,
    #                         border=border.all(1, Colors.BLACK12),
    #                         padding=10,
    #                         width=page.width * 0.8,
    #                     ),
    #                     Divider(),
    #                     Text("新しい相続人の追加", size=16),
    #                     Row(
    #                         [
    #                             new_heir_name_field,
    #                             new_heir_rel_field,
    #                             ElevatedButton("追加", on_click=lambda e: add_heir(e)),
    #                         ]
    #                     ),
    #                     Divider(),
    #                     ElevatedButton(
    #                         "👈 一覧へ戻る", on_click=lambda e: page.go("/")
    #                     ),
    #                 ],
    #                 horizontal_alignment=CrossAxisAlignment.START,
    #             ),
    #             padding=20,
    #         ),
    #     ],
    #     scroll=ScrollMode.AUTO,
    # )
