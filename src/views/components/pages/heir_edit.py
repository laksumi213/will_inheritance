# components/pages/heir_edit.py
from datetime import date

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

from components.utils.contact_controls import (
    add_new_contact_row,  # 💡 行追加用の共通関数
    collect_contacts,  # 💡 データ収集用の共通関数
    create_contact_input_row,  # 💡 UI生成用の共通関数
)
from services import deceased_service
from services.deceased_service import (
    get_address_info,
    get_case_id_by_deceased_id,
    get_heir_by_id,
    parse_all_flexible_date,
)

# --- ユーティリティ関数 ---


def convert_seireki_to_wareki(date_obj: date) -> str:
    """西暦の日付オブジェクトを和暦文字列に変換する"""
    if not date_obj:
        return ""

    y, m, d = date_obj.year, date_obj.month, date_obj.day
    # 令和 (Reiwa): 2019-05-01 から
    if y > 2019 or (y == 2019 and m >= 5 and d >= 1):
        gengo = "令和"
        wareki_year = y - 2018
    # 平成 (Heisei): 1989-01-08 から
    elif y > 1989 or (y == 1989 and m >= 1 and d >= 8):
        gengo = "平成"
        wareki_year = y - 1988
    # 昭和 (Showa): 1926-12-25 から
    elif y > 1926 or (y == 1926 and m >= 12 and d >= 25):
        gengo = "昭和"
        wareki_year = y - 1925
    # 大正 (Taisho): 1912-07-30 から
    elif y > 1912 or (y == 1912 and m >= 7 and d >= 30):
        gengo = "大正"
        wareki_year = y - 1911
    else:
        return date_obj.isoformat()

    wareki_year_str = "元年" if wareki_year == 1 else str(wareki_year) + "年"
    return f"{gengo}{wareki_year_str}{m}月{d}日"


def on_date_blur_handler(e, wareki_text: Text):
    """TextFieldがフォーカスを失ったときに実行されるハンドラー。和暦表示を更新する"""
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
        on_blur=lambda e: (
            dob_field.value,
            wareki_dob_text.value,
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

    # 💡 共通コントロールの Column を初期化
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
                # 💡 共通関数を使用
                new_row, _ = create_contact_input_row(
                    column, initial_value=c["value"], is_email=is_email
                )
                column.controls.append(new_row)
        else:
            # データがない場合はデフォルトで1行追加
            new_row, _ = create_contact_input_row(column, is_email=is_email)
            column.controls.append(new_row)

    # 初期化実行
    initialize_contact_controls(contacts, phone_inputs_column, False)
    initialize_contact_controls(contacts, email_inputs_column, True)

    # --- 住所自動入力ロジック ---
    # 💡 [推奨] 共通サービスラッパーの利用に置き換えを推奨しますが、ここでは既存の requests ロジックを維持します。

    def search_address_by_zip(e):
        """郵便番号に基づいて住所を自動入力する（サービスラッパー利用）"""

        zip_code = zip_field.value  # TextFieldから郵便番号を取得

        # 1. サービス層の API 呼び出し関数を使用
        address_info = deceased_service.search_address_by_zip_api(zip_code)

        if address_info is None:
            # 通信エラーや不正な形式の場合（サービス内でエラー処理済み）
            pref_field.value = "通信エラー、または無効な郵便番号です"
            city_field.value = ""
            street_field.value = ""
        elif address_info == {}:
            # 住所が見つからなかった場合（API通信は成功）
            pref_field.value = "住所が見つかりません"
            city_field.value = ""
            street_field.value = ""
        else:
            # 成功した場合、ローカルのUIコントロールを更新
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
            "phone_contacts": collect_contacts(phone_inputs_column),  # 💡 共通関数を使用
            "email_contacts": collect_contacts(email_inputs_column),  # 💡 共通関数を使用
        }

        # 2. サービス層呼び出し
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

            # 3. 成功通知と画面遷移
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

    # --- UIレイアウト構築 ---

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
                                    # 💡 共通関数を使用
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
                                    # 💡 共通関数を使用
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
                        # Row([street_field, building_field]),
                        Divider(),
                        Text("🏠 本籍地", weight=FontWeight.BOLD, size=16),
                        hometown_field,
                        Divider(),
                        # 保存・キャンセルボタン
                        Row(
                            [
                                ElevatedButton(
                                    "キャンセル",
                                    on_click=lambda e: page.go(
                                        back_route
                                    ),  # 💡 [修正済み] TypeErrorを解消
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
