# /components/pages/detail.py

from flet import (
    AlertDialog,
    AppBar,
    ButtonStyle,
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    Dropdown,
    ElevatedButton,
    FilePicker,  # FilePickerを追加
    FilePickerResultEvent,  # FilePickerResultEventを追加
    FontWeight,
    IconButton,
    Icons,
    MainAxisAlignment,
    Page,
    Row,
    ScrollMode,
    SnackBar,
    Text,
    TextButton,
    TextField,
    View,
    border,
    dropdown,
)

from components.utils.date_utils import convert_seireki_to_wareki
from components.utils.ui_utils import show_confirm_dialog
from services import deceased_service
from services.db_setup import get_all_users
from services.deceased_service import (
    parse_all_flexible_date,
    update_case_assignment,  # 担当者更新
    update_case_folder_path,  # フォルダパス更新
    get_address_by_id,
    get_case_by_id,
)

# --- グローバルな UI 定義 ---

# 💡 担当者情報フィールドの定義 (モーダル内で使用していたため、このファイルに残す)
USER_MAP = get_all_users()
USER_OPTIONS = [dropdown.Option(str(id), name) for id, name in USER_MAP.items()]
USER_OPTIONS.insert(0, dropdown.Option("", "未割当"))  # 値がNone/空文字の場合は未割定とする

# 案件担当者ドロップダウン（Assignment Modal用）
dialog_manager_field = Dropdown(
    label="担当者1 (進捗管理)",
    width=200,
    options=USER_OPTIONS,
    value="",
    autofocus=True,
)
dialog_operator_field = Dropdown(
    label="担当者2 (実務担当)", width=200, options=USER_OPTIONS, value=""
)


def on_date_blur_handler(e, wareki_text: Text):
    """TextFieldがフォーカスを失ったときに実行されるハンドラー。和暦表示を更新する。"""

    input_value = e.control.value  # e.control は操作された TextField
    wareki_text.value = ""  # 初期化

    if not input_value:
        e.control.error_text = None
        wareki_text.update()
        e.control.update()
        return

    try:
        # 柔軟な解析関数で日付オブジェクトを取得 (date.date型が返る想定)
        validated_date = parse_all_flexible_date(input_value)

        # YYYY-MM-DD 形式にフォーマットし直し、TextFieldの値を更新
        e.control.value = validated_date.isoformat()
        e.control.error_text = None  # エラーメッセージをクリア

        # ★ 和暦に変換してTEXTコントロールを更新 ★
        wareki_text.value = convert_seireki_to_wareki(validated_date)

    except ValueError:
        # 解析に失敗した場合
        e.control.error_text = "無効な日付形式です"
        wareki_text.value = ""

    wareki_text.update()  # Textコントロールを更新
    e.control.update()  # TextFieldの見た目を更新


# --- 1. モーダル編集で使用するフィールド定義  ---

# 氏名・基本情報
dialog_name_last_field = TextField(label="氏名 (姓)", width=150, autofocus=True)
dialog_name_first_field = TextField(label="氏名 (名)", width=150)
dialog_kana_last_field = TextField(label="ふりがな (姓)", width=150)
dialog_kana_first_field = TextField(label="ふりがな (名)", width=150)
dialog_rel_field = TextField(label="続柄", width=200)

# 住所・本籍地
dialog_hometown_field = TextField(label="本籍地")
dialog_zip_field = TextField(label="郵便番号", width=150)
dialog_pref_field = TextField(label="都道府県", width=150)
dialog_city_field = TextField(label="市区町村", width=200)
dialog_street_field = TextField(label="番地", width=150)
dialog_building_field = TextField(label="建物名・部屋番号")

# 連絡先入力のコンテナ (動的フォームを保持)
phone_inputs_column = Column(controls=[], spacing=5)
email_inputs_column = Column(controls=[], spacing=5)

# 日付
dialog_dob_field = TextField(
    label="生年月日 (YYYY-MM-DD)",
    width=180,
)
wareki_dob_text = Text(value="", width=250, color=Colors.BLUE_GREY_600, weight=FontWeight.W_500)
dialog_dob_field.on_blur = lambda e: on_date_blur_handler(e, wareki_dob_text)

dialog_dod_field = TextField(
    label="死亡日 (YYYY-MM-DD)",
    width=180,
)
wareki_dod_text = Text(value="", width=250, color=Colors.BLUE_GREY_600, weight=FontWeight.W_500)
dialog_dod_field.on_blur = lambda e: on_date_blur_handler(e, wareki_dod_text)

# タイトルコントロール
dialog_title_control = Text("情報編集", weight=FontWeight.BOLD)
# 案件番号入力フィールド
dialog_case_number_field = TextField(label="案件番号", width=250)


def copy_to_clipboard_and_notify(e, page: Page, content: str):
    """クリックされたテキストをクリップボードにコピーし、SnackBarで通知する"""

    # データを取得
    text_to_copy = content.strip()

    if not text_to_copy or text_to_copy == "N/A":
        return

    # 1. クリップボードにコピー
    # Fletの Page.set_clipboard() を使用
    page.set_clipboard(text_to_copy)

    # 2. SnackBarで通知
    snack_bar_content = Text(
        f"'{text_to_copy[:30].strip()}' をクリップボードにコピーしました。📋",
        color=Colors.WHITE,
    )

    page.open(
        SnackBar(
            content=snack_bar_content,
            bgcolor=Colors.BLUE_GREY_700,
            duration=1500,
        )
    )
    page.update()


def DeceasedDetailView(page: Page, case_id: int):
    # --- FilePickerの初期化とオーバーレイへの追加 ---
    file_picker = FilePicker(on_result=lambda e: page.update())
    if file_picker not in page.overlay:
        page.overlay.append(file_picker)

    # --- サービス層からデータを取得 ---
    case = deceased_service.get_case_by_id(case_id)
    deceased = deceased_service.get_deceased_by_id(case_id)
    
    # 新規モードのフラグを定義 (IDの比較を case_id に合わせる)
    is_new_client_case = case_id == -1  # 新規案件（契約者登録）モード
    is_new_deceased = case_id == 0  # 被相続人単独の新規登録モード
    deceased_id = deceased.id if deceased else case_id

    # 💡 最後の住所情報を取得
    last_address = None
    if deceased and deceased.last_address_id:
        last_address = get_address_by_id(deceased.last_address_id)

    display_deceased_address = "未登録"
    copyable_full_address = "未登録" # 💡 コピー用の変数も初期化

    if last_address:
        # last_address は Address オブジェクト
        # 郵便番号、都道府県、市区町村、番地、建物名などを結合して表示用の文字列を作成
        address_parts = [
            last_address.prefecture,
            last_address.city_ward_town,
            last_address.street_address,
        ]
        
        # 住所本体の整形
        raw_deceased_address = "".join(filter(None, address_parts))
        building = last_address.building_name if last_address.building_name else ""
        zip_code = last_address.zip_code if last_address.zip_code else ""
        
        # 1. 表示用の住所文字列の生成: 住所 + (建物名)
        if raw_deceased_address:
             display_deceased_address = raw_deceased_address
             if building:
                 display_deceased_address += f" ({building})"
        elif building:
             display_deceased_address = f"建物名: {building}"
        else:
            display_deceased_address = "未登録"
            
        # 2. コピー用の完全な住所を作成: 〒 + 住所 + 建物名
        copyable_full_address = (
            f"〒{zip_code} {raw_deceased_address} {building}"
            if raw_deceased_address
            else "未登録"
        ).strip()
    
    # 案件情報を取得
    case = deceased.case if deceased and deceased.case else None

    # if deceased and deceased_id > 0:
    #     # deceased_id > 0 の場合のみ、住所情報を取得する
    #     deceased_address_info = {}
    #     deceased_address_info = deceased_service.get_address_info("deceased", deceased_id)

    #     # 住所の整形
    #     address_parts = [
    #         deceased_address_info.get("prefecture", ""),
    #         deceased_address_info.get("city_ward_town", ""),
    #         deceased_address_info.get("street_address", ""),
    #     ]
    #     raw_deceased_address = "".join(filter(None, address_parts))
    #     # 🎯 建物名を取得
    #     building = deceased_address_info.get("building_name", "")

    #     # 🎯 コピー用の完全な住所を作成 (住所 + 建物名)
    #     copyable_full_address = raw_deceased_address
    #     if building:
    #         # 住所と建物名の間にスペースを入れる
    #         copyable_full_address += f" {building}"

    #     # 表示用の住所文字列の生成 (元のロジックを維持)
    #     display_deceased_address = raw_deceased_address or "未登録"
    #     if building:
    #         if display_deceased_address != "未登録":
    #             display_deceased_address += f" ({building})"
    #         else:
    #             display_deceased_address = f"建物名: {building}"

        # building = deceased_address_info.get("building_name", "")
        # if building:
        #     if display_deceased_address != "未登録":
        #         display_deceased_address += f" ({building})"
        #     else:
        #         display_deceased_address = f"建物名: {building}"  # 住所がない場合は建物名のみ表示

    if deceased and not is_new_client_case:
        full_name = f"{deceased.name_last} {deceased.name_first}"
        dob_date_obj = deceased.date_of_birth
        if dob_date_obj:
            seireki_dob = dob_date_obj.strftime("%Y/%m/%d")
            wareki_dob = convert_seireki_to_wareki(dob_date_obj)
            dob_display_str = f"{seireki_dob} ({wareki_dob})"
        else:
            dob_display_str = "未登録"

        dod_date_obj = deceased.date_of_death
        if dod_date_obj:
            seireki_dod = dod_date_obj.strftime("%Y/%m/%d")
            wareki_dod = convert_seireki_to_wareki(dod_date_obj)
            dod_display_str = f"{seireki_dod} ({wareki_dod})"
        else:
            dod_display_str = "未登録"

    elif is_new_client_case or is_new_deceased or deceased is None:
        # 新規登録の場合のロジック (DetachedInstanceError対策で一つのブロックにまとめる)
        full_name = "【未登録】新規登録が必要です"
        dob_str = "N/A"
        dod_str = "N/A"
        # モーダルを開くためにダミーのオブジェクトを使用
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
                "heirs": [],
                "case": None,  # case属性をダミーに追加
                "case_id": None,  # case_id属性をダミーに追加
            },
        )()
        # caseオブジェクトもNoneに設定
        case = None

    heirs_controls = Column()

    path_field = TextField(
        label="フォルダ保存パス",
        width=1000,
        read_only=False,
        value="",
    )

    def save_path_on_blur(e):
        """TextFieldからフォーカスが外れたとき、またはFilePickerからパスが返されたときに実行"""

        current_input = path_field.value.strip()

        if current_input == "パス設定をキャンセルしました":
            return

        if case and case.case_id:
            path_to_save = current_input if current_input else None

            if path_to_save != deceased_service.get_case_folder_path(case.case_id):
                success = deceased_service.update_case_folder_path(
                    case_id=case.case_id,
                    folder_path=path_to_save,
                )

                if success:
                    page.open(
                        SnackBar(
                            content=Text("フォルダパスを更新しました。", color=Colors.WHITE),
                            bgcolor=Colors.BLUE_700,
                            duration=1500,
                        )
                    )
                else:
                    page.open(
                        SnackBar(
                            content=Text(
                                "エラー: フォルダパスの保存に失敗しました。",
                                color=Colors.WHITE,
                            ),
                            bgcolor=Colors.RED_700,
                            duration=3000,
                        )
                    )

        page.update()

    # --- FilePicker 結果ハンドラ ---
    def get_directory_result_detail(e: FilePickerResultEvent):
        path_field.value = e.path if e.path else "パス設定をキャンセルしました"
        save_path_on_blur(e)
        page.update()
        # new_path = dialog_path_field.value.strip()
        # if case and new_path != "パス設定をキャンセルしました":
        #     update_case_folder_path(case.case_id, new_path or None)
        #     page.open(
        #         SnackBar(
        #             content=Text("フォルダパスを保存しました。", color=Colors.WHITE),
        #             bgcolor=Colors.GREEN_700,
        #             duration=1500,
        #         )
        #     )

        # page.update()

    # フォルダ選択ダイアログを開く
    def open_folder_dialog_detail(e):
        file_picker.on_result = get_directory_result_detail
        file_picker.get_directory_path(dialog_title="案件フォルダの保存先を選択")

    path_field.on_blur = lambda e: save_path_on_blur(e)

    # --- 案件削除確認ダイアログの定義 ---
    def create_delete_confirm_dialog(case_num: str):
        """案件削除の確認ダイアログ"""

        def confirm_delete_case(e):
            """削除サービスを呼び出し、削除後にトップ画面に戻る"""
            try:
                # 案件番号を渡して削除を実行
                success = deceased_service.delete_case_and_all_related_data(case_num)
                if success:
                    print(f"案件 {case_num} の削除が完了しました。")
                    page.go("/")  # 成功したらトップ画面に戻る
                else:
                    # 削除失敗の通知 (実際にはSnackbarなどを使うべき)
                    page.open(
                        SnackBar(
                            content=Text(
                                f"案件 {case_num} の削除に失敗しました。",
                                color=Colors.WHITE,
                            ),
                            bgcolor=Colors.RED_700,
                            duration=2000,
                        )
                    )
                    print(f"案件 {case_num} の削除に失敗しました。")
            except Exception as ex:
                print(f"削除処理中に予期せぬエラー: {ex}")
                page.oepn(
                    SnackBar(
                        content=Text(f"削除中にエラーが発生しました: {ex}", color=Colors.WHITE),
                        bgcolor=Colors.RED_700,
                        duration=2000,
                    )
                )

            # ダイアログを閉じる
            delete_confirm_dialog.open = False
            page.update()

        # 💡 キャンセルボタンの動作を定義
        def close_delete_dialog(e):
            delete_confirm_dialog.open = False
            page.update()

        delete_confirm_dialog = AlertDialog(
            modal=True,
            title=Text("案件削除の確認", weight=FontWeight.BOLD, color=Colors.RED_700),
            content=Text(
                f"案件番号 {case_num} に紐づく全ての情報（被相続人、相続人、財産、タスク等）を完全に削除します。よろしいですか？",
                size=14,
            ),
            actions=[
                TextButton("キャンセル", on_click=close_delete_dialog),
                ElevatedButton(
                    "完全に削除",
                    on_click=confirm_delete_case,
                    color=Colors.WHITE,
                    bgcolor=Colors.RED_600,
                ),
            ],
            actions_alignment=MainAxisAlignment.END,
        )
        return delete_confirm_dialog

    # --- 担当者専用モーダル定義 ---
    def create_assignment_dialog():
        """担当者情報のみを編集するためのモーダル"""

        return AlertDialog(
            modal=True,
            title=Text("案件担当者 編集", weight=FontWeight.BOLD),
            content=Container(
                content=Column(
                    [
                        Text(
                            f"案件番号: {case.case_number if case else 'N/A'}",
                            weight=FontWeight.W_500,
                        ),
                        Divider(),
                        Row([dialog_manager_field, dialog_operator_field]),
                    ],
                    tight=True,
                    spacing=15,
                ),
                width=450,  # 幅を調整
                height=200,  # 高さを調整
            ),
            actions=[
                TextButton("キャンセル", on_click=lambda e: close_dialog()),
                ElevatedButton("保存", on_click=lambda e: save_assignment_dialog(), data="submit"),
            ],
            actions_alignment=MainAxisAlignment.END,
        )

    assignment_edit_dialog = create_assignment_dialog()

    # 💡 案件削除確認ダイアログを生成
    delete_confirm_dialog = create_delete_confirm_dialog(case.case_number if case else "N/A")

    # --- モーダル制御関数 (担当者編集のみ有効) ---
    def close_dialog():
        if assignment_edit_dialog.open:
            assignment_edit_dialog.open = False
            page.update()

    # # 案件削除確認ダイアログを開く関数
    # def open_delete_confirm_dialog(e):
    #     page.open(delete_confirm_dialog)
    #     page.update()

    # 担当者情報保存ロジック
    def save_assignment_dialog():
        if not case:
            print("⚠️ 案件情報がないため、担当者を保存できません。")
            close_dialog()
            return

        def _get_id_from_dropdown(value):
            if value is None or value in ("", "None", "未割当"):
                return None

            try:
                return int(value)
            except ValueError:
                # 想定外の文字列が来た場合はエラーを回避し、Noneを返す（またはログを出力）
                print(f"Warning: Attempted to convert invalid value to int: {value}")
                return None

        manager_id = _get_id_from_dropdown(dialog_manager_field.value)
        operator_id = _get_id_from_dropdown(dialog_operator_field.value)
        new_path = dialog_path_field.value.strip()

        # 1. 担当者情報の更新
        update_case_assignment(
            case_id=case.case_id,
            manager_id=manager_id,
            operator_id=operator_id,
        )

        # 2. フォルダパスの更新
        if new_path != "パス設定をキャンセルしました":
            update_case_folder_path(case.case_id, new_path or None)

        close_dialog()

        # 3. ライブアップデート: caseオブジェクトとUI表示を更新
        case.manager_id = manager_id
        case.operator_id = operator_id

        # UI上の担当者フィールドを更新 (manager_field, operator_field は後で定義されているため、ここでは値の更新のみ)
        # manager_field.value = ... (更新ロジックはUI定義後に実行されることを期待)
        # operator_field.value = ...

        page.update()  # UI全体を再描画

    def open_assignment_dialog(e):
        """担当者編集モーダルを開く"""
        if not case:
            page.oepn(
                SnackBar(
                    content=Text(
                        "⚠️ 案件情報がないため、担当者を編集できません。",
                        color=Colors.WHITE,
                    ),
                    bgcolor=Colors.RED_700,
                    duration=2000,
                )
            )
            page.update()
            return

        # 現在の値でドロップダウンを初期化
        dialog_manager_field.value = str(case.manager_id) if case.manager_id else ""
        dialog_operator_field.value = str(case.operator_id) if case.operator_id else ""

        # モーダルを開く
        page.open(assignment_edit_dialog)
        page.update()

    def _on_mount(e):
        if is_new_client_case or is_new_deceased:
            # 💡 新規案件登録モード (-1) の場合、自動で /deceased_edit/-1 に遷移
            if is_new_client_case:
                page.go("/deceased_edit/-1")

            # 💡 単独新規被相続人登録モード (0) の場合、自動で /deceased_edit/0 に遷移
            elif is_new_deceased:
                page.go("/deceased_edit/0")

        page.update()

    # --- 新しいページ遷移関数 ---

    def go_to_deceased_edit_page(e):
        """被相続人編集ページに遷移する"""
        # DeceasedEditViewは Deceased IDを期待するため、deceased.id を渡す。
        #    - 新規案件の場合は -1 を渡す (Case IDと同じ値で処理)
        id_to_pass = deceased.id if deceased else case_id
        page.go(f"/deceased_edit/{id_to_pass}")

    def go_to_new_heir_page(e):
        """新しい相続人追加ページに遷移する"""
        # HeirEditViewに渡す Deceased ID を取得
        id_to_pass = deceased.id if deceased else case_id
        page.go(f"/heir_edit/new?deceased_id={id_to_pass}")

    def go_to_heir_edit_page(e):
        """既存の相続人編集ページに遷移する"""
        heir_id = e.control.data
        # HeirEditViewに渡す Deceased ID を取得
        id_to_pass = deceased.id if deceased else case_id
        page.go(f"/heir_edit/{heir_id}?deceased_id={id_to_pass}")

    # --- 相続人リストの表示ロジック ---
    def update_heirs_list():
        heirs_controls.controls.clear()
        current_deceased = deceased_service.get_deceased_by_id(deceased_id)

        if current_deceased is None or not current_deceased.heirs:
            page.update()
            return

        if case:
            current_path = deceased_service.get_case_folder_path(case.case_id) or ""
            path_field.value = current_path
        else:
            path_field.value = ""

        for heir in current_deceased.heirs:
            heir_full_name = f"{heir.name_last} {heir.name_first}"

            # 契約者マークを追加するロジック
            is_contracting = getattr(heir, "is_contracting_party", False)  # 💡 契約者フラグを取得
            contract_mark = "【契約者】" if is_contracting else ""

            # 連絡先情報を取得
            contacts = deceased_service.get_contact_info("heir", heir.id)
            # 住所情報を取得
            address_info = deceased_service.get_address_info("heir", heir.id)

            # 電話番号の整形
            primary_phone = "N/A"
            # UIで選択肢がないため、保存時に設定される "Primary" をまず探す
            priority_sub_types = ["Primary", "携帯", "自宅"]

            for sub_type in priority_sub_types:
                found_phone = next(
                    (
                        c["value"]
                        for c in contacts
                        if c["type"] == "PHONE" and c["sub_type"] == sub_type
                    ),
                    None,
                )
                if found_phone:
                    primary_phone = found_phone
                    break

            # 優先度の高いものがなければ、最初に見つかった電話番号を採用
            if primary_phone == "N/A":
                found_any_phone = next((c["value"] for c in contacts if c["type"] == "PHONE"), None)
                if found_any_phone:
                    primary_phone = found_any_phone

            if primary_phone == "N/A":
                display_phone_value = "未登録"
            else:
                display_phone_value = primary_phone

            # 主要な住所を結合して表示
            addr_parts = [
                address_info.get("prefecture", ""),
                address_info.get("city_ward_town", ""),
                address_info.get("street_address", ""),
            ]
            raw_address = "".join(filter(None, addr_parts))
            primary_address = raw_address or "未登録"

            building = address_info.get("building_name", "")
            if building:
                primary_address += f" ({building})"

            display_relationship = heir.relationship_type.strip() if heir.relationship_type else ""
            if not display_relationship:
                display_relationship = "未登録"

            phone_display_text = f"電話: {display_phone_value}"
            address_display_text = f"住所: {primary_address}"

            heirs_controls.controls.append(
                Row(
                    [
                        Text(f"ID:{heir.id}", width=50),
                        # 氏名 (クリックでコピー)
                        Container(
                            content=Text(
                                f"名前: {heir_full_name} {contract_mark}",
                                width=200,  # 氏名表示の幅を調整
                                # color=Colors.BLUE_800
                                # if heir_full_name.strip()
                                # else Colors.BLACK,
                            ),
                            # 氏名に on_click を設定
                            on_click=lambda e, name=heir_full_name: copy_to_clipboard_and_notify(
                                e, page, name.strip()
                            ),
                            data=heir_full_name.strip(),
                            tooltip="クリックして氏名をコピー",
                        ),
                        Text(f"続柄: {display_relationship}", width=100),
                        # ★ 電話番号 (クリックでコピー) ★
                        Container(
                            content=Text(
                                phone_display_text,
                                width=150,  # 電話番号表示の幅を広げる
                                size=12,
                                # color=Colors.BLUE_GREY_600,
                            ),
                            on_click=lambda e, phone=primary_phone: copy_to_clipboard_and_notify(
                                e, page, phone
                            ),
                            data=primary_phone,
                            tooltip="クリックして電話番号をコピー",
                        ),
                        # スペーサー（電話と住所を区切る）
                        Container(width=10),
                        # ★ 住所 (クリックでコピー) ★
                        Container(
                            content=Text(
                                address_display_text,
                                width=350,  # 住所表示の幅を調整
                                size=12,
                                # color=Colors.BLUE_GREY_600,
                            ),
                            on_click=lambda e, addr=raw_address: copy_to_clipboard_and_notify(
                                e, page, addr
                            ),
                            data=raw_address,
                            tooltip="クリックして住所をコピー",
                        ),
                        IconButton(
                            Icons.EDIT,
                            icon_color=Colors.BLUE_500,
                            data=heir.id,
                            on_click=go_to_heir_edit_page,  # 関数名を変更
                            tooltip="相続人を編集 (別ページへ遷移)",
                        ),
                        IconButton(
                            Icons.DELETE,
                            icon_color=Colors.RED_500,
                            data=heir.id,
                            on_click=lambda e, name=heir_full_name: open_heir_delete_confirm(
                                e, heir.id, name
                            ),
                        ),
                    ],
                    alignment=MainAxisAlignment.START,
                )
            )
        page.update()

    # --- 削除ダイアログ制御関数 ---
    def open_heir_delete_confirm(e, heir_id_to_delete: int, heir_full_name: str):
        """相続人削除確認ダイアログを表示し、コールバックを設定する"""

        def perform_delete(e):
            """削除サービスを実行するコールバック関数"""
            try:
                deceased_service.delete_heir(heir_id_to_delete)
                page.open(
                    SnackBar(
                        content=Text(
                            f"{heir_full_name} さんの情報を削除しました。",
                            color=Colors.WHITE,
                        ),
                        bgcolor=Colors.GREEN_700,
                        duration=1500,
                    )
                )
                update_heirs_list()
            except Exception as ex:
                print(f"相続人削除エラー: {ex}")
                page.open(
                    SnackBar(
                        content=Text(f"削除中にエラーが発生しました: {ex}", color=Colors.WHITE),
                        bgcolor=Colors.RED_700,
                        duration=3000,
                    )
                )

        show_confirm_dialog(
            page=page,
            title="相続人削除の確認",
            message=f"【{heir_full_name}】の相続人情報を削除します。この操作は元に戻せません。よろしいですか？",
            confirm_text="削除する",
            on_confirm=perform_delete,
            confirm_color=Colors.RED_600,
        )

    # 初期リストの表示
    if not is_new_deceased and not is_new_client_case:
        update_heirs_list()

    # # 案件削除確認ダイアログを開く関数
    # def open_delete_confirm_dialog(e):
    #     page.open(delete_confirm_dialog)
    #     page.update()

    # 担当者1の表示
    manager_field = Text(
        # caseがNone、またはmanager_idがNoneの場合は「未割当」を表示
        f"担当1 (進捗): {USER_MAP.get(case.manager_id, '未割当')}"
        if case is not None and case.manager_id is not None
        else "担当1 (進捗): 未割当",
        size=14,
        width=250,
    )

    operator_field = Text(
        # caseがNone、またはoperator_idがNoneの場合は「未割当」を表示
        f"担当2 (実務): {USER_MAP.get(case.operator_id, '未割当')}"
        if case is not None and case.operator_id is not None
        else "担当2 (実務): 未割当",
        size=14,
        width=250,
    )

    # View の定義
    view_controls = [
        AppBar(title=Text("被相続人 詳細/相続人管理"), bgcolor=Colors.BLUE_GREY_700),
        Container(
            content=Column(
                [
                    # 💡 案件番号表示セクション 💡
                    Container(
                        content=Column(
                            [
                                Row(
                                    [
                                        Text(
                                            f"案件番号: {case.case_number if case and case.case_number else 'N/A (未登録)'}",
                                            size=18,
                                            weight=FontWeight.BOLD,
                                            color=Colors.DEEP_ORANGE_600,  # 案件番号を目立たせる色に変更
                                        ),
                                        ElevatedButton(
                                            "案件を完全に削除",
                                            on_click=lambda e: page.open(delete_confirm_dialog),
                                            icon=Icons.DELETE_FOREVER,
                                            icon_color=Colors.RED,
                                            style=ButtonStyle(bgcolor=Colors.RED_100),
                                        ),
                                    ],
                                    alignment=MainAxisAlignment.SPACE_BETWEEN,
                                    vertical_alignment=CrossAxisAlignment.CENTER,
                                ),
                                Divider(
                                    height=10, color=Colors.TRANSPARENT
                                ),  # 案件番号と担当者情報を少し離す
                                # 💡 担当者情報表示 (被相続人情報の上に移動) 💡
                                Row(
                                    [
                                        Text(
                                            "👥 担当者情報",
                                            size=18,
                                            weight=FontWeight.BOLD,
                                        ),
                                        # 💡 編集ボタンを追加 💡
                                        IconButton(
                                            Icons.EDIT,
                                            icon_color=Colors.BLUE_500,
                                            tooltip="案件担当者を編集",
                                            on_click=open_assignment_dialog,
                                        ),
                                    ],
                                    alignment=MainAxisAlignment.START,
                                ),
                                Row(
                                    [
                                        # 担当者1の表示
                                        manager_field,
                                        # Text(
                                        #     # caseがNone、またはmanager_idがNoneの場合は「未割当」を表示
                                        #     f"担当1 (進捗): {USER_MAP.get(case.manager_id, '未割当')}"
                                        #     if case is not None
                                        #     and case.manager_id is not None
                                        #     else "担当1 (進捗): 未割当",
                                        #     size=14,
                                        #     width=250,
                                        # ),
                                        # 担当者2の表示
                                        operator_field,
                                        # Text(
                                        #     # caseがNone、またはoperator_idがNoneの場合は「未割当」を表示
                                        #     f"担当2 (実務): {USER_MAP.get(case.operator_id, '未割当')}"
                                        #     if case is not None
                                        #     and case.operator_id is not None
                                        #     else "担当2 (実務): 未割当",
                                        #     size=14,
                                        #     width=250,
                                        # ),
                                    ],
                                    alignment=MainAxisAlignment.START,
                                ),
                            ]
                        ),
                        # 新規案件モード（-1）または単独新規被相続人モード（0）以外で、case情報がある場合に表示
                        visible=not is_new_client_case and not is_new_deceased and case is not None,
                    ),
                    Divider(
                        visible=not is_new_client_case and not is_new_deceased and case is not None
                    ),
                    # 被相続人情報
                    Row(
                        [
                            Text(
                                # "👤 被相続人情報 ✏️ ",
                                "👤 被相続人情報",
                                size=18,
                                weight=FontWeight.BOLD,
                            ),
                            Text(
                                "【新規登録モード】",
                                size=16,
                                color=Colors.RED_500,
                                visible=is_new_deceased or is_new_client_case,
                            ),
                            IconButton(
                                Icons.EDIT,
                                icon_color=Colors.BLUE_500,
                                tooltip="被相続人を編集 (別ページへ遷移)",
                                on_click=go_to_deceased_edit_page,  # 関数名を変更
                            ),
                        ]
                    ),
                    Row(
                        [
                            Container(
                                content=Text(
                                    f"名前: {full_name}",
                                    weight=FontWeight.BOLD,
                                    size=16,
                                    width=200,
                                ),
                                on_click=lambda e, content=full_name: copy_to_clipboard_and_notify(
                                    e, page, content
                                ),
                                tooltip="クリックして氏名をコピー",
                            ),
                            Column(
                                [
                                    # 西暦のみ
                                    Container(
                                        content=Text(
                                            f"生年月日（西暦）: {dob_date_obj.isoformat() if dob_date_obj else '未登録'}",
                                            size=14,
                                            width=250,  # 幅を調整
                                        ),
                                        on_click=lambda e,
                                        content=(
                                            dob_date_obj.isoformat() if dob_date_obj else "未登録"
                                        ): copy_to_clipboard_and_notify(e, page, content),
                                        tooltip="クリックして西暦をコピー",
                                    ),
                                    Text(
                                        f"生年月日（和暦）: {convert_seireki_to_wareki(dob_date_obj) if dob_date_obj else '未登録'}",
                                        size=12,
                                        color=Colors.BLUE_GREY_600,
                                    ),
                                ],
                                spacing=2,
                            ),
                            Column(
                                [
                                    # 西暦のみ
                                    Container(
                                        content=Text(
                                            f"死亡日（西暦）: {dod_date_obj.isoformat() if dod_date_obj else '未登録'}",
                                            size=14,
                                            width=250,  # 幅を調整
                                        ),
                                        on_click=lambda e,
                                        content=(
                                            dod_date_obj.isoformat() if dod_date_obj else "未登録"
                                        ): copy_to_clipboard_and_notify(e, page, content),
                                        tooltip="クリックして西暦をコピー",
                                    ),
                                    # 和暦のみ
                                    Text(
                                        f"死亡日（和暦）: {convert_seireki_to_wareki(dod_date_obj) if dod_date_obj else '未登録'}",
                                        size=12,
                                        color=Colors.BLUE_GREY_600,
                                    ),
                                ],
                                spacing=2,
                            ),
                        ],
                        alignment=MainAxisAlignment.START,
                    ),
                    Row(
                        [
                            Container(
                                content=Text(
                                    f"最後の住所: {display_deceased_address}",
                                    size=14,
                                    width=600,
                                ),
                                # 住所のコピー機能を追加
                                on_click=lambda e,
                                content=copyable_full_address: copy_to_clipboard_and_notify(
                                    e, page, content
                                ),
                                tooltip="クリックして現住所をコピー",
                            ),
                            # 必要に応じて本籍地なども追加可能
                        ],
                        alignment=MainAxisAlignment.START,
                        visible=not is_new_client_case
                        and not is_new_deceased,  # 新規登録モード以外で表示
                    ),
                    Divider(),
                    # 相続人リスト
                    Column(
                        [
                            Row(
                                [
                                    Text(
                                        "👨‍👩‍👧‍👦 相続人リスト",
                                        size=16,
                                    ),
                                    # 💡 新しい相続人追加ボタン 💡
                                    ElevatedButton(
                                        "新しい相続人を追加",
                                        icon=Icons.ADD,
                                        on_click=go_to_new_heir_page,  # 関数名を変更
                                    ),
                                ],
                                # alignment=MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=CrossAxisAlignment.CENTER,
                            ),
                            Container(
                                content=heirs_controls,
                                border=border.all(1, Colors.BLACK12),
                                padding=10,
                                width=page.width * 0.8,
                            ),
                        ],
                        # 新規案件モード（-1）または単独新規被相続人モード（0）では非表示
                        visible=not is_new_deceased and not is_new_client_case,
                    ),
                    Divider(),
                    Container(
                        content=Column(
                            [
                                Text(
                                    "📁 案件フォルダ保存パス (OSネイティブ設定)",
                                    weight=FontWeight.BOLD,
                                    size=18,
                                ),
                                Row(
                                    [
                                        path_field,
                                        ElevatedButton(
                                            "フォルダ選択",
                                            icon=Icons.FOLDER_OPEN,
                                            on_click=open_folder_dialog_detail,
                                        ),
                                    ]
                                ),
                                Text(
                                    "※フォルダを選択するとパスが即座に保存されます。",
                                    size=12,
                                    color=Colors.BLUE_GREY_400,
                                ),
                            ]
                        ),
                        width=page.width * 0.8,
                        visible=case is not None,  # 案件情報がある場合のみ表示
                    ),
                    Divider(),
                    Row(
                        [
                            ElevatedButton("👈 一覧へ戻る", on_click=lambda e: page.go("/")),
                        ],
                        spacing=20,
                    ),
                ],
                horizontal_alignment=CrossAxisAlignment.START,
            ),
            padding=20,
        ),
    ]

    # --- View表示時の初期化処理 ---
    def on_view_show_handler(e):
        """Viewが表示されるたびに実行され、データ表示とパス初期化を行う"""
        page.update()

        # 新規登録モードの場合は自動遷移
        if is_new_client_case:
            page.go("/deceased_edit/-1")
            return
        elif is_new_deceased:
            page.go("/deceased_edit/0")
            return

        # 既存/登録済みの場合の処理
        if not is_new_deceased and not is_new_client_case:
            # 相続人リストの更新
            update_heirs_list()

        # 💡 パスフィールドの初期値を設定
        if case:
            current_path = deceased_service.get_case_folder_path(case.case_id) or ""
            path_field.value = current_path
        else:
            path_field.value = ""

        page.update()
        # page.update()
        # update_heirs_list()

        # # 💡 パスフィールドの初期値を設定
        # if case:
        #     current_path = get_case_folder_path(case.case_id) or ""
        #     path_field.value = current_path
        # else:
        #     path_field.value = ""
        # page.update()

    view = View(
        f"/detail/{case_id}",
        view_controls,
        scroll=ScrollMode.AUTO,
    )

    view.on_view_show = on_view_show_handler

    # ページがマウントされた時に自動でモーダルを開く設定
    # view.on_view_show = _on_mount

    # # 初期リストの表示 (新規の場合、heirs_controlsは空のまま)
    # if not is_new_deceased and not is_new_client_case:
    #     update_heirs_list()

    return view
