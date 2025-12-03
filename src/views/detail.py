# src/views/detail.py
import tkinter as tk
from tkinter import messagebox
import pyperclip

from flet import (
    AlertDialog,
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
    TextStyle,
    dropdown,
    ButtonStyle,
    border,
)

from src.utils.date_utils import (
    convert_seireki_to_wareki,
    parse_all_flexible_date,
    on_date_blur_handler,
)
from src.utils.ui_utils import show_confirm_dialog

# 💡 修正: インポートパスを新しいディレクトリ構成 (src.components.business) に変更
from src.components.business.contact_controls import (
    add_new_contact_row,
    collect_contacts,
    create_contact_input_row,
    add_initial_contact_rows,
)

from src.services.deceased_service import (
    get_all_users,
    get_address_by_id,
    get_address_info,
    get_case_by_id,
    get_case_folder_path,
    get_case_id_by_deceased_id,
    get_contact_info,
    get_deceased_by_case_id,
    get_deceased_by_id,
    get_kintone_integration_data,
    update_case_assignment,
    update_case_folder_path,
    update_deceased,
    delete_case_and_all_related_data,
    delete_heir,
    search_address_by_zip_api,
)

# --- グローバルな UI 定義 ---

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

# --- モーダル編集フィールド定義 ---
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
wareki_dob_text = Text(value="", width=250, color="onSurfaceVariant", weight=FontWeight.W_500) # 修正
dialog_dob_field.on_blur = lambda e: on_date_blur_handler(e, wareki_dob_text)

dialog_dod_field = TextField(label="死亡日 (YYYY-MM-DD)", width=180)
wareki_dod_text = Text(value="", width=250, color="onSurfaceVariant", weight=FontWeight.W_500) # 修正
dialog_dod_field.on_blur = lambda e: on_date_blur_handler(e, wareki_dod_text)

dialog_title_control = Text("情報編集", weight=FontWeight.BOLD)
dialog_case_number_field = TextField(label="案件番号", width=250)


def launch_kintone_automation(case_id: int):
    kintone_data = get_kintone_integration_data(case_id)
    if not kintone_data:
        print("エラー: データが見つかりませんでした")
        return

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

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
    if not text_to_copy or text_to_copy == "N/A":
        return
    page.set_clipboard(text_to_copy)
    page.open(
        SnackBar(
            content=Text(f"'{text_to_copy[:30]}' をコピーしました。", color=Colors.WHITE),
            bgcolor=Colors.BLUE_GREY_700,
            duration=1500,
        )
    )
    page.update()


def DeceasedDetailView(page: Page, case_id: int):
    file_picker = FilePicker(on_result=lambda e: page.update())
    if file_picker not in page.overlay:
        page.overlay.append(file_picker)

    case = get_case_by_id(case_id)
    deceased = get_deceased_by_case_id(case_id)

    is_new_client_case = case_id == -1
    is_new_deceased = case_id == 0
    deceased_id = deceased.id if deceased else (0 if is_new_deceased else -1)

    display_deceased_address = "未登録"
    copyable_full_address = "未登録"
    if deceased and deceased.last_address_id:
        last_address = get_address_by_id(deceased.last_address_id)
        if last_address:
            raw = f"{last_address.prefecture}{last_address.city_ward_town}{last_address.street_address}"
            building = last_address.building_name or ""
            display_deceased_address = f"{raw} ({building})" if building else raw
            copyable_full_address = f"〒{last_address.zip_code} {raw} {building}".strip()

    if deceased and not is_new_client_case:
        full_name = f"{deceased.name_last} {deceased.name_first}"
        dob_display = f"{deceased.date_of_birth} ({convert_seireki_to_wareki(deceased.date_of_birth)})" if deceased.date_of_birth else "未登録"
        dod_display = f"{deceased.date_of_death} ({convert_seireki_to_wareki(deceased.date_of_death)})" if deceased.date_of_death else "未登録"
    else:
        full_name = "【未登録】"
        dob_display = "N/A"
        dod_display = "N/A"
        deceased = type("Dummy", (object,), {
            "id": 0, "name_last": "", "name_first": "", "name_last_kana": "", "name_first_kana": "",
            "date_of_birth": None, "date_of_death": None, "relationship_type": "本人", "hometown": "",
            "heirs": [], "case": None, "case_id": None, "last_address_id": None, "last_address": None
        })()

    heirs_controls = Column()
    path_field = TextField(label="フォルダ保存パス", width=600, value="")

    def save_path_on_blur(e):
        current = path_field.value.strip()
        if case and current:
            saved = get_case_folder_path(case.case_id)
            if current != saved:
                update_case_folder_path(case.case_id, current)
                page.open(SnackBar(Text("パスを更新しました"), bgcolor=Colors.BLUE_700))
        page.update()

    path_field.on_blur = save_path_on_blur

    def get_directory_result(e: FilePickerResultEvent):
        if e.path:
            path_field.value = e.path
            save_path_on_blur(e)
            page.update()

    def open_folder_dialog_detail(e):
        file_picker.on_result = get_directory_result
        file_picker.get_directory_path("保存先を選択")

    def create_delete_confirm_dialog(case_num: str):
        def confirm_delete_case(e):
            if delete_case_and_all_related_data(case_num):
                page.go("/")
            else:
                page.open(SnackBar(Text("削除に失敗しました"), bgcolor=Colors.RED))
            delete_confirm_dialog.open = False
            page.update()

        def close_delete(e):
            delete_confirm_dialog.open = False
            page.update()

        delete_confirm_dialog = AlertDialog(
            modal=True,
            title=Text("案件削除確認", color=Colors.RED),
            content=Text(f"案件 {case_num} を完全に削除しますか？"),
            actions=[
                TextButton("キャンセル", on_click=close_delete),
                ElevatedButton("削除", on_click=confirm_delete_case, bgcolor=Colors.RED, color=Colors.WHITE)
            ]
        )
        return delete_confirm_dialog

    delete_confirm_dialog = create_delete_confirm_dialog(case.case_number if case else "N/A")

    def create_assignment_dialog():
        return AlertDialog(
            modal=True,
            title=Text("担当者編集"),
            content=Container(
                content=Column([
                    Text(f"案件: {case.case_number if case else 'N/A'}"),
                    dialog_manager_field,
                    dialog_operator_field
                ], tight=True),
                height=200
            ),
            actions=[
                TextButton("キャンセル", on_click=lambda e: close_dialog()),
                ElevatedButton("保存", on_click=lambda e: save_assignment())
            ]
        )
    
    assignment_edit_dialog = create_assignment_dialog()

    def open_assignment_dialog(e):
        if not case: return
        dialog_manager_field.value = str(case.manager_id) if case.manager_id else ""
        dialog_operator_field.value = str(case.operator_id) if case.operator_id else ""
        page.dialog = assignment_edit_dialog
        assignment_edit_dialog.open = True
        page.update()

    def save_assignment():
        if not case: return
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
        if not current_deceased or not current_deceased.heirs: return

        for heir in current_deceased.heirs:
            name = f"{heir.name_last} {heir.name_first}"
            mark = "【契約者】" if getattr(heir, "is_contracting_party", False) else ""
            contacts = get_contact_info("heir", heir.id)
            phone = next((c["value"] for c in contacts if c["type"] == "PHONE"), "未登録")

            heirs_controls.controls.append(
                Row([
                    Text(f"ID:{heir.id}", width=40, color="outline"), # 修正
                    Container(
                        content=Text(f"{name} {mark}", width=200, weight=FontWeight.BOLD),
                        on_click=lambda e, t=name: copy_to_clipboard_and_notify(e, page, t),
                        tooltip="クリックしてコピー"
                    ),
                    Text(heir.relationship_type or "-", width=80),
                    Container(
                        content=Text(f"Tel: {phone}", width=150, size=13),
                        on_click=lambda e, t=phone: copy_to_clipboard_and_notify(e, page, t),
                    ),
                    IconButton(Icons.EDIT, icon_color="primary", on_click=lambda e, hid=heir.id: page.go(f"/heir_edit/{hid}?deceased_id={current_deceased.id}")), # 修正
                    IconButton(Icons.DELETE, icon_color="error", on_click=lambda e, hid=heir.id: delete_heir_handler(hid)) # 修正
                ], vertical_alignment=CrossAxisAlignment.CENTER)
            )
        page.update()

    def delete_heir_handler(hid):
        delete_heir(hid)
        update_heirs_list()
        page.open(SnackBar(Text("削除しました"), bgcolor=Colors.RED))

    if not is_new_deceased and not is_new_client_case:
        update_heirs_list()
        if case:
            path_field.value = get_case_folder_path(case.case_id) or ""

    # UI構築
    return Column(
        controls=[
            Container(
                content=Column([
                    # ヘッダー
                    Row([
                        Container(
                            content=Text(f"案件番号: {case.case_number if case else 'New'}", size=22, weight=FontWeight.BOLD, color=Colors.ORANGE_400),
                            on_click=lambda e: copy_to_clipboard_and_notify(e, page, case.case_number if case else "")
                        ),
                        Row([
                            ElevatedButton("Kintone連携", icon=Icons.CLOUD_UPLOAD, on_click=lambda e: launch_kintone_automation(case.case_id) if case else None, style=ButtonStyle(bgcolor=Colors.AMBER_900, color=Colors.WHITE)),
                            Container(width=10),
                            ElevatedButton("案件削除", icon=Icons.DELETE_FOREVER, style=ButtonStyle(bgcolor=Colors.RED_900, color=Colors.WHITE), on_click=lambda e: page.open(delete_confirm_dialog) if case else None)
                        ])
                    ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                    
                    Divider(height=10, color=Colors.TRANSPARENT),
                    
                    # 担当者
                    Row([Text("👥 担当者情報", size=16, weight=FontWeight.BOLD), IconButton(Icons.EDIT, icon_color="primary", on_click=open_assignment_dialog)]), # 修正
                    Row([
                        Text(f"担当1: {USER_MAP.get(case.manager_id, '未割当')}" if case else "-", width=200),
                        Text(f"担当2: {USER_MAP.get(case.operator_id, '未割当')}" if case else "-", width=200),
                    ]),

                    Divider(color="outlineVariant"), # 修正

                    # 被相続人
                    Row([
                        Text("👤 被相続人情報", size=18, weight=FontWeight.BOLD),
                        IconButton(Icons.EDIT, icon_color="primary", on_click=lambda e: page.go(f"/deceased_edit/{deceased.id}") if deceased.id > 0 else None) # 修正
                    ]),
                    Row([
                        Container(content=Text(f"氏名: {full_name}", size=16, weight=FontWeight.BOLD), on_click=lambda e: copy_to_clipboard_and_notify(e, page, full_name)),
                        Text(f"生年月日: {dob_display}"),
                        Text(f"死亡日: {dod_display}"),
                    ], spacing=20),
                    Container(content=Text(f"住所: {display_deceased_address}"), on_click=lambda e: copy_to_clipboard_and_notify(e, page, copyable_full_address)),

                    Divider(color="outlineVariant"), # 修正

                    # 相続人リスト
                    Row([
                        Text("👨‍👩‍👧‍👦 相続人リスト", size=18, weight=FontWeight.BOLD),
                        ElevatedButton("追加", icon=Icons.ADD, on_click=lambda e: page.go(f"/heir_edit/new?deceased_id={deceased.id}") if deceased.id > 0 else None, bgcolor="primary", color="onPrimary"), # 修正
                    ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                    heirs_controls,

                    Divider(color="outlineVariant"), # 修正

                    # フォルダパス
                    Text("📁 案件フォルダ保存パス", weight=FontWeight.BOLD),
                    Row([path_field, IconButton(Icons.FOLDER, on_click=open_folder_dialog_detail)]),
                    
                    Divider(color="outlineVariant"), # 修正
                    ElevatedButton("👈 一覧へ戻る", on_click=lambda e: page.go("/")),
                ]),
                padding=20,
                border_radius=10,
                border=border.all(1, "outlineVariant") # 修正
            )
        ],
        scroll=ScrollMode.AUTO
    )