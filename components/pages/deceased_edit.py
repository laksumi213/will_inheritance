# /components/pages/deceased_edit.py
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
    SnackBar,
    Text,
    TextField,
    TextStyle,
    View,
    alignment,
)

from components.utils.date_utils import convert_seireki_to_wareki
from components.utils.contact_controls import (
    add_new_contact_row,
    collect_contacts,
    create_contact_input_row,
)
from services import deceased_service
from services.deceased_service import (
    parse_all_flexible_date,
    search_address_by_zip_api,
    get_address_by_id
)

# --- グローバルな UI 定義 ---

# 1. 基本情報フィールド (黒文字設定に変更)
dialog_name_last_field = TextField(
    label="氏名 (姓)", width=180, color=Colors.BLACK, label_style=TextStyle(color=Colors.BLACK54)
)
dialog_name_first_field = TextField(
    label="氏名 (名)", width=180, color=Colors.BLACK, label_style=TextStyle(color=Colors.BLACK54)
)
dialog_kana_last_field = TextField(
    label="ふりがな (姓)",
    width=180,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK54),
)
dialog_kana_first_field = TextField(
    label="ふりがな (名)",
    width=180,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK54),
)
dialog_hometown_field = TextField(
    label="本籍地", width=500, color=Colors.BLACK, label_style=TextStyle(color=Colors.BLACK54)
)

# 2. 日付フィールド
dialog_dob_field = TextField(
    label="生年月日 (YYYY-MM-DD)",
    width=180,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK54),
)
# 和暦表示は背景色に合わせてColors.BLUE_GREY_800に変更
wareki_dob_text = Text(value="", width=200, color=Colors.BLUE_GREY_800, weight=FontWeight.W_500)

dialog_dod_field = TextField(
    label="死亡日 (YYYY-MM-DD)",
    width=180,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK54),
)
# 和暦表示は背景色に合わせてColors.BLUE_GREY_800に変更
wareki_dod_text = Text(value="", width=200, color=Colors.BLUE_GREY_800, weight=FontWeight.W_500)


# 3. 最後の住所フィールド (Last Address Fields)
# フィールドの色を黒文字に変更
last_zip_field = TextField(
    label="郵便番号",
    width=120,
    max_length=8,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK54),
)
last_pref_field = TextField(
    label="都道府県 *",
    width=150,
    read_only=True,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK54),
)
last_city_field = TextField(
    label="市区町村 *",
    width=200,
    read_only=True,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK54),
)
last_street_field = TextField(
    label="番地 (丁目/番/号) *",
    width=250,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK54),
)
last_building_field = TextField(
    label="建物名・部屋番号",
    width=400,
    color=Colors.BLACK,
    label_style=TextStyle(color=Colors.BLACK54),
)

# 4. 過去の住所履歴コンテナ (動的リスト)
past_addresses_column = Column(controls=[], spacing=10)

# 5. 💡 連絡先フィールド (動的リスト)
phone_inputs_column = Column(controls=[], spacing=5)
email_inputs_column = Column(controls=[], spacing=5)


# ------------------------------------------------------------------
# UI ヘルパーロジック
# ------------------------------------------------------------------


def update_wareki_display(date_field: TextField, wareki_text: Text):
    """日付フィールドの値に基づいて和暦表示を更新するヘルパー関数"""
    input_value = date_field.value.strip()
    wareki_text.value = ""
    date_field.error_text = None

    if not input_value:
        return

    try:
        validated_date = parse_all_flexible_date(input_value)
        # TextFieldの値を正規化
        date_field.value = validated_date.isoformat()
        # 和暦に変換して表示
        wareki_text.value = convert_seireki_to_wareki(validated_date)

    except ValueError:
        date_field.error_text = "無効な日付形式です"
        wareki_text.value = ""


def on_date_blur_handler(e, wareki_text: Text):
    """TextFieldがフォーカスを失ったときに実行されるハンドラー。和暦表示を更新する。"""
    update_wareki_display(e.control, wareki_text)
    e.control.update()
    e.page.update()


def create_address_fields(is_last: bool, data: dict = None):
    """住所入力フィールドセットを作成するヘルパー関数"""
    prefix = "最後の住所" if is_last else "過去の住所"

    data = data if data is not None else {}

    if is_last:
        # グローバルフィールドの値を更新
        last_zip_field.value = data.get("zip_code", "")
        last_pref_field.value = data.get("prefecture", "")
        last_city_field.value = data.get("city_ward_town", "")
        last_street_field.value = data.get("street_address", "")
        last_building_field.value = data.get("building_name", "")

        return [
            last_zip_field,
            last_pref_field,
            last_city_field,
            last_street_field,
            last_building_field,
        ]

    # is_last=False (過去の住所) の場合は、新しいコントロールを動的に作成
    zip_field = TextField(
        label=f"{prefix} 郵便番号",
        width=120,
        max_length=8,
        value=data.get("zip_code", ""),
        color=Colors.BLACK,
        label_style=TextStyle(color=Colors.BLACK54),
    )
    pref_field = TextField(
        label=f"{prefix} 都道府県 *",
        width=150,
        value=data.get("prefecture", ""),
        color=Colors.BLACK,
        label_style=TextStyle(color=Colors.BLACK54),
    )
    city_field = TextField(
        label=f"{prefix} 市区町村 *",
        width=200,
        value=data.get("city_ward_town", ""),
        color=Colors.BLACK,
        label_style=TextStyle(color=Colors.BLACK54),
    )
    street_field = TextField(
        label=f"{prefix} 番地 *",
        width=250,
        value=data.get("street_address", ""),
        color=Colors.BLACK,
        label_style=TextStyle(color=Colors.BLACK54),
    )
    building_field = TextField(
        label=f"{prefix} 建物名",
        width=400,
        value=data.get("building_name", ""),
        color=Colors.BLACK,
        label_style=TextStyle(color=Colors.BLACK54),
    )

    zip_field.on_blur = lambda event: address_zip_handler(event, pref_field, city_field)

    delete_button = IconButton(
        Icons.DELETE_OUTLINE,
        icon_color=Colors.RED_400,
        tooltip="この過去の住所を削除",
    )

    control_set = Column(
        controls=[
            Row(
                [zip_field, pref_field, city_field, street_field, building_field, delete_button],
                spacing=10,
            ),
        ],
        data={"is_last": is_last, "id": data.get("address_id", None)},
        spacing=10,
    )

    def delete_past_address(e):
        past_addresses_column.controls.remove(control_set)
        e.page.update()

    delete_button.on_click = delete_past_address

    return control_set


def address_zip_handler(e, pref_field: TextField, city_field: TextField):
    """郵便番号を入力した際の住所自動検索ハンドラ"""
    zip_code = e.control.value.strip()

    if len(zip_code.replace("-", "")) < 7:
        return

    address_info = search_address_by_zip_api(zip_code)

    if address_info:
        pref_field.value = address_info.get("prefecture", "")
        city_field.value = address_info.get("city_ward_town", "")
        e.control.error_text = None
    else:
        if pref_field.read_only:
            pref_field.value = ""
            city_field.value = ""
        e.control.error_text = "住所が見つかりません"

    pref_field.update()
    city_field.update()
    e.control.update()
    e.page.update()


# 既存のグローバルフィールドにハンドラを割り当て
dialog_dob_field.on_blur = lambda e: on_date_blur_handler(e, wareki_dob_text)
dialog_dod_field.on_blur = lambda e: on_date_blur_handler(e, wareki_dod_text)


def DeceasedEditView(page: Page, deceased_id_or_case_id: int):
    # 編集対象IDを特定 (Deceased ID または Case ID)
    target_id = deceased_id_or_case_id

    deceased = None
    if target_id > 0:
        deceased = deceased_service.get_deceased_by_id(target_id)
    
    # case_id -1/0 の場合は新規モードとして扱う
    is_new_mode = deceased is None or target_id < 1
    current_deceased_id = deceased.id if deceased else None

    # 最後の住所情報を取得
    last_address = None
    if deceased and deceased.last_address_id:
        last_address = get_address_by_id(deceased.last_address_id)

    # ----------------------------------------------------
    # データロード & UI 初期化
    # ----------------------------------------------------

    def reset_fields(e):
        """フォームのすべてのフィールドをリセットする"""
        dialog_name_last_field.value = ""
        dialog_name_first_field.value = ""
        dialog_kana_last_field.value = ""
        dialog_kana_first_field.value = ""
        dialog_hometown_field.value = ""
        dialog_dob_field.value = ""
        dialog_dod_field.value = ""
        wareki_dob_text.value = ""
        wareki_dod_text.value = ""

        last_zip_field.value = ""
        last_pref_field.value = ""
        last_city_field.value = ""
        last_street_field.value = ""
        last_building_field.value = ""

        past_addresses_column.controls.clear()
        phone_inputs_column.controls.clear()
        email_inputs_column.controls.clear()
        
        # 空行を1つずつ追加
        new_row_p, _ = create_contact_input_row(phone_inputs_column, is_email=False)
        phone_inputs_column.controls.append(new_row_p)
        new_row_e, _ = create_contact_input_row(email_inputs_column, is_email=True)
        email_inputs_column.controls.append(new_row_e)

        page.update()

    def load_data():
        """既存の被相続人データをロードする"""
        if not is_new_mode and current_deceased_id:
            # 既存データをロード
            dialog_name_last_field.value = deceased.name_last or ""
            dialog_name_first_field.value = deceased.name_first or ""
            dialog_kana_last_field.value = deceased.name_last_kana or ""
            dialog_kana_first_field.value = deceased.name_first_kana or ""
            dialog_hometown_field.value = deceased.hometown or ""
            dialog_dob_field.value = (
                deceased.date_of_birth.isoformat() if deceased.date_of_birth else ""
            )
            dialog_dod_field.value = (
                deceased.date_of_death.isoformat() if deceased.date_of_death else ""
            )

            # 和暦表示を更新
            update_wareki_display(dialog_dob_field, wareki_dob_text)
            update_wareki_display(dialog_dod_field, wareki_dod_text)

            # 1. 最後の住所
            last_address = None
            if deceased.last_address_id:
                last_address = deceased_service.get_address_by_id(deceased.last_address_id)
            
            if last_address:
                last_zip_field.value = last_address.zip_code or ""
                last_pref_field.value = last_address.prefecture or ""
                last_city_field.value = last_address.city_ward_town or ""
                last_street_field.value = last_address.street_address or ""
                last_building_field.value = last_address.building_name or ""
            else:
                last_zip_field.value = ""
                last_pref_field.value = ""
                last_city_field.value = ""
                last_street_field.value = ""
                last_building_field.value = ""

            create_address_fields(is_last=True, data=last_address)
            
            # 2. 過去の住所履歴を取得
            address_history = deceased_service.get_deceased_address_history(current_deceased_id)
            past_addresses_column.controls.clear()
            for addr in address_history:
                control_set = create_address_fields(is_last=False, data=addr)
                past_addresses_column.controls.append(control_set)

            # 3. 💡 連絡先のロード
            contacts = deceased_service.get_contact_info("deceased", current_deceased_id)
            
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

        elif is_new_mode:
            reset_fields(None) 

        page.update()

    # ----------------------------------------------------
    # UI 操作ロジック
    # ----------------------------------------------------

    def add_past_address(e):
        """新しい過去の住所入力フィールドセットを追加する"""
        new_address_set = create_address_fields(is_last=False, data={})
        past_addresses_column.controls.append(new_address_set)
        page.update()

    def save_data(e):
        """データを収集し、サービス層に渡して保存・更新する"""

        nonlocal current_deceased_id

        name_last = dialog_name_last_field.value.strip()
        name_first = dialog_name_first_field.value.strip()

        if not name_last or not name_first:
            page.open(
                SnackBar(
                    content=Text("氏名（姓）と氏名（名）は必須項目です。", color=Colors.WHITE),
                    bgcolor=Colors.RED_700,
                )
            )
            page.update()
            return

        # 過去の住所データを収集
        collected_past_addresses = []
        for control_set in past_addresses_column.controls:
            if not control_set.controls: continue
            
            # [0] is Row(zip, pref, city, street, building, delete_btn)
            row_controls = control_set.controls[0].controls
            if len(row_controls) < 5: continue 

            zip_code = row_controls[0].value.strip() 
            prefecture = row_controls[1].value.strip() 
            city_ward_town = row_controls[2].value.strip() 
            street_address = row_controls[3].value.strip() 
            building_name = row_controls[4].value.strip() 

            if prefecture and street_address:
                collected_past_addresses.append(
                    {
                        "zip_code": zip_code,
                        "prefecture": prefecture,
                        "city_ward_town": city_ward_town,
                        "street_address": street_address,
                        "building_name": building_name,
                        "is_last_address": False,
                        "address_id": control_set.data.get("id", None),
                    }
                )

        # 💡 連絡先データを収集
        phone_contacts = collect_contacts(phone_inputs_column)
        email_contacts = collect_contacts(email_inputs_column)

        try:
            # 3. 保存・更新処理
            deceased_service.update_deceased(
                deceased_id=current_deceased_id,
                name_last=dialog_name_last_field.value.strip() or None,
                name_first=dialog_name_first_field.value.strip() or None,
                dob=dialog_dob_field.value,
                dod=dialog_dod_field.value or None,
                kana_last=dialog_kana_last_field.value.strip() or None,
                kana_first=dialog_kana_first_field.value.strip() or None,
                hometown=dialog_hometown_field.value.strip() or None,
                # 最後の住所
                last_zip_code=last_zip_field.value.strip() or None,
                last_pref=last_pref_field.value.strip() or None,
                last_city=last_city_field.value.strip() or None,
                last_street=last_street_field.value.strip() or None,
                last_building=last_building_field.value.strip() or None,
                # 過去の住所リスト
                past_addresses=collected_past_addresses,
                # 💡 連絡先リスト
                phone_contacts=phone_contacts,
                email_contacts=email_contacts,
            )

            page.open(
                SnackBar(
                    content=Text("被相続人情報を保存しました。", color=Colors.WHITE),
                    bgcolor=Colors.GREEN_700,
                    duration=2000,
                )
            )
            # 詳細画面へ戻る (Case IDを取得して遷移)
            case_id = deceased_service.get_case_id_by_deceased_id(current_deceased_id)
            page.go(f"/detail/{case_id}")

        except Exception as ex:
            print(f"保存エラー: {ex}")
            page.open(
                SnackBar(
                    content=Text(f"保存中にエラーが発生しました: {ex}", color=Colors.WHITE),
                    bgcolor=Colors.RED_700,
                    duration=3000,
                )
            )
            page.update()

    # ----------------------------------------------------
    # UI レイアウト構築
    # ----------------------------------------------------

    last_address_row_controls = [
        last_zip_field,
        last_pref_field,
        last_city_field,
        last_street_field,
        last_building_field,
    ]

    last_zip_field.on_blur = lambda e: address_zip_handler(e, last_pref_field, last_city_field)

    view_controls = [
        AppBar(
            title=Text(f"👤 被相続人情報 {'新規登録' if is_new_mode else '編集'}"),
            bgcolor=Colors.BLUE_GREY_700,
        ),
        Container(
            content=Column(
                [
                    Text("1. 基本情報", size=18, weight=FontWeight.BOLD, color=Colors.BLACK),
                    Row([dialog_name_last_field, dialog_name_first_field]),
                    Row([dialog_kana_last_field, dialog_kana_first_field]),
                    Divider(),
                    Text(
                        "2. 生年月日・死亡日", size=18, weight=FontWeight.BOLD, color=Colors.BLACK
                    ),
                    Row([dialog_dob_field, wareki_dob_text]),
                    Row([dialog_dod_field, wareki_dod_text]),
                    Divider(),
                    Text(
                        "3. 連絡先情報", size=18, weight=FontWeight.BOLD, color=Colors.BLACK
                    ),
                    Row(
                        [
                            Text("電話番号", size=14, weight=FontWeight.W_500),
                            IconButton(
                                Icons.ADD,
                                icon_color=Colors.BLUE_500,
                                on_click=lambda e: add_new_contact_row(e, phone_inputs_column, is_email=False),
                            ),
                        ],
                        alignment=MainAxisAlignment.SPACE_BETWEEN,
                        width=600,
                    ),
                    phone_inputs_column,
                    Row(
                        [
                            Text("メールアドレス", size=14, weight=FontWeight.W_500),
                            IconButton(
                                Icons.ADD,
                                icon_color=Colors.BLUE_500,
                                on_click=lambda e: add_new_contact_row(e, email_inputs_column, is_email=True),
                            ),
                        ],
                        alignment=MainAxisAlignment.SPACE_BETWEEN,
                        width=600,
                    ),
                    email_inputs_column,
                    Divider(),
                    Text(
                        "4. 住所履歴 (最後の住所)",
                        size=18,
                        weight=FontWeight.BOLD,
                        color=Colors.BLACK,
                    ),
                    Text(
                        "※ 死亡時の住民票上の住所を入力してください",
                        size=12,
                        color=Colors.BLUE_GREY_600,
                    ),
                    Row(last_address_row_controls, spacing=10),
                    Divider(),
                    Row(
                        [
                            Text(
                                "5. 過去の住所履歴",
                                size=18,
                                weight=FontWeight.BOLD,
                                color=Colors.BLACK,
                            ),
                            ElevatedButton(
                                "過去の住所を追加",
                                icon=Icons.ADD,
                                on_click=add_past_address,
                                bgcolor=Colors.BLUE_600,
                                color=Colors.WHITE,
                            ),
                        ],
                    ),
                    Container(
                        content=past_addresses_column,
                        padding=10,
                        alignment=alignment.top_left,
                    ),
                    Divider(),
                    Text("6. 本籍地", size=18, weight=FontWeight.BOLD, color=Colors.BLACK),
                    Row([dialog_hometown_field]),
                    Divider(),
                    Row(
                        [
                            ElevatedButton(
                                "キャンセル",
                                on_click=lambda e: page.go(
                                    f"/detail/{deceased.case.case_id}" if deceased and deceased.case else "/"
                                ),
                                bgcolor=Colors.GREY_600,
                                color=Colors.WHITE,
                            ),
                            ElevatedButton(
                                "保存",
                                on_click=save_data,
                                bgcolor=Colors.GREEN_700,
                                color=Colors.WHITE,
                            ),
                        ],
                        alignment=MainAxisAlignment.END,
                        spacing=20,
                    ),
                ],
                horizontal_alignment=CrossAxisAlignment.START,
                scroll=ScrollMode.ADAPTIVE,
            ),
            padding=20,
            expand=True,
            bgcolor=Colors.WHITE,
        ),
    ]

    view = View(f"/deceased_edit/{target_id}", view_controls, scroll=ScrollMode.ADAPTIVE)

    page.run_thread(load_data)

    return view