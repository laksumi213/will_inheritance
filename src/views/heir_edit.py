# src/views/heir_edit.py
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
)

from src.components.business.contact_controls import (
    add_new_contact_row,
    collect_contacts,
    create_contact_input_row,
)
from src.utils.date_utils import (
    convert_seireki_to_wareki,
    parse_all_flexible_date,
    on_date_blur_handler,
)

from src.services import deceased_service
from src.services.deceased_service import (
    get_address_info,
    get_heir_by_id,
)

def HeirEditView(page: Page, heir_id: int, deceased_id: int, case_id: int):
    """
    相続人情報（新規または既存）の編集を行う View
    """

    is_new_heir = heir_id == 0

    data = None
    address_info = {}
    contacts = []

    if not is_new_heir:
        data = get_heir_by_id(heir_id)
        if not data:
            return View(f"/heir_edit/{heir_id}", [Text("相続人データが見つかりませんでした。")])

        deceased_id = data.deceased_id
        address_info = get_address_info("heir", heir_id)
        contacts = deceased_service.get_contact_info("heir", heir_id)

    # 戻り先ルートの確定
    back_route = f"/detail/{case_id}" if case_id else "/"

    title_suffix = f" (被相続人ID: {deceased_id})" if deceased_id else ""
    title_text = (
        f"新しい相続人情報 新規登録{title_suffix}"
        if is_new_heir
        else f"相続人情報 編集{title_suffix}"
    )

    # --- UI コンポーネント ---
    name_last_field = TextField(label="氏名 (姓)", width=150, autofocus=True)
    name_first_field = TextField(label="氏名 (名)", width=150)
    kana_last_field = TextField(label="ふりがな (姓)", width=150)
    kana_first_field = TextField(label="ふりがな (名)", width=150)
    rel_field = TextField(label="続柄", width=200)
    hometown_field = TextField(label="本籍地")

    wareki_dob_text = Text(value="", width=250, color="onSurfaceVariant", weight=FontWeight.W_500)
    dob_field = TextField(
        label="生年月日 (YYYY-MM-DD)",
        width=180,
        on_blur=lambda e: (
            on_date_blur_handler(e, wareki_dob_text),
            page.update(),
        ),
    )

    zip_field = TextField(label="郵便番号", width=150)
    pref_field = TextField(label="都道府県", width=150)
    city_field = TextField(label="市区町村", width=200)
    street_field = TextField(label="番地", width=150)
    building_field = TextField(label="建物名・部屋番号")

    # --- 動的フォーム初期化 ---
    phone_inputs_column = Column(controls=[], spacing=5)
    email_inputs_column = Column(controls=[], spacing=5)

    def initialize_contact_controls(contact_list, column: Column, is_email: bool):
        column.controls.clear()
        filtered_contacts = [
            c for c in contact_list if c.get("type") == ("EMAIL" if is_email else "PHONE")
        ]

        if filtered_contacts:
            for c in filtered_contacts:
                new_row, _ = create_contact_input_row(
                    column, initial_value=c["value"], is_email=is_email
                )
                column.controls.append(new_row)
        else:
            new_row, _ = create_contact_input_row(column, is_email=is_email)
            column.controls.append(new_row)

    # 値のセット
    if data:
        name_last_field.value = data.name_last or ""
        name_first_field.value = data.name_first or ""
        kana_last_field.value = data.name_last_kana or ""
        kana_first_field.value = data.name_first_kana or ""
        rel_field.value = data.relationship_type or ""
        hometown_field.value = data.hometown or ""
        dob_field.value = str(data.date_of_birth) if data.date_of_birth else ""
        
        if dob_field.value:
            try:
                d = parse_all_flexible_date(dob_field.value)
                wareki_dob_text.value = convert_seireki_to_wareki(d)
            except ValueError: pass

        zip_field.value = address_info.get("zip_code", "")
        pref_field.value = address_info.get("prefecture", "")
        city_field.value = address_info.get("city_ward_town", "")
        street_field.value = address_info.get("street_address", "")
        building_field.value = address_info.get("building_name", "")

    initialize_contact_controls(contacts, phone_inputs_column, False)
    initialize_contact_controls(contacts, email_inputs_column, True)


    def search_address_by_zip(e):
        zip_code = zip_field.value
        address_info = deceased_service.search_address_by_zip_api(zip_code)

        if address_info is None:
            pref_field.value = "通信エラー"
            city_field.value = ""
            street_field.value = ""
        elif address_info == {}:
            pref_field.value = "住所が見つかりませんでした"
            city_field.value = ""
            street_field.value = ""
        else:
            pref_field.value = address_info.get("prefecture", "")
            city_field.value = address_info.get("city_ward_town", "")
            street_field.value = address_info.get("street_address", "")

        page.update()
        street_field.focus()

    zip_field.on_blur = search_address_by_zip

    # 💡 住所貼り付けロジック (他画面と同様に修正)
    def parse_and_fill_address(e):
        full_address = e.control.value
        if not full_address: return
        
        full_address = full_address.replace("　", " ").strip()
        
        match_pref = re.match(r'(.*?([都道府県]))(.+)', full_address)
        if match_pref:
            pref = match_pref.group(1)
            rest = match_pref.group(3).strip()
            
            pref_field.value = pref
            
            match_city = re.match(r'^(.+?[郡市区町村])(.+)', rest)
            if match_city:
                city = match_city.group(1)
                rest_street = match_city.group(2).strip()
                city_field.value = city
                
                parts = rest_street.split(" ", 1)
                street_field.value = parts[0]
                building_field.value = parts[1] if len(parts) > 1 else ""
            else:
                city_field.value = ""
                street_field.value = rest
                building_field.value = ""
        
        # 郵便番号検索 (修正済みロジック)
        if pref_field.value and city_field.value:
            # 別スレッドで検索を実行
            page.run_thread(lambda: _search_zip_async(pref_field.value, city_field.value, street_field.value))

        page.update()

    def _search_zip_async(pref: str, city: str, street: str):
        """
        非同期で郵便番号検索を行う。
        誤検知を防ぐため、町域での検索のみを行い、市レベルでのフォールバックは行わない。
        """
        try:
            from src.services.deceased_service import search_zip_by_address_api
            
            zip_code = None
            
            # 1. 町域レベルでの検索
            if street:
                # 数字とハイフンを除去して町名を抽出
                match = re.match(r'^([^0-9\-\uFF10-\uFF19]+)', street)
                if match:
                    town_part = match.group(1).strip()
                    target = f"{pref}{city}{town_part}"
                    zip_code = search_zip_by_address_api(target)

            # 2. ヒットしなければフル住所
            if not zip_code:
                full = f"{pref}{city}{street}"
                zip_code = search_zip_by_address_api(full)
            
            # 💡 修正: ここにあった「市レベルでのフォールバック (fallback = f"{pref}{city}")」を削除
            # これにより、町名が一致しない場合に誤った代表番号がセットされるのを防ぐ

            if zip_code:
                zip_field.value = zip_code
                page.update()
        except Exception as ex:
            print(f"Auto zip search failed: {ex}")

    paste_address_field = TextField(
        label="📍 住所貼り付け (ここに入力すると自動分割されます)",
        width=600,
        on_change=parse_and_fill_address,
        text_size=13,
        color="onSecondaryContainer",
        bgcolor="secondaryContainer",
        border_color=Colors.TRANSPARENT
    )


    def save_and_go_back(e):
        collected_data = {
            "name": f"{name_last_field.value.strip()} {name_first_field.value.strip()}",
            "kana_last": kana_last_field.value.strip(),
            "kana_first": kana_first_field.value.strip(),
            "dob": dob_field.value.strip(),
            "rel": rel_field.value.strip(),
            "hometown": hometown_field.value.strip(),
            "zip_code": zip_field.value.strip(),
            "pref": pref_field.value.strip(),
            "city": city_field.value.strip(),
            "street": street_field.value.strip(),
            "building": building_field.value.strip(),
            "phone_contacts": collect_contacts(phone_inputs_column),
            "email_contacts": collect_contacts(email_inputs_column),
        }

        try:
            if is_new_heir:
                deceased_service.add_heir(
                    deceased_id=deceased_id,
                    name=collected_data["name"],
                    rel=collected_data["rel"],
                    kana_last=collected_data["kana_last"],
                    kana_first=collected_data["kana_first"],
                    dob=collected_data["dob"],
                    hometown=collected_data["hometown"],
                    zip_code=collected_data["zip_code"],
                    pref=collected_data["pref"],
                    city=collected_data["city"],
                    street=collected_data["street"],
                    building=collected_data["building"],
                    phone_contacts=collected_data["phone_contacts"],
                    email_contacts=collected_data["email_contacts"],
                )
            else:
                deceased_service.update_heir(
                    heir_id,
                    name=collected_data["name"],
                    rel=collected_data["rel"],
                    kana_last=collected_data["kana_last"],
                    kana_first=collected_data["kana_first"],
                    hometown=collected_data["hometown"],
                    zip_code=collected_data["zip_code"],
                    pref=collected_data["pref"],
                    city=collected_data["city"],
                    street=collected_data["street"],
                    building=collected_data["building"],
                    phone_contacts=collected_data["phone_contacts"],
                    email_contacts=collected_data["email_contacts"],
                )

            page.open(SnackBar(Text("保存しました"), bgcolor=Colors.PRIMARY))
            
            # 💡 修正: back_route を使用して遷移
            page.go(back_route)

        except Exception as ex:
            print(f"保存エラー: {ex}")
            page.open(SnackBar(Text(f"保存エラー: {ex}"), bgcolor=Colors.ERROR))
            page.update()

    # --- UI レイアウト ---
    return View(
        f"/heir_edit/{heir_id}?deceased_id={deceased_id}&case_id={case_id}",
        [
            AppBar(
                title=Text(title_text),
                bgcolor="surfaceVariant",
                color="onSurfaceVariant",
                # 💡 AppBarの戻るボタンにも back_route を適用
                leading=IconButton(Icons.ARROW_BACK, on_click=lambda e: page.go(back_route)),
            ),
            Container(
                padding=30,
                content=Column(
                    [
                        Text("👤 基本情報", weight=FontWeight.BOLD, size=16, color="onSurface"),
                        Row([name_last_field, name_first_field]),
                        Row([kana_last_field, kana_first_field]),
                        Row([rel_field], visible=True),
                        Divider(),
                        
                        Text("📅 生年月日", weight=FontWeight.BOLD, size=16, color="onSurface"),
                        Row(
                            [dob_field, wareki_dob_text],
                            vertical_alignment=CrossAxisAlignment.END,
                        ),
                        Divider(),
                        
                        Text("📞 連絡先情報", weight=FontWeight.BOLD, size=16, color="onSurface"),
                        Row(
                            [
                                Text("電話番号", size=14, weight=FontWeight.W_500),
                                IconButton(
                                    Icons.ADD,
                                    icon_color="primary",
                                    on_click=lambda e: add_new_contact_row(e, phone_inputs_column, False)
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        phone_inputs_column,
                        Row(
                            [
                                Text("メールアドレス", size=14, weight=FontWeight.W_500),
                                IconButton(
                                    Icons.ADD,
                                    icon_color="primary",
                                    on_click=lambda e: add_new_contact_row(e, email_inputs_column, True)
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        email_inputs_column,
                        Divider(),
                        
                        Text("🏠 住所", weight=FontWeight.BOLD, size=16, color="onSurface"),
                        # 💡 貼り付けフィールド
                        paste_address_field,
                        Row([zip_field, pref_field, city_field, street_field, building_field]),
                        Divider(),
                        Text("🏠 本籍地", weight=FontWeight.BOLD, size=16, color="onSurface"),
                        hometown_field,
                        Divider(),
                        
                        Row(
                            [
                                # 💡 修正: キャンセルボタンも back_route を使用
                                ElevatedButton(
                                    "キャンセル",
                                    on_click=lambda e: page.go(back_route),
                                    bgcolor="surfaceVariant",
                                    color="onSurfaceVariant"
                                ),
                                ElevatedButton(
                                    "保存して戻る",
                                    on_click=save_and_go_back,
                                    icon=Icons.SAVE,
                                    bgcolor="primary",
                                    color="onPrimary"
                                ),
                            ],
                            alignment=MainAxisAlignment.END,
                            spacing=15,
                        ),
                    ]
                ),
            ),
        ],
        scroll=ScrollMode.AUTO,
    )