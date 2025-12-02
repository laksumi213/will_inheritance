# src/views/detail.py
import tkinter as tk
from tkinter import messagebox

import pyperclip
from flet import (
    Colors,
    Column,
    Container,
    Divider,
    Dropdown,
    ElevatedButton,
    FilePicker,
    FontWeight,
    IconButton,
    Icons,
    MainAxisAlignment,
    Page,
    Row,
    ScrollMode,
    SnackBar,
    Text,
    TextField,
    dropdown,
)
from src.utils.date_utils import convert_seireki_to_wareki

# 💡 修正: サービス層からのインポート
from src.services.deceased_service import (
    delete_heir,
    get_address_by_id,
    get_all_users,
    get_case_by_id,
    get_case_folder_path,
    get_deceased_by_case_id,
    get_kintone_integration_data,
    parse_all_flexible_date,
    update_case_folder_path,
)

# --- グローバル定義 ---
# 注意: ここでDBアクセスすると初期化前に走る可能性があるため、クラス内や関数内で呼ぶのが安全ですが、
# 提示コードの構造を維持します。
try:
    USER_MAP = get_all_users()
except:
    USER_MAP = {}

USER_OPTIONS = [dropdown.Option(str(id), name) for id, name in USER_MAP.items()]
USER_OPTIONS.insert(0, dropdown.Option("", "未割当"))

dialog_manager_field = Dropdown(
    label="担当者1 (進捗管理)", width=200, options=USER_OPTIONS, value=""
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

    # 最後の住所取得
    last_address = None
    if deceased and deceased.last_address_id:
        last_address = get_address_by_id(deceased.last_address_id)

    display_deceased_address = "未登録"
    copyable_full_address = "未登録"
    if last_address:
        raw = f"{last_address.prefecture}{last_address.city_ward_town}{last_address.street_address}"
        building = last_address.building_name or ""
        display_deceased_address = f"{raw} ({building})" if building else raw
        copyable_full_address = f"〒{last_address.zip_code} {raw} {building}".strip()

    if deceased and not is_new_client_case:
        full_name = f"{deceased.name_last} {deceased.name_first}"
        dob_display_str = (
            f"{deceased.date_of_birth} ({convert_seireki_to_wareki(deceased.date_of_birth)})"
            if deceased.date_of_birth
            else "未登録"
        )
        dod_display_str = (
            f"{deceased.date_of_death} ({convert_seireki_to_wareki(deceased.date_of_death)})"
            if deceased.date_of_death
            else "未登録"
        )
    else:
        full_name = "【未登録】"
        dob_display_str = "N/A"
        dod_display_str = "N/A"
        # Dummy
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
        case = None

    heirs_controls = Column()
    path_field = TextField(label="フォルダ保存パス", width=600, value="")

    def save_path_on_blur(e):
        current = path_field.value.strip()
        if case and current:
            if current != get_case_folder_path(case.case_id):
                update_case_folder_path(case.case_id, current)
                page.open(SnackBar(Text("パスを更新しました"), bgcolor=Colors.BLUE_700))
        page.update()

    path_field.on_blur = save_path_on_blur

    def open_folder_dialog_detail(e):
        file_picker.on_result = (
            lambda e: [setattr(path_field, "value", e.path), save_path_on_blur(e), page.update()]
            if e.path
            else None
        )
        file_picker.get_directory_path("保存先を選択")

    # --- UI Layout ---
    # 表示用コンポーネントを構築して返す（ViewではなくContainer/Column）
    # CaseHubViewでラップされるため、AppBarなどはCaseHubView側にあるのが自然だが、
    # ここでは詳細情報のColumnを返す。

    # 相続人リスト構築
    def update_heirs_list():
        heirs_controls.controls.clear()
        current = get_deceased_by_case_id(deceased.id) if deceased.id > 0 else None
        if not current or not current.heirs:
            return

        for heir in current.heirs:
            name = f"{heir.name_last} {heir.name_first}"
            heirs_controls.controls.append(
                Row(
                    [
                        Text(f"ID:{heir.id}", width=40),
                        Text(name, width=150, weight=FontWeight.BOLD),
                        Text(heir.relationship_type or "-", width=80),
                        IconButton(
                            Icons.EDIT,
                            icon_color=Colors.BLUE,
                            on_click=lambda e, hid=heir.id: page.go(
                                f"/heir_edit/{hid}?deceased_id={current.id}"
                            ),
                        ),
                        IconButton(
                            Icons.DELETE,
                            icon_color=Colors.RED,
                            on_click=lambda e, hid=heir.id: delete_heir_handler(hid),
                        ),
                    ]
                )
            )
        page.update()

    def delete_heir_handler(hid):
        delete_heir(hid)
        update_heirs_list()
        page.open(SnackBar(Text("削除しました"), bgcolor=Colors.RED))

    if not is_new_deceased:
        update_heirs_list()
        path_field.value = get_case_folder_path(case.case_id) if case else ""

    # メインレイアウト
    return Column(
        controls=[
            Container(
                content=Column(
                    [
                        Row(
                            [
                                Text(
                                    f"案件番号: {case.case_number if case else 'New'}",
                                    size=20,
                                    weight=FontWeight.BOLD,
                                ),
                                ElevatedButton(
                                    "Kintone連携",
                                    icon=Icons.CLOUD_UPLOAD,
                                    on_click=lambda e: launch_kintone_automation(case.case_id)
                                    if case
                                    else None,
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        Divider(),
                        Text("👤 被相続人情報", size=18, weight=FontWeight.BOLD),
                        Row(
                            [
                                Text(f"氏名: {full_name}", size=16),
                                Text(f"生年月日: {dob_display_str}"),
                                Text(f"死亡日: {dod_display_str}"),
                            ],
                            spacing=20,
                        ),
                        Text(f"住所: {display_deceased_address}"),
                        Divider(),
                        Row(
                            [
                                Text("相続人リスト", size=18, weight=FontWeight.BOLD),
                                ElevatedButton(
                                    "追加",
                                    icon=Icons.ADD,
                                    on_click=lambda e: page.go(
                                        f"/heir_edit/new?deceased_id={deceased.id}"
                                    )
                                    if deceased.id
                                    else None,
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        heirs_controls,
                        Divider(),
                        Text("フォルダパス設定", weight=FontWeight.BOLD),
                        Row(
                            [
                                path_field,
                                IconButton(Icons.FOLDER, on_click=open_folder_dialog_detail),
                            ]
                        ),
                    ]
                ),
                padding=20,
                bgcolor=Colors.WHITE,
                border_radius=10,
            )
        ],
        scroll=ScrollMode.AUTO,
    )
