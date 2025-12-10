# src/views/deceased_edit.py
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
    padding,
)

from src.utils.date_utils import convert_seireki_to_wareki, parse_all_flexible_date, on_date_blur_handler
from src.components.business.contact_controls import (
    add_new_contact_row,
    collect_contacts,
    create_contact_input_row,
    add_initial_contact_rows,
)
from src.services import deceased_service
from src.services.deceased_service import (
    get_address_by_id,
    get_case_id_by_deceased_id,
    search_address_by_zip_api,
    get_deceased_by_id,
)


def DeceasedEditView(page: Page, deceased_id: int, case_id: int):
    """
    被相続人情報の編集・新規登録画面
    """
    # DBからデータ取得
    deceased = None
    if deceased_id > 0:
        deceased = get_deceased_by_id(deceased_id)
    
    # 新規モード判定
    is_new_mode = deceased is None or deceased_id < 1
    
    # 保存時に使用するID
    current_deceased_id = deceased.id if deceased else None

    # 💡 戻り先ルートの確定 (渡された case_id を使用して確実に詳細画面へ戻る)
    back_route = f"/detail/{case_id}" if case_id else "/"
    print('back_route:', back_route)

    # ----------------------------------------------------
    # UI コンポーネント定義
    # ----------------------------------------------------

    # 1. 基本情報フィールド
    name_last_field = TextField(label="氏名 (姓)", width=180, autofocus=True)
    name_first_field = TextField(label="氏名 (名)", width=180)
    kana_last_field = TextField(label="ふりがな (姓)", width=180)
    kana_first_field = TextField(label="ふりがな (名)", width=180)
    hometown_field = TextField(label="本籍地", width=500)

    # 2. 日付フィールド
    wareki_dob_text = Text(value="", width=200, color="onSurfaceVariant", weight=FontWeight.W_500)
    dob_field = TextField(
        label="生年月日 (YYYY-MM-DD)",
        width=180,
        on_blur=lambda e: on_date_blur_handler(e, wareki_dob_text)
    )

    wareki_dod_text = Text(value="", width=200, color="onSurfaceVariant", weight=FontWeight.W_500)
    dod_field = TextField(
        label="死亡日 (YYYY-MM-DD)",
        width=180,
        on_blur=lambda e: on_date_blur_handler(e, wareki_dod_text)
    )

    # 3. 最後の住所フィールド
    last_zip_field = TextField(label="郵便番号", width=120, max_length=8)
    last_pref_field = TextField(label="都道府県", width=150)
    last_city_field = TextField(label="市区町村", width=200)
    last_street_field = TextField(label="番地 (丁目/番/号)", width=250)
    last_building_field = TextField(label="建物名・部屋番号", width=400)

    # 住所自動入力ハンドラ
    def address_zip_handler(e, pref_f, city_f, street_f):
        zip_code = e.control.value.strip()
        if len(zip_code.replace("-", "")) < 7:
            return
        
        addr_info = search_address_by_zip_api(zip_code)
        if addr_info:
            pref_f.value = addr_info.get("prefecture", "")
            city_f.value = addr_info.get("city_ward_town", "")
            street_f.value = addr_info.get("street_address", "")
            e.control.error_text = None
        else:
            e.control.error_text = "住所が見つかりません"
        page.update()

    last_zip_field.on_blur = lambda e: address_zip_handler(e, last_pref_field, last_city_field, last_street_field)

    # 4. 履歴・連絡先コンテナ
    past_addresses_column = Column(controls=[], spacing=10)
    phone_inputs_column = Column(controls=[], spacing=5)
    email_inputs_column = Column(controls=[], spacing=5)

    # ----------------------------------------------------
    # ヘルパー関数
    # ----------------------------------------------------

    def update_wareki_display(date_field, wareki_text):
        if not date_field.value: return
        try:
            d = parse_all_flexible_date(date_field.value)
            date_field.value = d.isoformat()
            wareki_text.value = convert_seireki_to_wareki(d)
        except ValueError:
            pass

    def create_past_address_fields(data: dict = None):
        data = data or {}
        
        zip_f = TextField(label="郵便番号", width=120, value=data.get("zip_code", ""))
        pref_f = TextField(label="都道府県", width=150, value=data.get("prefecture", ""))
        city_f = TextField(label="市区町村", width=200, value=data.get("city_ward_town", ""))
        street_f = TextField(label="番地", width=250, value=data.get("street_address", ""))
        bldg_f = TextField(label="建物名", width=200, value=data.get("building_name", ""))
        
        zip_f.on_blur = lambda e: address_zip_handler(e, pref_f, city_f, street_f)

        delete_btn = IconButton(Icons.DELETE_OUTLINE, icon_color="error", tooltip="削除")
        
        row_control = Row([zip_f, pref_f, city_f, street_f, bldg_f, delete_btn], spacing=10)
        
        def delete_row(e):
            past_addresses_column.controls.remove(row_control)
            page.update()
        
        delete_btn.on_click = delete_row
        row_control.data = {"address_id": data.get("address_id")}
        
        return row_control

    def add_past_address(e):
        past_addresses_column.controls.append(create_past_address_fields({}))
        page.update()

    # ----------------------------------------------------
    # データロード処理
    # ----------------------------------------------------
    def load_data():
        if not is_new_mode and deceased:
            name_last_field.value = deceased.name_last or ""
            name_first_field.value = deceased.name_first or ""
            kana_last_field.value = deceased.name_last_kana or ""
            kana_first_field.value = deceased.name_first_kana or ""
            hometown_field.value = deceased.hometown or ""
            
            dob_field.value = str(deceased.date_of_birth) if deceased.date_of_birth else ""
            dod_field.value = str(deceased.date_of_death) if deceased.date_of_death else ""
            update_wareki_display(dob_field, wareki_dob_text)
            update_wareki_display(dod_field, wareki_dod_text)

            if deceased.last_address_id:
                addr = get_address_by_id(deceased.last_address_id)
                if addr:
                    last_zip_field.value = addr.zip_code or ""
                    last_pref_field.value = addr.prefecture or ""
                    last_city_field.value = addr.city_ward_town or ""
                    last_street_field.value = addr.street_address or ""
                    last_building_field.value = addr.building_name or ""

            histories = deceased_service.get_deceased_address_history(deceased.id)
            past_addresses_column.controls.clear()
            for h in histories:
                past_addresses_column.controls.append(create_past_address_fields(h))

            contacts = deceased_service.get_contact_info("deceased", deceased.id)
            
            phone_contacts = [c for c in contacts if c["type"] == "PHONE"]
            phone_inputs_column.controls.clear()
            if phone_contacts:
                for c in phone_contacts:
                    row, _ = create_contact_input_row(phone_inputs_column, initial_value=c["value"], is_email=False)
                    phone_inputs_column.controls.append(row)
            else:
                add_initial_contact_rows(phone_inputs_column, is_email=False, count=1)

            email_contacts = [c for c in contacts if c["type"] == "EMAIL"]
            email_inputs_column.controls.clear()
            if email_contacts:
                for c in email_contacts:
                    row, _ = create_contact_input_row(email_inputs_column, initial_value=c["value"], is_email=True)
                    email_inputs_column.controls.append(row)
            else:
                add_initial_contact_rows(email_inputs_column, is_email=True, count=1)

        else:
            # 新規モード: 空行を追加
            name_last_field.value = ""
            name_first_field.value = ""
            kana_last_field.value = ""
            kana_first_field.value = ""
            hometown_field.value = ""
            dob_field.value = ""
            dod_field.value = ""
            last_zip_field.value = ""
            last_pref_field.value = ""
            last_city_field.value = ""
            last_street_field.value = ""
            last_building_field.value = ""
            wareki_dob_text.value = ""
            wareki_dod_text.value = ""
            
            past_addresses_column.controls.clear()
            phone_inputs_column.controls.clear()
            email_inputs_column.controls.clear()
            
            add_initial_contact_rows(phone_inputs_column, is_email=False, count=1)
            add_initial_contact_rows(email_inputs_column, is_email=True, count=1)

        page.update()

    # ----------------------------------------------------
    # 保存処理
    # ----------------------------------------------------
    def save_data(e):
        if not name_last_field.value or not name_first_field.value:
            page.open(SnackBar(Text("氏名は必須です"), bgcolor="error"))
            page.update()
            return

        past_addresses_data = []
        for row in past_addresses_column.controls:
            controls = row.controls
            if len(controls) < 5: continue
            
            p_zip = controls[0].value
            p_pref = controls[1].value
            p_city = controls[2].value
            p_street = controls[3].value
            p_bldg = controls[4].value
            
            if p_pref or p_street:
                past_addresses_data.append({
                    "zip_code": p_zip,
                    "prefecture": p_pref,
                    "city_ward_town": p_city,
                    "street_address": p_street,
                    "building_name": p_bldg,
                    "is_last_address": False,
                    "address_id": row.data.get("address_id")
                })

        try:
            success = deceased_service.update_deceased(
                deceased_id=current_deceased_id, 
                name_last=name_last_field.value,
                name_first=name_first_field.value,
                kana_last=kana_last_field.value,
                kana_first=kana_first_field.value,
                hometown=hometown_field.value,
                dob=dob_field.value,
                dod=dod_field.value,
                last_zip_code=last_zip_field.value,
                last_pref=last_pref_field.value,
                last_city=last_city_field.value,
                last_street=last_street_field.value,
                last_building=last_building_field.value,
                past_addresses=past_addresses_data,
                phone_contacts=collect_contacts(phone_inputs_column),
                email_contacts=collect_contacts(email_inputs_column)
            )

            if success:
                page.open(SnackBar(Text("保存しました"), bgcolor="primary"))
                # 💡 修正: back_route を使用して遷移
                page.go(back_route)
            else:
                page.open(SnackBar(Text("保存に失敗しました"), bgcolor="error"))

        except Exception as ex:
            print(f"Save Error: {ex}")
            page.open(SnackBar(Text(f"エラー: {ex}"), bgcolor="error"))
        page.update()


    # ----------------------------------------------------
    # 画面レイアウト構築
    # ----------------------------------------------------
    
    def on_cancel_click(e):
        print(f"DEBUG: Cancel Clicked. Going to -> {back_route}")
        page.go(back_route)

    view_controls = [
        AppBar(
            title=Text(f"👤 被相続人情報 {'新規登録' if is_new_mode else '編集'}"),
            bgcolor="surfaceVariant",
            # 💡 AppBarの戻るボタンにも back_route を適用
            leading=IconButton(Icons.ARROW_BACK, on_click=lambda e: page.go(back_route)),
        ),
        Container(
            content=Column(
                [
                    Text("1. 基本情報", size=18, weight=FontWeight.BOLD, color="onSurface"),
                    Row([name_last_field, name_first_field]),
                    Row([kana_last_field, kana_first_field]),
                    Divider(),
                    
                    Text("2. 生年月日・死亡日", size=18, weight=FontWeight.BOLD, color="onSurface"),
                    Row([dob_field, wareki_dob_text]),
                    Row([dod_field, wareki_dod_text]),
                    Divider(),
                    
                    Text("3. 連絡先情報", size=18, weight=FontWeight.BOLD, color="onSurface"),
                    Row([
                        Text("電話番号", size=14, weight=FontWeight.W_500),
                        IconButton(Icons.ADD, icon_color="primary", on_click=lambda e: add_new_contact_row(e, phone_inputs_column, False))
                    ], width=600, alignment=MainAxisAlignment.SPACE_BETWEEN),
                    phone_inputs_column,
                    
                    Row([
                        Text("メールアドレス", size=14, weight=FontWeight.W_500),
                        IconButton(Icons.ADD, icon_color="primary", on_click=lambda e: add_new_contact_row(e, email_inputs_column, True))
                    ], width=600, alignment=MainAxisAlignment.SPACE_BETWEEN),
                    email_inputs_column,
                    Divider(),

                    Text("4. 住所履歴 (最後の住所)", size=18, weight=FontWeight.BOLD, color="onSurface"),
                    Text("※ 死亡時の住民票上の住所を入力してください", size=12, color="onSurfaceVariant"),
                    Row([last_zip_field, last_pref_field, last_city_field, last_street_field, last_building_field], wrap=True),
                    Divider(),

                    Row([
                        Text("5. 過去の住所履歴", size=18, weight=FontWeight.BOLD, color="onSurface"),
                        ElevatedButton("追加", icon=Icons.ADD, on_click=add_past_address, bgcolor="primaryContainer", color="onPrimaryContainer"),
                    ]),
                    past_addresses_column,
                    Divider(),

                    Text("6. 本籍地", size=18, weight=FontWeight.BOLD, color="onSurface"),
                    hometown_field,
                    Divider(),

                    Row([
                        # ElevatedButton("キャンセル", on_click=lambda e: page.go(back_route), bgcolor="surfaceVariant", color="onSurfaceVariant"),
                        ElevatedButton("キャンセル", on_click=on_cancel_click, bgcolor="surfaceVariant", color="onSurfaceVariant"),
                        ElevatedButton("保存", on_click=save_data, bgcolor="primary", color="onPrimary"),
                    ], alignment=MainAxisAlignment.END, spacing=20),
                ],
                scroll=ScrollMode.ADAPTIVE,
            ),
            padding=20,
            expand=True,
        )
    ]

    view = View(f"/deceased_edit/{deceased_id}?case_id={case_id}", view_controls, scroll=ScrollMode.ADAPTIVE)
    page.run_thread(load_data)

    return view