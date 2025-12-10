# src/views/detail.py

import threading
import time
import os
import tkinter as tk
from tkinter import messagebox

import pyperclip
from flet import (
    AlertDialog,
    ButtonStyle,
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    Dropdown,
    ElevatedButton,
    FilePicker,
    FilePickerResultEvent,
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
    border,
    dropdown,
)

from src.services.deceased_service import (
    delete_case_and_all_related_data,
    delete_heir,
    get_address_info,
    get_address_string_parts,
    get_all_users,
    get_case_by_id,
    get_case_folder_path,
    get_contact_info,
    get_deceased_by_case_id,
    get_deceased_by_id,
    get_kintone_integration_data,
    update_case_assignment,
    update_case_folder_path,
    update_case_number,
)
from src.utils.date_utils import (
    convert_seireki_to_wareki,
)


USER_MAP = {}
try:
    USER_MAP = get_all_users()
except Exception as e:
    print(f"User load error: {e}")

USER_OPTIONS = [dropdown.Option(str(id), name) for id, name in USER_MAP.items()]
USER_OPTIONS.insert(0, dropdown.Option("", "未割当"))

# 担当者フィールド
dialog_manager_field = Dropdown(
    label="担当者1 (進捗管理)", width=200, options=USER_OPTIONS, value=""
)
dialog_operator_field = Dropdown(
    label="担当者2 (実務担当)", width=200, options=USER_OPTIONS, value=""
)


def launch_kintone_automation(case_id: int):
    kintone_data = get_kintone_integration_data(case_id)
    if not kintone_data:
        print("エラー: データが見つかりませんでした")
        return

    load_dotenv()
    KINTONE_USER = os.getenv("KINTONE_USER")
    KINTONE_PASS = os.getenv("KINTONE_PASS")

    message = (
        "Kintone自動化を開始しますか？\n\n"
        f"案件番号: {kintone_data.get('case_number')}\n"
        f"依頼者: {kintone_data.get('client_name')}\n"
        f"被相続人: {kintone_data.get('deceased_name')}\n\n"
        "※ [OK]を押すと、クリップボードに案件番号がコピーされます。"
    )

    if messagebox.askokcancel("Kintone連携", message):
        pyperclip.copy(kintone_data.get("case_number", ""))
        print(f"Kintone automation launched for case {case_id}")
    root.destroy()


def copy_to_clipboard_and_notify(e, page: Page, content: str):
    text_to_copy = content.strip()
    if not text_to_copy or text_to_copy == "N/A" or text_to_copy == "未登録":
        return
    page.set_clipboard(text_to_copy)
    page.open(
        SnackBar(
            content=Text(f"'{text_to_copy[:30]}' をコピーしました。", color=Colors.ON_INVERSE_SURFACE),
            bgcolor=Colors.INVERSE_SURFACE,
            duration=1500,
        )
    )
    page.update()


def DeceasedDetailView(page: Page, case_id: int) -> View:
    # --- UI 初期化 ---
    file_picker = FilePicker(on_result=lambda e: page.update())
    if file_picker not in page.overlay:
        page.overlay.append(file_picker)

    # データの取得
    case = get_case_by_id(case_id)
    # ケースIDから被相続人を取得（存在しない場合はNone）
    deceased = get_deceased_by_case_id(case_id)

    is_new_client_case = case_id == -1
    is_new_deceased = case_id == 0
    # 被相続人IDの特定（新規の場合は0または-1）
    deceased_id = deceased.id if deceased else case_id

    # 💡 新規作成モードの場合のリダイレクト処理
    if is_new_client_case:
        page.run_thread(lambda: page.go("/deceased_edit/-1"))
        return View(f"/detail/{case_id}", controls=[]) # リダイレクト中に表示する空のView

    if is_new_deceased:
        page.run_thread(lambda: page.go("/deceased_edit/0"))
        return View(f"/detail/{case_id}", controls=[]) # リダイレクト中に表示する空のView

    # ユーザーリストの取得（リロードごとに最新化）
    user_map = get_all_users()
    user_options = [dropdown.Option(str(uid), name) for uid, name in user_map.items()]
    user_options.insert(0, dropdown.Option("", "未割当"))

    # 担当者ドロップダウン定義
    dialog_manager_field = Dropdown(
        label="担当者1 (進捗管理)",
        width=200,
        options=user_options,
        value="",
    )
    dialog_operator_field = Dropdown(
        label="担当者2 (実務担当)", 
        width=200, 
        options=user_options, 
        value=""
    )

    # 最後の住所取得
    last_address = None
    if deceased and deceased.last_address_id:
        last_address = get_address_by_id(deceased.last_address_id)

    # 被相続人 住所表示ロジック
    deceased_zip_code = "〒未登録"
    deceased_full_address = "未登録"

    if deceased and deceased.last_address_id:
        zip_res, addr_res = get_address_string_parts(deceased.last_address_id)
        deceased_zip_code = zip_res
        deceased_full_address = addr_res

    if last_address:
        address_parts = [
            last_address.prefecture,
            last_address.city_ward_town,
            last_address.street_address,
        ]
        raw_deceased_address = "".join(filter(None, address_parts))
        building = last_address.building_name if last_address.building_name else ""
        zip_code = last_address.zip_code if last_address.zip_code else ""
        deceased_zip_code = f"〒{zip_code}"

        if raw_deceased_address:
            display_deceased_address = raw_deceased_address
            if building:
                display_deceased_address += f" ({building})"
        elif building:
            display_deceased_address = f"建物名: {building}"

        copyable_full_address = (
            f"〒{zip_code} {raw_deceased_address} {building}" if raw_deceased_address else "未登録"
        ).strip()

    # 案件オブジェクトの再確認（被相続人経由で取得できている場合）
    case = deceased.case if deceased and deceased.case else case

    # 表示用文字列の生成
    if deceased and not is_new_client_case:
        full_name = f"{deceased.name_last} {deceased.name_first}"
        dob_display = (
            f"{deceased.date_of_birth} ({convert_seireki_to_wareki(deceased.date_of_birth)})"
            if deceased.date_of_birth
            else "未登録"
        )
        dod_display = (
            f"{deceased.date_of_death} ({convert_seireki_to_wareki(deceased.date_of_death)})"
            if deceased.date_of_death
            else "未登録"
        )
    else:
        full_name = "【未登録】"
        dob_display = "N/A"
        dod_display = "N/A"
        deceased = type(
            "Dummy",
            (object,),
            {
                "id": 0,
                "name_last": "",
                "name_first": "",
                "name_last_kana": "",
                "name_first_kana": "",
                "date_of_birth": None,
                "date_of_death": None,
                "relationship_type": "本人",
                "hometown": "",
                "heirs": [],
                "case": None,
                "case_id": None,
                "last_address_id": None,
                "last_address": None,
            },
        )()

    # --- 案件番号インライン編集ロジック ---
    case_number_container = Container()
    edit_case_number_field = TextField(
        label="案件番号", width=200, height=40, content_padding=10, text_size=14, autofocus=True
    )

    # --- 案件番号インライン編集用のコンテナとロジック ---
    case_number_container = Container()

    # 編集用フィールド
    edit_case_number_field = TextField(
        label="案件番号", width=200, height=40, content_padding=10, text_size=14, autofocus=True
    )

    def save_case_number_inline(e):
        """インライン編集の保存処理"""
        new_num = edit_case_number_field.value.strip()
        if not new_num:
            page.open(SnackBar(Text("案件番号は必須です"), bgcolor=Colors.RED))
            return

        if case and update_case_number(case.case_id, new_num):
            page.open(SnackBar(Text("案件番号を更新しました"), bgcolor=Colors.GREEN))
            # メモリ上のオブジェクトも更新して表示モードへ
            case.case_number = new_num
            render_view_mode()
        else:
            page.open(
                SnackBar(Text("更新失敗: この案件番号は既に使用されています"), bgcolor=Colors.RED)
            )
            page.update()

    def render_edit_mode(e=None):
        """編集モードのUIを表示"""
        if not case:
            return
        edit_case_number_field.value = case.case_number

        case_number_container.content = Row(
            [
                edit_case_number_field,
                IconButton(
                    icon=Icons.CHECK,
                    icon_color=Colors.GREEN,
                    tooltip="保存",
                    on_click=save_case_number_inline,
                ),
                IconButton(
                    icon=Icons.CLOSE,
                    icon_color=Colors.RED,
                    tooltip="キャンセル",
                    on_click=lambda _: render_view_mode(),
                ),
            ],
            alignment=MainAxisAlignment.START,
            vertical_alignment=CrossAxisAlignment.CENTER,
        )

        # 修正: ページに追加されている場合のみ update() を呼ぶ
        if case_number_container.page:
            case_number_container.update()

    def render_view_mode(e=None):
        """表示モードのUIを表示"""
        current_num = case.case_number if case else "New"

        case_number_container.content = Row(
            [
                Container(
                    content=Text(
                        f"案件番号: {current_num}",
                        size=22,
                        weight=FontWeight.BOLD,
                        color=Colors.ORANGE_400,
                    ),
                    on_click=lambda e: copy_to_clipboard_and_notify(e, page, current_num),
                    tooltip="クリックしてコピー",
                ),
                IconButton(
                    icon=Icons.EDIT,
                    icon_color=Colors.ORANGE_400,
                    tooltip="案件番号を編集",
                    on_click=render_edit_mode,
                ),
            ],
            alignment=MainAxisAlignment.START,
            vertical_alignment=CrossAxisAlignment.CENTER,
        )

        # 修正: ページに追加されている場合のみ update() を呼ぶ
        if case_number_container.page:
            case_number_container.update()

    # 初期表示モード設定 (ここではまだページに追加されていないため update() は呼ばれない)
    render_view_mode()

    # --- フォルダパス保存ロジック ---
    def save_path_on_blur(e):
        current = path_field.value.strip()
        if case and current:
            saved = get_case_folder_path(case.case_id)
            if current != saved:
                update_case_folder_path(case.case_id, current)
                page.open(SnackBar(Text("パスを更新しました"), bgcolor=Colors.BLUE_700))
        page.update()

    def save_path_on_event(e):
        """BlurやSubmitから呼び出されるイベントハンドラ"""
        save_path_logic(path_field.value.strip())

    path_field.on_blur = save_path_on_event
    path_field.on_submit = save_path_on_event # Enterキーでも保存
    
    def open_folder_dialog_detail(e):
        # フォルダ選択後に即時保存
        def on_result(e: FilePickerResultEvent):
            if e.path:
                path_field.value = e.path
                save_path_logic(e.path) # 保存と正規化を実行
                page.update()
        
        file_picker.on_result = on_result
        file_picker.get_directory_path(dialog_title="案件フォルダの保存先を選択")

    # --- 削除確認ダイアログ ---
    def create_delete_confirm_dialog(case_num: str):
        def confirm_delete_case(e):
            if delete_case_and_all_related_data(case_num):
                page.go("/")
            else:
                page.open(SnackBar(Text("削除処理に失敗しました"), bgcolor=Colors.ERROR))
            delete_confirm_dialog.open = False
            page.update()

        delete_confirm_dialog = AlertDialog(
            modal=True,
            title=Text("案件削除の確認", weight=FontWeight.BOLD, color=Colors.ERROR),
            content=Text(f"案件 {case_num} を完全に削除しますか？\n被相続人、相続人、タスクなど全ての情報が削除され、元に戻せません。"),
            actions=[
                TextButton("キャンセル", on_click=close_delete),
                ElevatedButton(
                    "削除", on_click=confirm_delete_case, bgcolor=Colors.RED, color=Colors.WHITE
                ),
            ],
        )
        return delete_confirm_dialog

    delete_confirm_dialog = create_delete_confirm_dialog(case.case_number if case else "N/A")

    # --- 担当者編集用ダイアログ ---
    def create_assignment_dialog():
        return AlertDialog(
            modal=True,
            title=Text("案件担当者 編集"),
            content=Container(
                content=Column(
                    [
                        Text(f"案件: {case.case_number if case else 'N/A'}"),
                        dialog_manager_field,
                        dialog_operator_field,
                    ],
                    tight=True,
                ),
                height=200,
            ),
            actions=[
                TextButton("キャンセル", on_click=lambda e: close_dialog()),
                ElevatedButton("保存", on_click=lambda e: save_assignment()),
            ],
        )

    assignment_edit_dialog = create_assignment_dialog()

    def close_dialog():
        assignment_edit_dialog.open = False
        page.update()

    def save_assignment_dialog():
        if not case: return close_dialog()
        
        m_id = int(dialog_manager_field.value) if dialog_manager_field.value else None
        o_id = int(dialog_operator_field.value) if dialog_operator_field.value else None
        
        update_case_assignment(case.case_id, m_id, o_id)
        
        # メモリ更新
        case.manager_id = m_id
        case.operator_id = o_id
        
        close_dialog()
        page.open(SnackBar(Text("担当者情報を更新しました"), bgcolor=Colors.GREEN))
        page.update()

    def open_assignment_dialog(e):
        if not case:
            return
        dialog_manager_field.value = str(case.manager_id) if case.manager_id else ""
        dialog_operator_field.value = str(case.operator_id) if case.operator_id else ""
        page.open(assignment_edit_dialog)
        page.update()

    def save_assignment():
        if not case:
            return
        m_id = int(dialog_manager_field.value) if dialog_manager_field.value else None
        o_id = int(dialog_operator_field.value) if dialog_operator_field.value else None
        update_case_assignment(case.case_id, m_id, o_id)
        close_dialog()
        page.open(SnackBar(Text("更新しました"), bgcolor=Colors.GREEN))

    def close_dialog():
        if page.dialog:
            page.dialog.open = False
            page.update()

    def update_heirs_list():
        heirs_controls.controls.clear()
        current_deceased = get_deceased_by_id(deceased.id) if deceased.id > 0 else None
        if not current_deceased or not current_deceased.heirs:
            return

        for heir in current_deceased.heirs:
            heir_name = f"{heir.name_last} {heir.name_first}"
            mark = "【契約者】" if getattr(heir, "is_contracting_party", False) else ""
            
            # 連絡先・住所取得ロジック
            contacts = get_contact_info("heir", heir.id)
            address_info = get_address_info("heir", heir.id)
            
            # 電話番号 (優先順位: 携帯 > 自宅 > その他)
            phone = "未登録"
            for sub in ["Primary", "携帯", "自宅"]:
                found = next((c["value"] for c in contacts if c["type"] == "PHONE" and c["sub_type"] == sub), None)
                if found:
                    phone = found
                    break
            if phone == "未登録":
                found = next((c["value"] for c in contacts if c["type"] == "PHONE"), None)
                if found: phone = found
            
            # メールアドレス
            email = "未登録"
            email_found = next((c["value"] for c in contacts if c["type"] == "EMAIL"), None)
            if email_found: email = email_found

            # 住所・郵便番号
            zip_code = address_info.get("zip_code", "")
            zip_display = f"〒{zip_code}" if zip_code else "〒未登録"
            
            addr_str = f"{address_info.get('prefecture', '')}{address_info.get('city_ward_town', '')}{address_info.get('street_address', '')}"
            if address_info.get("building_name"):
                addr_str += f" ({address_info.get('building_name')})"
            
            full_addr_display = f"{zip_display} {addr_str}".strip() if addr_str else "未登録"

            # 相続人の住所取得
            heir_zip_code = "〒未登録"
            heir_full_address = "未登録"

            addr_info = get_address_info("heir", heir.id)
            if addr_info:
                heir_zip_code = f"〒{addr_info.get('zip_code', '未登録')}"
                raw = f"{addr_info.get('prefecture', '')}{addr_info.get('city_ward_town', '')}{addr_info.get('street_address', '')}"
                bldg = addr_info.get("building_name", "")
                heir_full_address = f"{raw} {bldg}".strip()

            # 相続人リストの行構成
            heirs_controls.controls.append(
                Row(
                    [
                        # 氏名
                        Container(
                            content=Text(f"{name} {mark}", width=160, weight=FontWeight.BOLD),
                            on_click=lambda e, t=name: copy_to_clipboard_and_notify(e, page, t),
                            tooltip="クリックしてコピー",
                        ),
                        Text(heir.relationship_type or "-", width=60),
                        # 郵便番号
                        Container(
                            content=Text(heir_zip_code, width=100, color=Colors.BLUE_700),
                            on_click=lambda e, t=heir_zip_code: copy_to_clipboard_and_notify(
                                e, page, t
                            ),
                            tooltip="郵便番号をコピー",
                        ),
                        # 住所
                        Container(
                            content=Text(
                                heir_full_address,
                                width=250,
                                no_wrap=True,
                                overflow="ellipsis",
                                color=Colors.BLUE_700,
                            ),
                            on_click=lambda e, t=heir_full_address: copy_to_clipboard_and_notify(
                                e, page, t
                            ),
                            tooltip="住所をコピー",
                        ),
                        Container(
                            content=Text(f"Tel: {phone}", width=140, size=13),
                            on_click=lambda e, t=phone: copy_to_clipboard_and_notify(e, page, t),
                        ),
                        IconButton(
                            Icons.EDIT,
                            icon_color="primary",
                            on_click=lambda e, hid=heir.id: page.go(
                                f"/heir_edit/{hid}?deceased_id={current_deceased.id}"
                            ),
                        ),
                        IconButton(
                            Icons.DELETE,
                            icon_color="error",
                            on_click=lambda e, hid=heir.id: delete_heir_handler(hid),
                        ),
                    ],
                    vertical_alignment=CrossAxisAlignment.CENTER,
                )
            )
        page.update()

    def open_heir_delete_confirm(heir_id, name):
        def perform_delete(e):
            delete_heir(heir_id)
            update_heirs_list()
            page.open(SnackBar(Text(f"{name} さんの情報を削除しました"), bgcolor=Colors.GREEN))

        show_confirm_dialog(page, "相続人削除", f"【{name}】の情報を削除しますか？\nこの操作は元に戻せません。", "削除", perform_delete, Colors.ERROR)

    # 画面描画時にデータを最新化
    if not is_new_deceased and not is_new_client_case:
        update_heirs_list()
        
    if case: 
        # 💡 初期表示時にも正規化されたパスを表示
        normalized_path = get_case_folder_path(case.case_id)
        path_field.value = normalized_path or ""

    # --- View Main Structure ---
    return View(
        f"/detail/{case_id}",
        [
            Container(
                content=Column(
                    [
                        # ヘッダー (案件番号インライン編集を含む)
                        Row(
                            [
                                case_number_container,  # インライン編集コンテナを配置
                                Row(
                                    [
                                        ElevatedButton(
                                            "Kintone連携",
                                            icon=Icons.CLOUD_UPLOAD,
                                            on_click=lambda e: launch_kintone_automation(
                                                case.case_id
                                            )
                                            if case
                                            else None,
                                            style=ButtonStyle(
                                                bgcolor=Colors.AMBER_900, color=Colors.WHITE
                                            ),
                                        ),
                                        Container(width=10),
                                        ElevatedButton(
                                            "案件削除",
                                            icon=Icons.DELETE_FOREVER,
                                            style=ButtonStyle(
                                                bgcolor=Colors.RED_900, color=Colors.WHITE
                                            ),
                                            on_click=lambda e: page.open(delete_confirm_dialog)
                                            if case
                                            else None,
                                        ),
                                    ]
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        Divider(height=10, color=Colors.TRANSPARENT),
                        # 担当者
                        Row(
                            [
                                Text("👥 担当者情報", size=16, weight=FontWeight.BOLD),
                                IconButton(
                                    Icons.EDIT,
                                    icon_color="primary",
                                    on_click=open_assignment_dialog,
                                ),
                            ]
                        ),
                        Row(
                            [
                                Text(
                                    f"担当1: {USER_MAP.get(case.manager_id, '未割当')}"
                                    if case
                                    else "-",
                                    width=200,
                                ),
                                Text(
                                    f"担当2: {USER_MAP.get(case.operator_id, '未割当')}"
                                    if case
                                    else "-",
                                    width=200,
                                ),
                            ]
                        ),
                        Divider(color="outlineVariant"),
                        # 被相続人
                        Row(
                            [
                                Text("👤 被相続人情報", size=18, weight=FontWeight.BOLD),
                                IconButton(
                                    Icons.EDIT,
                                    icon_color="primary",
                                    on_click=lambda e: page.go(f"/deceased_edit/{deceased.id}")
                                    if deceased.id > 0
                                    else None,
                                ),
                            ]
                        ),
                        Row(
                            [
                                Container(
                                    content=Text(
                                        f"氏名: {full_name}", size=16, weight=FontWeight.BOLD
                                    ),
                                    on_click=lambda e: copy_to_clipboard_and_notify(
                                        e, page, full_name
                                    ),
                                ),
                                Text(f"生年月日: {dob_display}"),
                                Text(f"死亡日: {dod_display}"),
                            ],
                            spacing=20,
                        ),
                        # 被相続人 住所表示 (郵便番号分離)
                        Row(
                            [
                                Text("住所:", weight=FontWeight.BOLD),
                                Container(
                                    content=Text(
                                        deceased_zip_code,
                                        color=Colors.BLUE_700,
                                        weight=FontWeight.BOLD,
                                    ),
                                    on_click=lambda e: copy_to_clipboard_and_notify(
                                        e, page, deceased_zip_code
                                    ),
                                    tooltip="郵便番号をコピー",
                                ),
                                Container(
                                    content=Text(deceased_full_address, color=Colors.BLUE_700),
                                    on_click=lambda e: copy_to_clipboard_and_notify(
                                        e, page, deceased_full_address
                                    ),
                                    tooltip="住所をコピー",
                                ),
                            ],
                            spacing=10,
                        ),
                        Divider(color="outlineVariant"),
                        # 相続人リスト
                        Row(
                            [
                                Text("👨‍👩‍👧‍👦 相続人リスト", size=18, weight=FontWeight.BOLD),
                                ElevatedButton(
                                    "追加",
                                    icon=Icons.ADD,
                                    on_click=lambda e: page.go(
                                        f"/heir_edit/new?deceased_id={deceased.id}"
                                    )
                                    if deceased.id > 0
                                    else None,
                                    bgcolor="primary",
                                    color="onPrimary",
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        # 相続人コンテナ
                        Container(content=heirs_controls, padding=5),
                        Divider(color="outlineVariant"),
                        # フォルダパス
                        Text("📁 案件フォルダ保存パス", weight=FontWeight.BOLD),
                        Row(
                            [
                                path_field,
                                IconButton(Icons.FOLDER, on_click=open_folder_dialog_detail),
                            ]
                        ),
                        Divider(color="outlineVariant"),
                        ElevatedButton("👈 一覧へ戻る", on_click=lambda e: page.go("/")),
                    ]
                ),
                padding=20,
                border_radius=10,
                border=border.all(1, "outlineVariant"),
            )
        ],
        scroll=ScrollMode.AUTO,
    )
