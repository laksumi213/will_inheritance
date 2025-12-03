# src/views/heir_edit.py
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

# 💡 修正: UI部品は src/views/components からインポート
from src.views.components.contact_controls import (
    add_new_contact_row,
    collect_contacts,
    create_contact_input_row,
)
# 💡 修正: ユーティリティは src/utils からインポート
from src.utils.date_utils import (
    convert_seireki_to_wareki,
    parse_all_flexible_date,
    on_date_blur_handler,
)

# サービス層からのインポート
from src.services import deceased_service
from src.services.deceased_service import (
    get_address_info,
    get_case_id_by_deceased_id,
    get_heir_by_id,
)

# --- メインの編集ビュー関数 ---

def HeirEditView(page: Page, heir_id: int, deceased_id: int):
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
            return View(f"/heir_edit/{heir_id}", [Text("相続人データが見つかりません。")])

        deceased_id = data.deceased_id
        address_info = get_address_info("heir", heir_id)
        contacts = deceased_service.get_contact_info("heir", heir_id)

    # --- フォームコントロールの定義 ---

    title_suffix = f" (被相続人ID: {deceased_id})" if deceased_id else ""
    title_text = (
        f"新しい相続人情報 新規登録{title_suffix}"
        if is_new_heir
        else f"相続人情報 編集{title_suffix}"
    )

    name_last_field = TextField(
        label="氏名 (姓)",
        width=150,
        autofocus=True,
        value=data.name_last if data else "",
    )
    name_first_field = TextField(
        label="氏名 (名)", width=150, value=data.name_first if data else ""
    )
    kana_last_field = TextField(
        label="ふりがな (姓)",
        width=150,
        value=data.name_last_kana if data and data.name_last_kana else "",
    )
    kana_first_field = TextField(
        label="ふりがな (名)",
        width=150,
        value=data.name_first_kana if data and data.name_first_kana else "",
    )
    rel_field = TextField(label="続柄", width=200, value=data.relationship_type if data else "")
    hometown_field = TextField(
        label="本籍地", value=data.hometown if data and data.hometown else ""
    )

    # 日付フィールドと和暦表示のセットアップ
    dob_date = data.date_of_birth if data else None

    wareki_dob_text = Text(
        value=convert_seireki_to_wareki(dob_date),
        width=250,
        color=Colors.BLUE_GREY_600,
        weight=FontWeight.W_500,
    )
    dob_field = TextField(
        label="生年月日 (YYYY-MM-DD)",
        width=180,
        value=str(dob_date) if dob_date else "",
        # on_blur ハンドラを直接使用
        on_blur=lambda e: (
            on_date_blur_handler(e, wareki_dob_text),
            page.update(),
        ),
    )

    # 住所フィールド
    zip_field = TextField(label="郵便番号", width=150, value=address_info.get("zip_code", ""))
    pref_field = TextField(label="都道府県", width=150, value=address_info.get("prefecture", ""))
    city_field = TextField(
        label="市区町村", width=200, value=address_info.get("city_ward_town", "")
    )
    street_field = TextField(label="番地", width=150, value=address_info.get("street_address", ""))
    building_field = TextField(
        label="建物名・部屋番号", value=address_info.get("building_name", "")
    )

    # --- 連絡先動的フォームの初期化 ---

    phone_inputs_column = Column(controls=[], spacing=5)
    email_inputs_column = Column(controls=[], spacing=5)

    def initialize_contact_controls(contact_list, column: Column, is_email: bool):
        """連絡先データをロードし、UIコントロールを初期化する"""
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

    # 初期化実行
    initialize_contact_controls(contacts, phone_inputs_column, False)
    initialize_contact_controls(contacts, email_inputs_column, True)

    # --- 住所自動入力ロジック ---

    def search_address_by_zip(e):
        """郵便番号に基づいて住所を自動入力する（サービスラッパー利用）"""

        zip_code = zip_field.value  # TextFieldから郵便番号を取得
        address_info = deceased_service.search_address_by_zip_api(zip_code)

        if address_info is None:
            pref_field.value = "通信エラー、または無効な郵便番号です"
            city_field.value = ""
            street_field.value = ""
        elif address_info == {}:
            pref_field.value = "住所が見つかりません"
            city_field.value = ""
            street_field.value = ""
        else:
            pref_field.value = address_info.get("prefecture", "")
            city_field.value = address_info.get("city_ward_town", "")
            street_field.value = address_info.get("street_address", "")

        page.update()
        street_field.focus()  # 最後に番地フィールドにフォーカスを移動

    zip_field.on_blur = search_address_by_zip

    # --- 保存処理 ---
    def save_and_go_back(e):
        # フォーム値の取得
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
            "phone_contacts": collect_contacts(phone_inputs_column),  # 共通関数を使用
            "email_contacts": collect_contacts(email_inputs_column),  # 共通関数を使用
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

            # 成功通知と画面遷移
            page.open(
                SnackBar(
                    content=Text("相続人情報を保存しました。", color=Colors.WHITE),
                    bgcolor=Colors.GREEN_700,
                    duration=1500,
                )
            )
            # 詳細ページに戻る
            case_id = get_case_id_by_deceased_id(deceased_id)
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

    # 戻り先ルートの確定
    back_route = f"/detail/{deceased_id}"

    return View(
        f"/heir_edit/{heir_id}?deceased_id={deceased_id}",
        [
            AppBar(
                title=Text(title_text),
                bgcolor=Colors.BLUE_GREY_700,
                leading=IconButton(Icons.ARROW_BACK, on_click=lambda e: page.go(back_route)),
            ),
            Container(
                padding=30,
                content=Column(
                    [
                        # 基本情報セクション
                        Text("👤 基本情報", weight=FontWeight.BOLD, size=16),
                        Row([name_last_field, name_first_field]),
                        Row([kana_last_field, kana_first_field]),
                        Row([rel_field], visible=True),
                        Divider(),
                        # 日付情報セクション
                        Text("📅 生年月日", weight=FontWeight.BOLD, size=16),
                        Row(
                            [dob_field, wareki_dob_text],
                            vertical_alignment=CrossAxisAlignment.END,
                        ),
                        Divider(),
                        # 連絡先情報セクション
                        Text("📞 連絡先情報", weight=FontWeight.BOLD, size=16),
                        Row(
                            [
                                Text("電話番号", size=14, weight=FontWeight.W_500),
                                ElevatedButton(
                                    "追加",
                                    icon=Icons.ADD,
                                    on_click=lambda e: add_new_contact_row(
                                        e, phone_inputs_column, is_email=False
                                    ),
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        phone_inputs_column,
                        Row(
                            [
                                Text("メールアドレス", size=14, weight=FontWeight.W_500),
                                ElevatedButton(
                                    "追加",
                                    icon=Icons.ADD,
                                    on_click=lambda e: add_new_contact_row(
                                        e, email_inputs_column, is_email=True
                                    ),
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        email_inputs_column,
                        Divider(),
                        # 住所情報セクション
                        Text("🏠 住所", weight=FontWeight.BOLD, size=16),
                        Row([zip_field, pref_field, city_field, street_field, building_field]),
                        Divider(),
                        Text("🏠 本籍地", weight=FontWeight.BOLD, size=16),
                        hometown_field,
                        Divider(),
                        # 保存・キャンセルボタン
                        Row(
                            [
                                ElevatedButton(
                                    "キャンセル",
                                    on_click=lambda e: page.go(back_route),
                                ),
                                ElevatedButton(
                                    "保存して戻る",
                                    on_click=save_and_go_back,
                                    icon=Icons.SAVE,
                                    bgcolor=Colors.BLUE_600,
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