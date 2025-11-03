# /components/pages/deceased_edit.py
from datetime import date

import requests
from flet import (
    AppBar,
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    Dropdown,
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
    dropdown,
)

from services import deceased_service
from services.db_setup import get_all_users, get_next_case_number
from services.deceased_service import (
    parse_all_flexible_date,  # 追加: 日付解析のため
)

# --- ユーティリティ関数（detail.pyからコピー） ---


def convert_seireki_to_wareki(date_obj: date) -> str:
    """西暦の日付オブジェクトを和暦文字列に変換する"""
    if not date_obj:
        return ""

    y, m, d = date_obj.year, date_obj.month, date_obj.day
    # 令和 (Reiwa)
    if y > 2019 or (y == 2019 and m >= 5 and d >= 1):
        gengo = "令和"
        wareki_year = y - 2018
    # 平成 (Heisei)
    elif y > 1989 or (y == 1989 and m >= 1 and d >= 8):
        gengo = "平成"
        wareki_year = y - 1988
    # 昭和 (Showa)
    elif y > 1926 or (y == 1926 and m >= 12 and d >= 25):
        gengo = "昭和"
        wareki_year = y - 1925
    # 大正 (Taisho)
    elif y > 1912 or (y == 1912 and m >= 7 and d >= 30):
        gengo = "大正"
        wareki_year = y - 1911
    else:
        return date_obj.isoformat()

    wareki_year_str = "元年" if wareki_year == 1 else str(wareki_year) + "年"
    return f"{gengo}{wareki_year_str}{m}月{d}日"


def on_date_blur_handler(e, wareki_text: Text):
    """TextFieldがフォーカスを失ったときに実行されるハンドラー。和暦表示を更新する (heir_edit.pyからコピー)"""
    input_value = e.control.value
    wareki_text.value = ""

    if not input_value:
        e.control.error_text = None
        wareki_text.update()
        e.control.update()
        return

    try:
        # parse_all_flexible_date は services.deceased_service からインポート済み
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

# 💡 担当者リスト (グローバルで一度ロード)
USER_MAP = get_all_users()
USER_OPTIONS = [dropdown.Option(str(id), name) for id, name in USER_MAP.items()]
USER_OPTIONS.insert(0, dropdown.Option("", "未割当"))


def DeceasedEditView(page: Page, deceased_id: int):
    """
    被相続人情報（および新規案件登録時の契約者情報）の編集を行う View
    :param deceased_id: 編集対象の Deceased ID (新規登録時は -1)
    """

    is_new_client_case = deceased_id == -1  # 新規案件（契約者登録）モード
    is_edit_mode = deceased_id > 0  # 既存の被相続人編集モード

    # 既存データまたはダミーデータのロード
    data = None
    case = None
    address_info = {}
    contacts = []

    if is_edit_mode:
        data = deceased_service.get_deceased_by_id(deceased_id)
        if not data:
            return View(
                f"/deceased_edit/{deceased_id}", [Text("データが見つかりません。")]
            )
        case = data.case
        address_info = deceased_service.get_address_info("deceased", deceased_id)
        # Deceasedの連絡先は現在サービス層から取得できないため、空のまま
        contacts = []

    elif is_new_client_case:
        # 新規契約者登録モード（被相続人データは空、契約者データ（Heir）として入力させる）
        data = None
        case = None
        address_info = {}
        contacts = []

    else:  # deceased_id == 0 の単独新規被相続人登録は、このルーティングで処理しない想定だが、エラー回避のため
        return View(f"/deceased_edit/{deceased_id}", [Text("無効なIDです。")])

    # --- フォームコントロールの定義（ローカル変数として） ---

    # 案件・担当者
    case_number_field = TextField(
        label="案件番号",
        value=get_next_case_number()
        if is_new_client_case
        else (case.case_number if case else ""),
        width=250,
        visible=is_new_client_case,  # 新規登録時のみ表示
    )
    manager_field = Dropdown(
        label="担当者1 (進捗管理)",
        width=200,
        options=USER_OPTIONS,
        value=str(case.manager_id) if case and case.manager_id else "",
        visible=is_new_client_case,  # 新規登録時のみ表示
    )
    operator_field = Dropdown(
        label="担当者2 (実務担当)",
        width=200,
        options=USER_OPTIONS,
        value=str(case.operator_id) if case and case.operator_id else "",
        visible=is_new_client_case,  # 新規登録時のみ表示
    )

    # 基本情報
    name_last_field = TextField(
        label="氏名 (姓)",
        width=150,
        autofocus=True,
        value=data.name_last if is_edit_mode and data else "",
    )
    name_first_field = TextField(
        label="氏名 (名)",
        width=150,
        value=data.name_first if is_edit_mode and data else "",
    )
    kana_last_field = TextField(
        label="ふりがな (姓)",
        width=150,
        value=data.name_last_kana
        if is_edit_mode and data and data.name_last_kana
        else "",
    )
    kana_first_field = TextField(
        label="ふりがな (名)",
        width=150,
        value=data.name_first_kana
        if is_edit_mode and data and data.name_first_kana
        else "",
    )
    rel_field = TextField(
        label="続柄",
        width=200,
        value=data.relationship_type
        if is_edit_mode and data
        else ("" if is_new_client_case else "本人"),
        visible=is_new_client_case,  # 新規契約者登録時のみ表示
    )

    # 日付フィールドと和暦表示のセットアップ
    dob_date = data.date_of_birth if is_edit_mode and data else None
    dod_date = data.date_of_death if is_edit_mode and data else None

    wareki_dob_text = Text(
        value=convert_seireki_to_wareki(dob_date),
        width=250,
        color=Colors.BLUE_GREY_600,
        weight=FontWeight.W_500,
    )

    def dob_blur(e):
        on_date_blur_handler(e, wareki_dob_text)
        page.update()  # on_date_blur_handler 内でも page.update() は必要だが、明示的に呼ぶ

    dob_field = TextField(
        label="生年月日 (YYYY-MM-DD)",
        width=180,
        value=str(dob_date) if dob_date else "",
        on_blur=dob_blur,  # 💡 ラムダ式をやめて関数参照に
    )

    wareki_dod_text = Text(
        value=convert_seireki_to_wareki(dod_date),
        width=250,
        color=Colors.BLUE_GREY_600,
        weight=FontWeight.W_500,
    )
    dod_field = TextField(
        label="死亡日 (YYYY-MM-DD)",
        width=180,
        value=str(dod_date) if dod_date else "",
        on_blur=lambda e: (
            dod_field.value,
            wareki_dod_text.value,
            on_date_blur_handler(e, wareki_dod_text),
            page.update(),
        ),
        visible=not is_new_client_case,  # 新規契約者登録時は死亡日は入力させない
    )

    # 住所フィールド
    hometown_field = TextField(
        label="本籍地 (全体)",
        value=data.hometown if is_edit_mode and data and data.hometown else "",
    )
    zip_field = TextField(
        label="郵便番号", width=150, value=address_info.get("zip_code", "")
    )
    pref_field = TextField(
        label="都道府県", width=150, value=address_info.get("prefecture", "")
    )
    city_field = TextField(
        label="市区町村", width=200, value=address_info.get("city_ward_town", "")
    )
    street_field = TextField(
        label="番地", width=150, value=address_info.get("street_address", "")
    )
    building_field = TextField(
        label="建物名・部屋番号", value=address_info.get("building_name", "")
    )

    # --- 連絡先動的フォームのセットアップ ---

    def create_contact_input_row(
        column_container: Column, initial_value="", is_email=False
    ):
        """電話またはメールの入力行と削除ボタンを作成する"""

        def remove_row(e):
            if row in column_container.controls:
                column_container.controls.remove(row)
                column_container.update()
                e.page.update()

        value_field = TextField(
            label="メールアドレス" if is_email else "電話番号",
            value=initial_value,
            width=500 if is_email else 350,
        )

        row = Row(
            [
                value_field,
                IconButton(
                    icon=Icons.DELETE,
                    icon_color=Colors.RED_500,
                    on_click=remove_row,
                    tooltip="削除",
                ),
            ],
            alignment=MainAxisAlignment.START,
        )

        return row, value_field

    def add_new_contact_row(e, column_container: Column, is_email: bool):
        """ボタンクリックで新しい入力行を追加する"""
        new_row, new_field = create_contact_input_row(
            column_container, is_email=is_email
        )
        column_container.controls.append(new_row)
        column_container.update()
        new_field.focus()
        e.page.update()

    phone_inputs_column = Column(controls=[], spacing=5)
    email_inputs_column = Column(controls=[], spacing=5)

    # 新規契約者登録の場合、デフォルトで空の連絡先入力行を1つずつ追加
    if is_new_client_case:
        new_phone_row, _ = create_contact_input_row(phone_inputs_column, is_email=False)
        phone_inputs_column.controls.append(new_phone_row)
        new_email_row, _ = create_contact_input_row(email_inputs_column, is_email=True)
        email_inputs_column.controls.append(new_email_row)

    # --- 住所自動入力ロジック（detail.pyからコピー） ---

    def search_address_by_zip(e):
        zip_code = zip_field.value.replace("-", "").strip()
        if len(zip_code) == 7 and zip_code.isdigit():
            try:
                api_url = f"https://zipcloud.ibsnet.co.jp/api/search?zipcode={zip_code}"
                response = requests.get(api_url)
                data_json = response.json()
                if data_json and data_json.get("results"):
                    address_data = data_json["results"][0]
                    pref_field.value = address_data["address1"]
                    city_field.value = address_data["address2"]
                    street_field.value = address_data["address3"]
                    page.update()
                else:
                    pref_field.value = "住所が見つかりません"
                    city_field.value = ""
                    street_field.value = ""
                    page.update()
            except Exception as ex:
                print(f"APIエラー: {ex}")
        street_field.focus()

    zip_field.on_blur = search_address_by_zip

    # --- 保存処理 ---
    def save_and_go_back(e):
        # 1. データ収集
        def collect_contacts(column: Column):
            contacts = []
            for row in column.controls:
                # 連絡先入力行であることを確認
                if (
                    isinstance(row, Row)
                    and len(row.controls) >= 2
                    and isinstance(row.controls[0], TextField)
                ):
                    value = row.controls[0].value.strip()
                    # 種別は「Primary」固定
                    sub_type = "Primary"

                    if value:
                        contacts.append({"value": value, "sub_type": sub_type})
            return contacts

        # フォーム値の取得
        collected_data = {
            "name": f"{name_last_field.value.strip()} {name_first_field.value.strip()}",
            "kana_last": kana_last_field.value.strip(),
            "kana_first": kana_first_field.value.strip(),
            "dob": dob_field.value.strip(),
            "dod": dod_field.value.strip(),
            "hometown": hometown_field.value.strip(),
            "zip_code": zip_field.value.strip(),
            "pref": pref_field.value.strip(),
            "city": city_field.value.strip(),
            "street": street_field.value.strip(),
            "building": building_field.value.strip(),
            "phone_contacts": collect_contacts(phone_inputs_column),
            "email_contacts": collect_contacts(email_inputs_column),
            "rel": rel_field.value.strip()
            if is_new_client_case
            else "本人",  # 新規契約者のみ続柄を保存
            "case_number": case_number_field.value.strip(),
            "manager_id": int(manager_field.value) if manager_field.value else None,
            "operator_id": int(operator_field.value) if operator_field.value else None,
        }

        new_id = deceased_id

        # 2. サービス層呼び出し
        try:
            if is_new_client_case:
                # 案件新規登録
                new_id = deceased_service.add_new_case_for_client_registration(
                    case_number=collected_data["case_number"],
                    name=collected_data["name"],
                    kana_last=collected_data["kana_last"],
                    kana_first=collected_data["kana_first"],
                    rel=collected_data["rel"],
                    hometown=collected_data["hometown"],
                    zip_code=collected_data["zip_code"],
                    pref=collected_data["pref"],
                    city=collected_data["city"],
                    street=collected_data["street"],
                    building=collected_data["building"],
                    dob=collected_data["dob"],
                    dod=collected_data["dod"],
                    manager_id=collected_data["manager_id"],
                    operator_id=collected_data["operator_id"],
                    phone_contacts=collected_data["phone_contacts"],
                    email_contacts=collected_data["email_contacts"],
                )
                if new_id < 1:
                    raise Exception("新規案件登録に失敗しました。")

            elif is_edit_mode:
                # 既存被相続人情報更新
                # update_deceased 関数が hometown を受け付けるように services/deceased_service.py を修正済み
                deceased_service.update_deceased(
                    deceased_id,
                    name=collected_data["name"],
                    kana_last=collected_data["kana_last"],
                    kana_first=collected_data["kana_first"],
                    dob=collected_data["dob"],
                    dod=collected_data["dod"],
                    hometown=collected_data["hometown"],  # 追加
                    zip_code=collected_data["zip_code"],
                    pref=collected_data["pref"],
                    city=collected_data["city"],
                    street=collected_data["street"],
                    building=collected_data["building"],
                    # 連絡先更新ロジックは update_deceased 側にないため、ここでは除外
                )

            # 3. 成功通知と画面遷移
            page.open(
                SnackBar(
                    content=Text("情報を保存しました。", color=Colors.WHITE),
                    bgcolor=Colors.GREEN_700,
                    duration=1500,
                )
            )
            # 詳細ページに戻る
            page.go(f"/detail/{new_id}")

        except Exception as ex:
            print(f"保存エラー: {ex}")
            page.open(
                SnackBar(
                    content=Text(
                        f"保存中にエラーが発生しました: {ex}", color=Colors.WHITE
                    ),
                    bgcolor=Colors.RED_700,
                    duration=3000,
                )
            )
            page.update()

    # --- UIレイアウト構築 ---

    title_text = (
        "新規案件登録（契約者情報）" if is_new_client_case else "被相続人情報 編集"
    )
    current_deceased_id = deceased_id if is_edit_mode else (data.id if data else -1)

    # 戻るボタンの遷移先
    back_route = f"/detail/{current_deceased_id}"

    return View(
        f"/deceased_edit/{deceased_id}",
        [
            AppBar(
                title=Text(title_text),
                bgcolor=Colors.BLUE_GREY_700,
                # 戻るボタンを追加
                leading=IconButton(
                    Icons.ARROW_BACK, on_click=lambda e: page.go(back_route)
                ),
            ),
            Container(
                padding=30,
                content=Column(
                    [
                        # 案件情報セクション (新規登録時のみ)
                        Row(
                            [
                                Column([case_number_field]),
                                Column([manager_field, Text("担当者1")]),
                                Column([operator_field, Text("担当者2")]),
                            ],
                            visible=is_new_client_case,
                        ),
                        Divider(visible=is_new_client_case),
                        # 基本情報セクション
                        Text("👤 基本情報", weight=FontWeight.BOLD, size=16),
                        Row([name_last_field, name_first_field]),
                        Row([kana_last_field, kana_first_field]),
                        Row(
                            [rel_field], visible=is_new_client_case
                        ),  # 続柄フィールド（新規契約者のみ）
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
                                Text(
                                    "メールアドレス", size=14, weight=FontWeight.W_500
                                ),
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
                        # 日付情報セクション
                        Text("📅 日付情報", weight=FontWeight.BOLD, size=16),
                        Row(
                            [dob_field, wareki_dob_text],
                            vertical_alignment=CrossAxisAlignment.END,
                        ),
                        Row(
                            [dod_field, wareki_dod_text],
                            vertical_alignment=CrossAxisAlignment.END,
                            visible=not is_new_client_case,
                        ),
                        Divider(),
                        # 住所情報セクション
                        Text("🏠 住所・本籍地", weight=FontWeight.BOLD, size=16),
                        hometown_field,
                        Row([zip_field, pref_field, city_field]),
                        Row([street_field, building_field]),
                        Divider(),
                        # 保存・キャンセルボタン
                        Row(
                            [
                                ElevatedButton(
                                    "キャンセル", on_click=lambda e: page.go(back_route)
                                ),
                                ElevatedButton(
                                    "保存して戻る",
                                    on_click=save_and_go_back,
                                    icon=Icons.SAVE,
                                    bgcolor=Colors.BLUE_600,
                                ),
                            ],
                            # alignment=MainAxisAlignment.END,
                            spacing=15,
                        ),
                    ]
                ),
            ),
        ],
        scroll=ScrollMode.AUTO,
    )
