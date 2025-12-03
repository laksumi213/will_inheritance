# components/pages/detail.py

import threading
import time
import os
from datetime import datetime

# 自動化用ライブラリ
import pyautogui
import pyperclip
# import keyboard

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv
import tkinter as tk
from tkinter import messagebox

from flet import (
    AlertDialog,
    AppBar,
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
    View,
    border,
    dropdown,
    ButtonStyle,
)

from components.utils.date_utils import convert_seireki_to_wareki
from components.utils.ui_utils import show_confirm_dialog
from components.utils.contact_controls import (
    add_new_contact_row,
    collect_contacts,
    create_contact_input_row,
)
from services import deceased_service

# 💡 修正: db_setup からのインポートを排除し、deceased_service に集約
from services.deceased_service import (
    get_all_users,         # 💡 ここからインポートするように修正
    get_address_by_id,
    parse_all_flexible_date,
    update_case_assignment,
    update_case_folder_path,
)

# --- グローバルな UI 定義 ---

USER_MAP = get_all_users()
USER_OPTIONS = [dropdown.Option(str(id), name) for id, name in USER_MAP.items()]
USER_OPTIONS.insert(0, dropdown.Option("", "未割当"))

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
    input_value = e.control.value
    wareki_text.value = ""

    if not input_value:
        e.control.error_text = None
        wareki_text.update()
        e.control.update()
        return

    try:
        validated_date = parse_all_flexible_date(input_value)
        e.control.value = validated_date.isoformat()
        e.control.error_text = None
        wareki_text.value = convert_seireki_to_wareki(validated_date)

    except ValueError:
        e.control.error_text = "無効な日付形式です"
        wareki_text.value = ""

    wareki_text.update()
    e.control.update()


# --- モーダル編集で使用するフィールド定義 ---
dialog_name_last_field = TextField(label="氏名 (姓)", width=150, autofocus=True)
dialog_name_first_field = TextField(label="氏名 (名)", width=150)
dialog_kana_last_field = TextField(label="ふりがな (姓)", width=150)
dialog_kana_first_field = TextField(label="ふりがな (名)", width=150)
dialog_rel_field = TextField(label="続柄", width=200)

dialog_hometown_field = TextField(label="本籍地")
dialog_zip_field = TextField(label="郵便番号", width=150)
dialog_pref_field = TextField(label="都道府県", width=150)
dialog_city_field = TextField(label="市区町村", width=200)
dialog_street_field = TextField(label="番地", width=150)
dialog_building_field = TextField(label="建物名・部屋番号")

phone_inputs_column = Column(controls=[], spacing=5)
email_inputs_column = Column(controls=[], spacing=5)

dialog_dob_field = TextField(label="生年月日 (YYYY-MM-DD)", width=180)
wareki_dob_text = Text(value="", width=250, color=Colors.BLUE_GREY_600, weight=FontWeight.W_500)
dialog_dob_field.on_blur = lambda e: on_date_blur_handler(e, wareki_dob_text)

dialog_dod_field = TextField(label="死亡日 (YYYY-MM-DD)", width=180)
wareki_dod_text = Text(value="", width=250, color=Colors.BLUE_GREY_600, weight=FontWeight.W_500)
dialog_dod_field.on_blur = lambda e: on_date_blur_handler(e, wareki_dod_text)

dialog_title_control = Text("情報編集", weight=FontWeight.BOLD)
dialog_case_number_field = TextField(label="案件番号", width=250)


# ---------------------------------------------
# 💡 Kintone 自動化ロジック (PyAutoGUI版)
# ---------------------------------------------
def launch_kintone_automation(case_id: int):
    """
    Kintoneへのデータ自動入力ロジック。
    実際にはPyAutoGUIなどを使ってWebブラウザを操作する想定ですが、
    ここでは取得したデータを確認するダイアログを表示します。
    """
    
    # DBからKintone連携用データを取得
    kintone_data = deceased_service.get_kintone_integration_data(case_id)
    
    if not kintone_data:
        print("エラー: データが見つかりませんでした")
        return

    # 取得したデータ
    case_number = kintone_data.get("case_number")
    client_name = kintone_data.get("client_name")
    deceased_name = kintone_data.get("deceased_name")

    # デモとして、取得したデータをコンソールに表示
    print("--- Kintone連携データ ---")
    print(f"案件番号: {case_number}")
    print(f"依頼者名: {client_name}")
    print(f"被相続人: {deceased_name}")
    print("-------------------------")

    # 実際の自動化ロジックの代わりに、確認メッセージボックスを表示 (Tkinter使用)
    root = tk.Tk()
    root.withdraw()  # メインウィンドウを隠す
    root.attributes("-topmost", True) # 最前面に表示

    message = (
        "Kintone自動化を開始しますか？\n\n"
        f"案件番号: {case_number}\n"
        f"依頼者: {client_name}\n"
        f"被相続人: {deceased_name}\n\n"
        "※ [OK]を押すと、クリップボードに案件番号がコピーされます。"
    )
    
    if messagebox.askokcancel("Kintone連携", message):
        # 案件番号をクリップボードにコピー
        pyperclip.copy(case_number)
        print(f"Kintone automation launched for case {case_id} (Clipboard copied)")
    
    root.destroy()


def copy_to_clipboard_and_notify(e, page: Page, content: str):
    """クリックされたテキストをクリップボードにコピーし、SnackBarで通知する"""
    text_to_copy = content.strip()
    if not text_to_copy or text_to_copy == "N/A":
        return

    page.set_clipboard(text_to_copy)

    page.open(
        SnackBar(
            content=Text(
                f"'{text_to_copy[:30].strip()}' をクリップボードにコピーしました。📋",
                color=Colors.WHITE,
            ),
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
    # 💡 修正: Case ID から Deceased を取得
    deceased = deceased_service.get_deceased_by_case_id(case_id)

    is_new_client_case = case_id == -1
    is_new_deceased = case_id == 0
    # Deceased IDを特定（新規モード以外）
    deceased_id = deceased.id if deceased else case_id

    # 最後の住所情報を取得
    last_address = None
    if deceased and deceased.last_address_id:
        last_address = get_address_by_id(deceased.last_address_id)

    display_deceased_address = "未登録"
    copyable_full_address = "未登録"

    if last_address:
        address_parts = [
            last_address.prefecture,
            last_address.city_ward_town,
            last_address.street_address,
        ]
        raw_deceased_address = "".join(filter(None, address_parts))
        building = last_address.building_name if last_address.building_name else ""
        zip_code = last_address.zip_code if last_address.zip_code else ""

        if raw_deceased_address:
            display_deceased_address = raw_deceased_address
            if building:
                display_deceased_address += f" ({building})"
        elif building:
            display_deceased_address = f"建物名: {building}"
        else:
            display_deceased_address = "未登録"

        copyable_full_address = (
            f"〒{zip_code} {raw_deceased_address} {building}" if raw_deceased_address else "未登録"
        ).strip()

    # 案件情報を取得
    case = deceased.case if deceased and deceased.case else None

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
        full_name = "【未登録】新規登録が必要です"
        dob_display_str = "N/A"
        dod_display_str = "N/A"
        # ダミーオブジェクト
        deceased = type(
            "DummyDeceased",
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
            },
        )()
        case = None

    heirs_controls = Column()

    path_field = TextField(
        label="フォルダ保存パス",
        width=1000,
        read_only=False,
        value="",
    )

    def save_path_on_blur(e):
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

    def get_directory_result_detail(e: FilePickerResultEvent):
        path_field.value = e.path if e.path else "パス設定をキャンセルしました"
        save_path_on_blur(e)
        page.update()

    def open_folder_dialog_detail(e):
        file_picker.on_result = get_directory_result_detail
        file_picker.get_directory_path(dialog_title="案件フォルダの保存先を選択")

    path_field.on_blur = lambda e: save_path_on_blur(e)

    def create_delete_confirm_dialog(case_num: str):
        def confirm_delete_case(e):
            try:
                success = deceased_service.delete_case_and_all_related_data(case_num)
                if success:
                    print(f"案件 {case_num} の削除が完了しました。")
                    page.go("/")
                else:
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
            except Exception as ex:
                page.open(
                    SnackBar(
                        content=Text(f"削除中にエラーが発生しました: {ex}", color=Colors.WHITE),
                        bgcolor=Colors.RED_700,
                        duration=2000,
                    )
                )
            delete_confirm_dialog.open = False
            page.update()

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

    def create_assignment_dialog():
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
                width=450,
                height=200,
            ),
            actions=[
                TextButton("キャンセル", on_click=lambda e: close_dialog()),
                ElevatedButton("保存", on_click=lambda e: save_assignment_dialog(), data="submit"),
            ],
            actions_alignment=MainAxisAlignment.END,
        )

    assignment_edit_dialog = create_assignment_dialog()
    delete_confirm_dialog = create_delete_confirm_dialog(case.case_number if case else "N/A")

    # --- 共通モーダル定義 (詳細画面から簡易編集する場合) ---
    def create_edit_dialog(is_deceased: bool):
        # 続柄フィールドは被相続人（本人）の場合は表示しない
        rel_row = Row([dialog_rel_field])
        if is_deceased:
            rel_row.visible = False

        date_rows = [
            Row(
                [dialog_dob_field, wareki_dob_text],
                spacing=10,
                vertical_alignment=CrossAxisAlignment.END,
            )
        ]
        if is_deceased:
            date_rows.append(
                Row(
                    [dialog_dod_field, wareki_dod_text],
                    spacing=10,
                    vertical_alignment=CrossAxisAlignment.END,
                )
            )

        # 案件番号フィールド
        case_num_row = Row([dialog_case_number_field])

        # 担当者選択フィールド
        assignment_row = Row([dialog_manager_field, dialog_operator_field])

        if is_deceased:
            assignment_row.visible = is_new_client_case
        elif is_new_client_case:
            assignment_row.visible = True
        else:
            assignment_row.visible = False

        def on_submit_handler(e):
            save_dialog(is_deceased)

        dialog_building_field.on_submit = on_submit_handler
        dialog_hometown_field.on_submit = on_submit_handler
        dialog_case_number_field.on_submit = on_submit_handler

        save_button = ElevatedButton(
            "保存", on_click=lambda e: save_dialog(is_deceased), data="submit"
        )

        return AlertDialog(
            modal=True,
            title=dialog_title_control,
            content=Container(
                content=Column(
                    [
                        Divider(),
                        case_num_row,
                        assignment_row,
                        Divider(),
                        Text("基本情報", weight=FontWeight.BOLD),
                        Row([dialog_name_last_field, dialog_name_first_field]),
                        Row([dialog_kana_last_field, dialog_kana_first_field]),
                        Divider(),
                        Text("連絡先情報", weight=FontWeight.BOLD),
                        Row(
                            [
                                Text("📞 電話番号", size=14, weight=FontWeight.W_500),
                                IconButton(
                                    Icons.ADD,
                                    icon_color=Colors.BLUE_500,
                                    on_click=lambda e: add_new_contact_row(
                                        e, phone_inputs_column, is_email=False
                                    ),
                                    tooltip="電話番号を追加",
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                            width=550,
                        ),
                        phone_inputs_column,
                        Row(
                            [
                                Text(
                                    "📧 メールアドレス",
                                    size=14,
                                    weight=FontWeight.W_500,
                                ),
                                IconButton(
                                    Icons.ADD,
                                    icon_color=Colors.BLUE_500,
                                    on_click=lambda e: add_new_contact_row(
                                        e, email_inputs_column, is_email=True
                                    ),
                                    tooltip="メールアドレスを追加",
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                            width=550,
                        ),
                        email_inputs_column,
                        Divider(),
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
                save_button,
            ],
            actions_alignment=MainAxisAlignment.END,
        )

    if is_new_client_case == -1:
        heir_edit_dialog = create_edit_dialog(is_deceased=True)
        deceased_edit_dialog = create_edit_dialog(is_deceased=False)
    else:
        heir_edit_dialog = create_edit_dialog(is_deceased=False)
        deceased_edit_dialog = create_edit_dialog(is_deceased=True)

    def close_dialog():
        if assignment_edit_dialog.open:
            assignment_edit_dialog.open = False
        elif deceased_edit_dialog.open:
            deceased_edit_dialog.open = False
        elif heir_edit_dialog.open:
            heir_edit_dialog.open = False
        
        page.update()
        
        # モーダルを閉じたら画面更新
        # ただし、新規登録モーダルの場合はトップへ
        if heir_edit_dialog.data == "NEW_CLIENT_CASE":
             page.go("/")
        else:
             # リロード
             update_heirs_list()
             page.update()

    def save_assignment_dialog():
        if not case:
            return

        def _get_id_from_dropdown(value):
            if value is None or value in ("", "None", "未割当"):
                return None
            try:
                return int(value)
            except ValueError:
                return None

        manager_id = _get_id_from_dropdown(dialog_manager_field.value)
        operator_id = _get_id_from_dropdown(dialog_operator_field.value)
        
        update_case_assignment(
            case_id=case.case_id,
            manager_id=manager_id,
            operator_id=operator_id,
        )
        close_dialog()
        case.manager_id = manager_id
        case.operator_id = operator_id
        page.update()

    def open_assignment_dialog(e):
        if not case:
            page.open(
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

        dialog_manager_field.value = str(case.manager_id) if case.manager_id else ""
        dialog_operator_field.value = str(case.operator_id) if case.operator_id else ""
        page.open(assignment_edit_dialog)
        page.update()

    def go_to_deceased_edit_page(e):
        # 💡 Case ID ではなく、Deceased ID を渡す (存在すれば)
        # 存在しなければ Case ID を渡すが、詳細画面が表示されている時点で Deceased は必ず存在するはず (Dummy含む)
        id_to_pass = deceased.id if deceased and deceased.id > 0 else case_id
        page.go(f"/deceased_edit/{id_to_pass}")

    def go_to_new_heir_page(e):
        id_to_pass = deceased.id if deceased and deceased.id > 0 else case_id
        page.go(f"/heir_edit/new?deceased_id={id_to_pass}")

    def go_to_heir_edit_page(e):
        heir_id = e.control.data
        id_to_pass = deceased.id if deceased and deceased.id > 0 else case_id
        page.go(f"/heir_edit/{heir_id}?deceased_id={id_to_pass}")

    def update_heirs_list():
        heirs_controls.controls.clear()
        
        # 💡 IDで再取得せず、現在の deceased オブジェクト（Eager Load済み）を使用する
        # 再取得する場合は get_deceased_by_id を使う
        current_deceased = deceased_service.get_deceased_by_id(deceased.id) if deceased and deceased.id > 0 else None

        if current_deceased is None or not current_deceased.heirs:
            page.update()
            return

        if case:
            current_path = deceased_service.get_case_folder_path(case.case_id) or ""
            path_field.value = current_path
        else:
            path_field.value = ""

        for heir in current_deceased.heirs:
            heir_full_name = f"{heir.name_last}　{heir.name_first}"
            is_contracting = getattr(heir, "is_contracting_party", False)
            contract_mark = "【契約者】" if is_contracting else ""

            contacts = deceased_service.get_contact_info("heir", heir.id)
            address_info = deceased_service.get_address_info("heir", heir.id)

            primary_phone = "N/A"
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

            if primary_phone == "N/A":
                found_any_phone = next((c["value"] for c in contacts if c["type"] == "PHONE"), None)
                if found_any_phone:
                    primary_phone = found_any_phone

            display_phone_value = "未登録" if primary_phone == "N/A" else primary_phone

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

            heirs_controls.controls.append(
                Row(
                    [
                        Text(f"ID:{heir.id}", width=50),
                        Container(
                            content=Text(
                                f"名前: {heir_full_name} {contract_mark}",
                                width=200,
                            ),
                            on_click=lambda e, name=heir_full_name: copy_to_clipboard_and_notify(
                                e, page, name.strip()
                            ),
                            data=heir_full_name.strip(),
                            tooltip="クリックして氏名をコピー",
                        ),
                        Text(f"続柄: {display_relationship}", width=100),
                        Container(
                            content=Text(f"電話: {display_phone_value}", width=150, size=12),
                            on_click=lambda e, phone=primary_phone: copy_to_clipboard_and_notify(
                                e, page, phone
                            ),
                            data=primary_phone,
                            tooltip="クリックして電話番号をコピー",
                        ),
                        Container(width=10),
                        Container(
                            content=Text(f"住所: {primary_address}", width=350, size=12),
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
                            on_click=go_to_heir_edit_page,
                            tooltip="相続人を編集",
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

    def open_heir_delete_confirm(e, heir_id_to_delete: int, heir_full_name: str):
        def perform_delete(e):
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

    if not is_new_deceased and not is_new_client_case:
        update_heirs_list()

    manager_field = Text(
        f"担当1 (進捗): {USER_MAP.get(case.manager_id, '未割当')}"
        if case is not None and case.manager_id is not None
        else "担当1 (進捗): 未割当",
        size=14,
        width=250,
    )

    operator_field = Text(
        f"担当2 (実務): {USER_MAP.get(case.operator_id, '未割当')}"
        if case is not None and case.operator_id is not None
        else "担当2 (実務): 未割当",
        size=14,
        width=250,
    )

    # --- 保存ロジック (簡易編集モーダル用) ---
    def save_dialog(is_deceased: bool):
        # 連絡先収集
        phone_contacts = collect_contacts(phone_inputs_column)
        email_contacts = collect_contacts(email_inputs_column)

        name = f"{dialog_name_last_field.value.strip()} {dialog_name_first_field.value.strip()}"
        
        # ID特定
        target_id = deceased_edit_dialog.data if is_deceased else heir_edit_dialog.data

        try:
            if is_deceased:
                deceased_service.update_deceased(
                    deceased_id=target_id, # Deceased ID
                    name_last=dialog_name_last_field.value.strip(),
                    name_first=dialog_name_first_field.value.strip(),
                    dob=dialog_dob_field.value,
                    dod=dialog_dod_field.value,
                    kana_last=dialog_kana_last_field.value.strip(),
                    kana_first=dialog_kana_first_field.value.strip(),
                    hometown=dialog_hometown_field.value.strip(),
                    last_zip_code=dialog_zip_field.value.strip(),
                    last_pref=dialog_pref_field.value.strip(),
                    last_city=dialog_city_field.value.strip(),
                    last_street=dialog_street_field.value.strip(),
                    last_building=dialog_building_field.value.strip(),
                    # 💡 連絡先を渡す
                    phone_contacts=phone_contacts,
                    email_contacts=email_contacts,
                )
            else:
                # 相続人
                if target_id is None: # 新規
                     # (簡易モーダルでは新規追加は実装していないがロジックとして)
                     pass
                else:
                    deceased_service.update_heir(
                        heir_id=target_id,
                        name=name,
                        rel=dialog_rel_field.value.strip(),
                        kana_last=dialog_kana_last_field.value.strip(),
                        kana_first=dialog_kana_first_field.value.strip(),
                        zip_code=dialog_zip_field.value.strip(),
                        pref=dialog_pref_field.value.strip(),
                        city=dialog_city_field.value.strip(),
                        street=dialog_street_field.value.strip(),
                        building=dialog_building_field.value.strip(),
                        phone_contacts=phone_contacts,
                        email_contacts=email_contacts,
                    )
            
            close_dialog()
            page.open(SnackBar(Text("保存しました"), bgcolor=Colors.GREEN))
            
            # 画面リロード
            if is_deceased:
                # ページ全体リロードが必要 (Deceasedはトップレベルの情報)
                page.go(f"/detail/{case_id}")
            else:
                update_heirs_list()

        except Exception as ex:
            print(ex)
            page.open(SnackBar(Text(f"エラー: {ex}"), bgcolor=Colors.RED))

    # 被相続人編集モーダルを開く処理
    def open_deceased_dialog(e):
        if not deceased: return
        
        deceased_edit_dialog.data = deceased.id # IDをセット
        
        dialog_title_control.value = "被相続人情報 編集"
        
        dialog_name_last_field.value = deceased.name_last
        dialog_name_first_field.value = deceased.name_first
        dialog_kana_last_field.value = deceased.name_last_kana or ""
        dialog_kana_first_field.value = deceased.name_first_kana or ""
        
        dob_date = deceased.date_of_birth
        dod_date = deceased.date_of_death
        dialog_dob_field.value = str(dob_date) if dob_date else ""
        dialog_dod_field.value = str(dod_date) if dod_date else ""
        wareki_dob_text.value = convert_seireki_to_wareki(dob_date)
        wareki_dod_text.value = convert_seireki_to_wareki(dod_date)
        
        dialog_hometown_field.value = deceased.hometown or ""
        
        # 住所
        last_addr = deceased.last_address
        if last_addr:
            dialog_zip_field.value = last_addr.zip_code or ""
            dialog_pref_field.value = last_addr.prefecture or ""
            dialog_city_field.value = last_addr.city_ward_town or ""
            dialog_street_field.value = last_addr.street_address or ""
            dialog_building_field.value = last_addr.building_name or ""
        else:
            dialog_zip_field.value = ""
            dialog_pref_field.value = ""
            dialog_city_field.value = ""
            dialog_street_field.value = ""
            dialog_building_field.value = ""

        # 連絡先
        contacts = deceased_service.get_contact_info("deceased", deceased.id)
        
        phone_contacts = [c for c in contacts if c["type"] == "PHONE"]
        phone_inputs_column.controls.clear()
        if phone_contacts:
            for c in phone_contacts:
                new_row, _ = create_contact_input_row(phone_inputs_column, initial_value=c["value"], is_email=False)
                phone_inputs_column.controls.append(new_row)
        else:
            new_row, _ = create_contact_input_row(phone_inputs_column, is_email=False)
            phone_inputs_column.controls.append(new_row)

        email_contacts = [c for c in contacts if c["type"] == "EMAIL"]
        email_inputs_column.controls.clear()
        if email_contacts:
            for c in email_contacts:
                new_row, _ = create_contact_input_row(email_inputs_column, initial_value=c["value"], is_email=True)
                email_inputs_column.controls.append(new_row)
        else:
            new_row, _ = create_contact_input_row(email_inputs_column, is_email=True)
            email_inputs_column.controls.append(new_row)

        page.open(deceased_edit_dialog)
        page.update()


    view_controls = [
        AppBar(title=Text("被相続人 詳細/相続人管理"), bgcolor=Colors.BLUE_GREY_700),
        Container(
            content=Column(
                [
                    Container(
                        content=Column(
                            [
                                Row(
                                    [
                                        Container(
                                            content=Text(
                                                f"案件番号: {case.case_number if case and case.case_number else 'N/A (未登録)'}",
                                                size=18,
                                                weight=FontWeight.BOLD,
                                            ),
                                            on_click=lambda e,
                                            content=(
                                                case.case_number
                                                if case and case.case_number
                                                else ""
                                            ): copy_to_clipboard_and_notify(e, page, content),
                                            tooltip="クリックして案件番号をコピー",
                                        ),
                                        ElevatedButton(
                                            "Kintone入力",
                                            icon=Icons.CLOUD_UPLOAD,
                                            on_click=lambda e: launch_kintone_automation(case.case_id) if case else None,
                                            style=ButtonStyle(
                                                bgcolor=Colors.AMBER_100,
                                                color=Colors.BROWN_900,
                                            ),
                                            tooltip="Kintoneを開き、詳細情報を自動入力します"
                                        ),
                                        Container(width=10),
                                        ElevatedButton(
                                            "案件を完全に削除",
                                            on_click=lambda e: page.open(delete_confirm_dialog),
                                            icon=Icons.DELETE_FOREVER,
                                            icon_color=Colors.RED,
                                            bgcolor=Colors.BLUE_50,
                                            color=Colors.BLUE_800,
                                        ),
                                    ],
                                    alignment=MainAxisAlignment.SPACE_BETWEEN,
                                    vertical_alignment=CrossAxisAlignment.CENTER,
                                ),
                                Divider(height=10, color=Colors.TRANSPARENT),
                                Row(
                                    [
                                        Text(
                                            "👥 担当者情報",
                                            size=18,
                                            weight=FontWeight.BOLD,
                                        ),
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
                                    [manager_field, operator_field],
                                    alignment=MainAxisAlignment.START,
                                ),
                            ]
                        ),
                        visible=not is_new_client_case and not is_new_deceased and case is not None,
                    ),
                    Divider(
                        visible=not is_new_client_case and not is_new_deceased and case is not None
                    ),
                    Row(
                        [
                            Text(
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
                            # 💡 編集ボタン: 別ページへ遷移する関数を呼ぶ
                            IconButton(
                                Icons.EDIT,
                                icon_color=Colors.BLUE_500,
                                tooltip="被相続人を編集 (別ページへ遷移)",
                                on_click=go_to_deceased_edit_page,
                            ),
                            # 💡 (旧) 簡易モーダル編集ボタン
                            IconButton(
                                Icons.EDIT_NOTE,
                                icon_color=Colors.TEAL_500,
                                tooltip="被相続人を編集 (簡易モーダル)",
                                on_click=open_deceased_dialog,
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
                                    Container(
                                        content=Text(
                                            f"生年月日（西暦）: {dob_date_obj.isoformat() if dob_date_obj else '未登録'}",
                                            size=14,
                                            width=250,
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
                                    Container(
                                        content=Text(
                                            f"死亡日（西暦）: {dod_date_obj.isoformat() if dod_date_obj else '未登録'}",
                                            size=14,
                                            width=250,
                                        ),
                                        on_click=lambda e,
                                        content=(
                                            dod_date_obj.isoformat() if dod_date_obj else "未登録"
                                        ): copy_to_clipboard_and_notify(e, page, content),
                                        tooltip="クリックして西暦をコピー",
                                    ),
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
                                on_click=lambda e,
                                content=copyable_full_address: copy_to_clipboard_and_notify(
                                    e, page, content
                                ),
                                tooltip="クリックして現住所をコピー",
                            ),
                        ],
                        alignment=MainAxisAlignment.START,
                        visible=not is_new_client_case and not is_new_deceased,
                    ),
                    Divider(),
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
                                        on_click=go_to_new_heir_page,
                                    ),
                                ],
                                alignment=MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=CrossAxisAlignment.CENTER,
                            ),
                            Container(
                                content=heirs_controls,
                                border=border.all(1, Colors.BLACK12),
                                padding=10,
                                width=page.width * 0.8,
                            ),
                        ],
                        visible=not is_new_deceased and not is_new_client_case,
                    ),
                    Divider(),
                    Container(
                        content=Column(
                            [
                                Text(
                                    "📁 案件フォルダ保存パス",
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
                        visible=case is not None,
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

    def on_view_show_handler(e):
        page.update()

        if is_new_client_case:
            page.go("/deceased_edit/-1")
            return
        elif is_new_deceased:
            page.go("/deceased_edit/0")
            return

        if not is_new_deceased and not is_new_client_case:
            update_heirs_list()

        if case:
            current_path = deceased_service.get_case_folder_path(case.case_id) or ""
            path_field.value = current_path
        else:
            path_field.value = ""

        page.update()

    view = View(
        f"/detail/{case_id}",
        view_controls,
        scroll=ScrollMode.AUTO,
    )

    view.on_view_show = on_view_show_handler
    return view