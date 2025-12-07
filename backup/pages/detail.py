# src/views/detail.py
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

# 案件番号編集フィールド
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
    if not text_to_copy or text_to_copy == "N/A" or text_to_copy == "未登録":
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

    # 被相続人 住所表示ロジック
    deceased_zip_code = "〒未登録"
    deceased_full_address = "未登録"

    if deceased and deceased.last_address_id:
        zip_res, addr_res = get_address_string_parts(deceased.last_address_id)
        deceased_zip_code = zip_res
        deceased_full_address = addr_res

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
                ElevatedButton(
                    "削除", on_click=confirm_delete_case, bgcolor=Colors.RED, color=Colors.WHITE
                ),
            ],
        )
        return delete_confirm_dialog

    delete_confirm_dialog = create_delete_confirm_dialog(case.case_number if case else "N/A")

    # --- 案件番号編集用ダイアログ ---
    def create_case_number_dialog():
        return AlertDialog(
            modal=True,
            title=Text("案件番号編集"),
            content=Container(
                content=Column(
                    [Text("新しい案件番号を入力してください。"), dialog_case_number_field],
                    tight=True,
                ),
                height=150,
            ),
            actions=[
                TextButton("キャンセル", on_click=lambda e: close_dialog()),
                ElevatedButton("保存", on_click=lambda e: save_case_number()),
            ],
        )

    case_number_edit_dialog = create_case_number_dialog()

    def open_case_number_dialog(e):
        if not case:
            return
        dialog_case_number_field.value = case.case_number
        page.dialog = case_number_edit_dialog
        case_number_edit_dialog.open = True
        page.update()

    def save_case_number():
        if not case:
            return
        new_num = dialog_case_number_field.value.strip()
        if not new_num:
            page.open(SnackBar(Text("案件番号は必須です"), bgcolor=Colors.RED))
            return

        if update_case_number(case.case_id, new_num):
            page.open(SnackBar(Text("案件番号を更新しました"), bgcolor=Colors.GREEN))
            close_dialog()
            page.go(page.route)
        else:
            page.open(
                SnackBar(Text("更新失敗: この案件番号は既に使用されています"), bgcolor=Colors.RED)
            )

    # --- 担当者編集用ダイアログ ---
    def create_assignment_dialog():
        return AlertDialog(
            modal=True,
            title=Text("担当者編集"),
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

    def open_assignment_dialog(e):
        if not case:
            return
        dialog_manager_field.value = str(case.manager_id) if case.manager_id else ""
        dialog_operator_field.value = str(case.operator_id) if case.operator_id else ""
        page.dialog = assignment_edit_dialog
        assignment_edit_dialog.open = True
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
            name = f"{heir.name_last} {heir.name_first}"
            mark = "【契約者】" if getattr(heir, "is_contracting_party", False) else ""
            contacts = get_contact_info("heir", heir.id)
            phone = next((c["value"] for c in contacts if c["type"] == "PHONE"), "未登録")

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
                        # 修正: ID表示用のTextウィジェットを完全に削除しました
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
                content=Column(
                    [
                        # ヘッダー
                        Row(
                            [
                                Row(
                                    [
                                        Container(
                                            content=Text(
                                                f"案件番号: {case.case_number if case else 'New'}",
                                                size=22,
                                                weight=FontWeight.BOLD,
                                                color=Colors.ORANGE_400,
                                            ),
                                            on_click=lambda e: copy_to_clipboard_and_notify(
                                                e, page, case.case_number if case else ""
                                            ),
                                        ),
                                        # 案件番号編集ボタン
                                        IconButton(
                                            icon=Icons.EDIT,
                                            icon_color=Colors.ORANGE_400,
                                            tooltip="案件番号を編集",
                                            on_click=open_case_number_dialog,
                                        ),
                                    ]
                                ),
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
