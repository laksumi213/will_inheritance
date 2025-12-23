# src/views/deceased_edit.py
import re
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
    View,
    alignment,
    padding,
    Chip,
    border,
)

from src.components.business.contact_controls import (
    add_new_contact_row,
    collect_contacts,
    create_contact_input_row,
    add_initial_contact_rows,
)
from src.utils.date_utils import (
    convert_seireki_to_wareki,
    parse_all_flexible_date,
    on_date_blur_handler,
)

from src.services import deceased_service
from src.services.deceased_service import (
    get_address_by_id,
    get_case_id_by_deceased_id,
    search_address_by_zip_api,
    search_zip_by_address_api,
    get_deceased_by_id,
)
from src.services.ai_service import ai_service


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

    # 戻り先ルートの確定
    back_route = f"/detail/{case_id}" if case_id else "/"

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

    # AI候補表示エリア
    candidate_chips_row = Row(wrap=True, spacing=5)
    candidate_container = Container(
        content=Column([
            Text("💡 都道府県が見つかりませんでした。以下から選択してください:", size=12, color=Colors.ORANGE_900),
            candidate_chips_row
        ], spacing=5),
        visible=False,
        bgcolor=Colors.ORANGE_50,
        padding=10,
        border_radius=5,
        border=border.all(1, Colors.ORANGE_200)
    )

    # 住所自動入力ハンドラ (Zip -> Address)
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
            e.control.error_text = "住所が見つかりませんでした"
        page.update()

    # 郵便番号自動入力ハンドラ (Address -> Zip)
    def auto_fill_zip_handler(e, zip_f, pref_f, city_f, street_f):
        if zip_f.value: return # 既に入力済ならスキップ
        
        pref = pref_f.value or ""
        city = city_f.value or ""
        street = street_f.value or ""
        if not pref or not city: return

        # 精度向上ロジック: 町域のみを抽出
        zip_code = None
        if street:
            # 💡 修正: 全角数字も含めて除外対象にする正規表現に変更
            match = re.match(r'^([^0-9\-\uFF10-\uFF19]+)', street)
            if match:
                town_part = match.group(1).strip()
                zip_code = search_zip_by_address_api(f"{pref}{city}{town_part}")

        if not zip_code:
            zip_code = search_zip_by_address_api(f"{pref}{city}{street}")
        
        # 💡 修正: 「市レベルでのフォールバック」を削除
        # これにより、町名不一致時に代表番号（矢上町など）がセットされるのを防ぎます。

        if zip_code:
            zip_f.value = zip_code
            page.update()

    # ヘルパー: フィールドへのセットとZIP検索
    def _fill_address_fields_local(pref: str, rest: str):
        last_pref_field.value = pref
        
        # 市区町村抽出
        match_city = re.match(r'^(.+?[郡市区町村])(.+)', rest)
        if match_city:
            city = match_city.group(1)
            rest_street = match_city.group(2).strip()
            last_city_field.value = city
            
            parts = rest_street.split(" ", 1)
            last_street_field.value = parts[0]
            last_building_field.value = parts[1] if len(parts) > 1 else ""
        else:
            last_city_field.value = ""
            last_street_field.value = rest
            last_building_field.value = ""
        
        # 非同期でZIP検索
        page.run_thread(lambda: auto_fill_zip_handler(None, last_zip_field, last_pref_field, last_city_field, last_street_field))
        page.update()

    # ヘルパー: 候補選択時
    def _on_candidate_select(pref: str, rest: str):
        candidate_container.visible = False
        _fill_address_fields_local(pref, rest)

    # AI推測ロジック
    def _predict_prefecture_with_ai(address_fragment: str):
        page.open(SnackBar(Text("都道府県を検索中..."), bgcolor=Colors.BLUE_GREY_400))
        page.update()

        def task():
            try:
                candidates = ai_service.predict_prefectures_sync(address_fragment)
                if not candidates:
                    page.open(SnackBar(Text("都道府県を特定できませんでした。"), bgcolor=Colors.ORANGE))
                    candidate_container.visible = False
                elif len(candidates) == 1:
                    pref = candidates[0]
                    page.open(SnackBar(Text(f"「{pref}」を補完しました。"), bgcolor=Colors.GREEN))
                    _fill_address_fields_local(pref, address_fragment)
                else:
                    candidate_chips_row.controls.clear()
                    for cand in candidates:
                        candidate_chips_row.controls.append(
                            Chip(
                                label=Text(cand),
                                on_select=lambda e, p=cand: _on_candidate_select(p, address_fragment),
                                bgcolor=Colors.WHITE
                            )
                        )
                    candidate_container.visible = True
            except Exception as e:
                print(f"AI Error: {e}")
                candidate_container.visible = False
            page.update()

        page.run_thread(task)

    # 住所貼り付けハンドラ
    def parse_and_fill_address(e):
        full_address = e.control.value
        if not full_address:
            candidate_container.visible = False
            page.update()
            return
        
        full_address = full_address.replace("　", " ").strip()
        
        match_pref = re.match(r'(.*?([都道府県]))(.+)', full_address)
        if match_pref:
            candidate_container.visible = False
            pref = match_pref.group(1)
            rest = match_pref.group(3).strip()
            _fill_address_fields_local(pref, rest)
        else:
            _predict_prefecture_with_ai(full_address)

    last_paste_address_field = TextField(
        label="📍 住所貼り付け (ここに入力すると自動分割されます)",
        width=600,
        on_change=parse_and_fill_address,
        text_size=13,
        color="onSecondaryContainer",
        bgcolor="secondaryContainer",
        border_color=Colors.TRANSPARENT,
        hint_text="都道府県がない場合、AIが補完します"
    )

    last_zip_field.on_blur = lambda e: address_zip_handler(e, last_pref_field, last_city_field, last_street_field)
    
    # 各住所フィールドのon_blurにZip検索ハンドラを紐付け
    last_pref_field.on_blur = lambda e: auto_fill_zip_handler(e, last_zip_field, last_pref_field, last_city_field, last_street_field)
    last_city_field.on_blur = lambda e: auto_fill_zip_handler(e, last_zip_field, last_pref_field, last_city_field, last_street_field)
    last_street_field.on_blur = lambda e: auto_fill_zip_handler(e, last_zip_field, last_pref_field, last_city_field, last_street_field)

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
        
        # 過去の住所欄にも逆引きを適用
        pref_f.on_blur = lambda e: auto_fill_zip_handler(e, zip_f, pref_f, city_f, street_f)
        city_f.on_blur = lambda e: auto_fill_zip_handler(e, zip_f, pref_f, city_f, street_f)
        street_f.on_blur = lambda e: auto_fill_zip_handler(e, zip_f, pref_f, city_f, street_f)

        delete_btn = IconButton(Icons.DELETE_OUTLINE, icon_color=Colors.ERROR, tooltip="削除")
        
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
            page.open(SnackBar(Text("氏名は必須です"), bgcolor=Colors.ERROR))
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
                page.open(SnackBar(Text("保存しました"), bgcolor=Colors.PRIMARY))
                # 💡 修正: back_route を使用して遷移
                page.go(back_route)
            else:
                page.open(SnackBar(Text("保存に失敗しました"), bgcolor=Colors.ERROR))

        except Exception as ex:
            print(f"Save Error: {ex}")
            page.open(SnackBar(Text(f"エラー: {ex}"), bgcolor=Colors.ERROR))
        page.update()


    # ----------------------------------------------------
    # 画面レイアウト構築
    # ----------------------------------------------------
    
    def on_cancel_click(e):
        page.go(back_route)

    view_controls = [
        AppBar(
            title=Text(f"👤 被相続人情報 {'新規登録' if is_new_mode else '編集'}"),
            bgcolor="surfaceVariant",
            color="onSurfaceVariant",
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
                    Row(
                        [dob_field, wareki_dob_text],
                        vertical_alignment=CrossAxisAlignment.END,
                    ),
                    Row([dod_field, wareki_dod_text]),
                    Divider(),
                    
                    Text("3. 連絡先情報", size=18, weight=FontWeight.BOLD, color="onSurface"),
                    Row([
                        Text("電話番号", size=14, weight=FontWeight.W_500),
                        IconButton(Icons.ADD, icon_color=Colors.PRIMARY, on_click=lambda e: add_new_contact_row(e, phone_inputs_column, False))
                    ], width=600, alignment=MainAxisAlignment.SPACE_BETWEEN),
                    phone_inputs_column,
                    
                    Row([
                        Text("メールアドレス", size=14, weight=FontWeight.W_500),
                        IconButton(Icons.ADD, icon_color=Colors.PRIMARY, on_click=lambda e: add_new_contact_row(e, email_inputs_column, True))
                    ], width=600, alignment=MainAxisAlignment.SPACE_BETWEEN),
                    email_inputs_column,
                    Divider(),

                    Text("4. 住所履歴 (最後の住所)", size=18, weight=FontWeight.BOLD, color="onSurface"),
                    Text("※ 死亡時の住民票上の住所を入力してください", size=12, color="onSurfaceVariant"),
                    # 💡 住所貼り付けフィールド
                    last_paste_address_field,
                    candidate_container, # 候補表示
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