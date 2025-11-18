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
from services import deceased_service
from services.deceased_service import (
    parse_all_flexible_date,
    search_address_by_zip_api,
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


# ------------------------------------------------------------------
# UI ヘルパーロジック
# ------------------------------------------------------------------


def update_wareki_display(date_field: TextField, wareki_text: Text):
    """日付フィールドの値に基づいて和暦表示を更新するヘルパー関数"""
    input_value = date_field.value.strip()
    wareki_text.value = ""
    date_field.error_text = None

    if not input_value:
        # update() は呼び出し元で行う
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

    # update() は呼び出し元で行う


# 🎯 on_date_blur_handler はクロージャとして使用されるため、eventオブジェクト e のみを受け取る
def on_date_blur_handler(e, wareki_text: Text):
    """TextFieldがフォーカスを失ったときに実行されるハンドラー。和暦表示を更新する。"""
    update_wareki_display(e.control, wareki_text)
    e.control.update()
    e.page.update()


def create_address_fields(is_last: bool, data: dict = None):
    """住所入力フィールドセットを作成するヘルパー関数"""
    prefix = "最後の住所" if is_last else "過去の住所"

    # データが存在しない場合のデフォルト値
    data = data if data is not None else {}

    # 💡 is_last=True の場合は、グローバルに定義されたフィールドの参照を返す
    if is_last:
        # グローバルフィールドの値を更新
        last_zip_field.value = data.get("zip_code", "")
        last_pref_field.value = data.get("prefecture", "")
        last_city_field.value = data.get("city_ward_town", "")
        last_street_field.value = data.get("street_address", "")
        last_building_field.value = data.get("building_name", "")

        # 💡 ここで field のリストを返すだけで、Viewにコントロールを追加する処理は不要。
        #    メインのレイアウトで既に last_address_controls が参照されているため。
        return [ 
            last_zip_field,
            last_pref_field,
            last_city_field,
            last_street_field,
            last_building_field,
        ]

    # 💡 is_last=False (過去の住所) の場合は、新しいコントロールを動的に作成
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
        # 過去の住所は手動入力も許可するため read_only=False (または省略)
        value=data.get("prefecture", ""),
        color=Colors.BLACK,
        label_style=TextStyle(color=Colors.BLACK54),
    )
    city_field = TextField(
        label=f"{prefix} 市区町村 *",
        width=200,
        # 過去の住所は手動入力も許可するため read_only=False (または省略)
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

    # 過去の住所の削除ボタン
    delete_button = IconButton(
        Icons.DELETE_OUTLINE,
        icon_color=Colors.RED_400,
        tooltip="この過去の住所を削除",
    )

    # 住所入力セット全体をColumnでラップし、削除ボタンを含める
    control_set = Column(
        controls=[
            # Row([zip_field, pref_field, city_field], spacing=10),
            # Row(
            #     [street_field, building_field, delete_button],
            #     vertical_alignment=CrossAxisAlignment.END,
            #     spacing=10,
            # ),
            Row(
                [zip_field, pref_field, city_field, street_field, building_field, delete_button],
                spacing=10,
            ),
            # Divider(height=1, color=Colors.GREY_300),
        ],
        data={"is_last": is_last, "id": data.get("address_id", None)},
        spacing=10,
    )

    # 削除ボタンのハンドラを定義
    def delete_past_address(e):
        # UIからコントロールを削除
        past_addresses_column.controls.remove(control_set)
        e.page.update()

    delete_button.on_click = delete_past_address

    # 過去の住所フィールドにも郵便番号ハンドラを動的に割り当てる
    zip_field.on_blur = lambda event: address_zip_handler(event, pref_field, city_field)

    return control_set


def address_zip_handler(e, pref_field: TextField, city_field: TextField):
    """郵便番号を入力した際の住所自動検索ハンドラ"""
    zip_code = e.control.value.strip()

    # 郵便番号のフォーマットチェック（ここでは簡易的に桁数のみ）
    if len(zip_code.replace("-", "")) < 7:
        # 短い場合は検索しない
        return

    address_info = search_address_by_zip_api(zip_code)

    if address_info:
        pref_field.value = address_info.get("prefecture", "")
        city_field.value = address_info.get("city_ward_town", "")
        e.control.error_text = None
    else:
        # 住所が見つからなかった場合
        # 最後の住所（都道府県/市区町村がread_only）の場合のみエラー表示とクリア
        if pref_field.read_only:
            pref_field.value = ""
            city_field.value = ""
            e.control.error_text = "住所が見つかりません"
        # 過去の住所（read_onlyでない）は手動入力の可能性を残すため、クリアしない

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

    # 💡 case_id -1/0 の場合は新規モードとして扱う
    is_new_mode = deceased is None or target_id < 1
    current_deceased_id = deceased.id if deceased else None

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

            # 住所履歴を取得
            address_history = deceased_service.get_deceased_address_history(current_deceased_id)

            past_addresses_column.controls.clear()

            # 最後の住所と過去の住所を分離してロード
            for addr in address_history:
                # 💡 create_address_fields を使用してフィールドに値を設定
                if addr["is_last_address"]:
                    # 最後の住所はグローバルフィールドに直接値を設定 (create_address_fields で値設定の処理を一本化)
                    # 💡 create_address_fields(is_last=True, data=addr) を呼び出すことで、
                    #    グローバルフィールドに値が設定され、かつ冗長なコードを避ける。
                    create_address_fields(is_last=True, data=addr) # <- これを呼び出す
                    
                    # ↓ 冗長な直接代入は削除またはコメントアウト
                    # last_zip_field.value = addr["zip_code"]
                    # last_pref_field.value = addr["prefecture"]
                    # last_city_field.value = addr["city_ward_town"]
                    # last_street_field.value = addr["street_address"]
                    # last_building_field.value = addr["building_name"]
                else:
                    # 過去の住所を動的リストにロード
                    control_set = create_address_fields(is_last=False, data=addr)
                    past_addresses_column.controls.append(control_set)

            # # 最後の住所と過去の住所を分離してロード
            # for addr in address_history:
            #     # 💡 create_address_fields を使用してフィールドに値を設定
            #     if addr["is_last_address"]:
            #         # 最後の住所はグローバルフィールドに直接値を設定
            #         last_zip_field.value = addr["zip_code"]
            #         last_pref_field.value = addr["prefecture"]
            #         last_city_field.value = addr["city_ward_town"]
            #         last_street_field.value = addr["street_address"]
            #         last_building_field.value = addr["building_name"]
            #     else:
            #         # 過去の住所を動的リストにロード
            #         control_set = create_address_fields(is_last=False, data=addr)
            #         past_addresses_column.controls.append(control_set)

        # 💡 新規モードの場合はフィールドをクリアしておく
        elif is_new_mode:
            # is_new_modeの場合は、reset_fields(None)を呼び出す代わりに、
            # 必要なフィールドだけをクリアまたは初期設定を保証する
            reset_fields(None)  # 全フィールドをリセット

        page.update()

    # ----------------------------------------------------
    # 住所履歴 UI 操作ロジック
    # ----------------------------------------------------

    def add_past_address(e):
        """新しい過去の住所入力フィールドセットを追加する"""
        new_address_set = create_address_fields(is_last=False, data={})
        past_addresses_column.controls.append(new_address_set)
        page.update()

    def save_data(e):
        """データを収集し、サービス層に渡して保存・更新する"""

        nonlocal current_deceased_id

        # 1. データの収集とバリデーション
        name_last = dialog_name_last_field.value.strip()
        name_first = dialog_name_first_field.value.strip()
        full_name = f"{name_last} {name_first}".strip()

        if not name_last or not name_first:
            page.open(
                SnackBar(
                    content=Text("氏名（姓）と氏名（名）は必須項目です。", color=Colors.WHITE),
                    bgcolor=Colors.RED_700,
                )
            )
            page.update()
            return

        # 2. 過去の住所データを UI コントロールから収集 (is_last=False のみ)
        collected_past_addresses = []
        for control_set in past_addresses_column.controls:
            # control_set は Column。その controls[0] が Row 
            
            # UIからのデータが空の Column でなければ処理を継続
            if not control_set.controls:
                continue

            addr_row = control_set.controls[0] 
            
            # 💡 コントロールのインデックスを新しいRow構成で確認
            # [0]zip, [1]pref, [2]city, [3]street, [4]building, [5]delete_button (削除ボタンがある場合)
            if len(addr_row.controls) < 5: 
                continue # 最低限のコントロール数チェック

            zip_code = addr_row.controls[0].value.strip() 
            prefecture = addr_row.controls[1].value.strip() 
            city_ward_town = addr_row.controls[2].value.strip() 
            street_address = addr_row.controls[3].value.strip() 
            building_name = addr_row.controls[4].value.strip() 

            # 過去の住所として有効なデータのみを収集 (都道府県と番地は必須とする)
            if prefecture and street_address:
                collected_past_addresses.append(
                    {
                        "zip_code": zip_code,
                        "prefecture": prefecture,
                        "city_ward_town": city_ward_town,
                        "street_address": street_address,
                        "building_name": building_name,
                        "is_last_address": False,
                        "address_id": control_set.data.get("id", None),  # 既存のAddress IDを渡す
                    }
                )

        try:
            # 3. 保存・更新処理
            # ... (中略：引数を渡し、サービス関数を呼び出す) ...
            deceased_service.update_deceased(
                deceased_id=current_deceased_id,
                name_last=dialog_name_last_field.value.strip() or None,  # 姓
                name_first=dialog_name_first_field.value.strip() or None,  # 名
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
            )
        # for control_set in past_addresses_column.controls:
        #     # Column(Row([zip, pref, city]), Row([street, building, delete])) の構造を仮定
        #     addr_row_1 = control_set.controls[0]
        #     addr_row_2 = control_set.controls[1]

        #     zip_code = addr_row_1.controls[0].value.strip()
        #     prefecture = addr_row_1.controls[1].value.strip()
        #     city_ward_town = addr_row_1.controls[2].value.strip()
        #     street_address = addr_row_2.controls[0].value.strip()
        #     building_name = addr_row_2.controls[1].value.strip()

        #     # 過去の住所として有効なデータのみを収集 (都道府県と番地は必須とする)
        #     if prefecture and street_address:
        #         collected_past_addresses.append(
        #             {
        #                 "zip_code": zip_code,
        #                 "prefecture": prefecture,
        #                 "city_ward_town": city_ward_town,
        #                 "street_address": street_address,
        #                 "building_name": building_name,
        #                 "is_last_address": False,  # 明示的にFalseを設定
        #                 "address_id": control_set.data.get("id", None),  # 既存のIDがあれば渡す
        #             }
        #         )

        # try:
        #     # 3. 保存・更新処理

        #     if is_new_mode:
        #         # 新規登録モードでは、まず Deceased と Case を作成
        #         new_id = deceased_service.add_deceased(full_name, dialog_dob_field.value)
        #         current_deceased_id = new_id

        #         if current_deceased_id <= 0:
        #             raise Exception("被相続人の登録に失敗しました。")

        #         # 新規登録時は、最後に update_deceased で残りの情報と住所を登録

        #     # 既存データ更新、または新規登録後の追加情報登録
        #     deceased_service.update_deceased(
        #         deceased_id=current_deceased_id,
        #         name_last=dialog_name_last_field.value.strip() or None,  # 姓
        #         name_first=dialog_name_first_field.value.strip() or None,  # 名
        #         dob=dialog_dob_field.value,
        #         dod=dialog_dod_field.value or None,
        #         kana_last=dialog_kana_last_field.value.strip() or None,
        #         kana_first=dialog_kana_first_field.value.strip() or None,
        #         hometown=dialog_hometown_field.value.strip() or None,
        #         # 最後の住所
        #         last_zip_code=last_zip_field.value.strip() or None,
        #         last_pref=last_pref_field.value.strip() or None,
        #         last_city=last_city_field.value.strip() or None,
        #         last_street=last_street_field.value.strip() or None,
        #         last_building=last_building_field.value.strip() or None,
        #         # 過去の住所リスト
        #         past_addresses=collected_past_addresses,
        #     )

            # 成功後の遷移
            page.open(
                SnackBar(
                    content=Text("被相続人情報を保存しました。", color=Colors.WHITE),
                    bgcolor=Colors.GREEN_700,
                    duration=2000,
                )
            )
            # 詳細画面へ戻る (新規の場合は、新規登録されたIDで遷移)
            page.go(f"/detail/{current_deceased_id}")

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

    # 💡 最後の住所フィールドセット（グローバル変数）
    last_address_controls = [
        last_zip_field,
        last_pref_field,
        last_city_field,
        last_street_field,
        last_building_field,
    ]

    # 💡 最後の住所の郵便番号フィールドにハンドラを割り当て（View内での定義を推奨）
    last_zip_field.on_blur = lambda e: address_zip_handler(e, last_pref_field, last_city_field)

    view_controls = [
        AppBar(
            title=Text(f"👤 被相続人情報 {'新規登録' if is_new_mode else '編集'} ({target_id})"),
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
                        "3. 住所履歴 (最後の住所)",
                        size=18,
                        weight=FontWeight.BOLD,
                        color=Colors.BLACK,
                    ),
                    Text(
                        size=12,
                        color=Colors.BLUE_GREY_600,
                    ),
                    # 最後の住所フィールド
                    # Row(last_address_controls[0:3], spacing=10),  # Zip, Pref, City
                    # Row(last_address_controls[3:5], spacing=10),  # Street, Building
                    Row(last_address_controls, spacing=10),
                    Divider(),
                    Row(
                        [
                            Text(
                                "4. 過去の住所履歴",
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
                        # alignment=MainAxisAlignment.END,
                    ),
                    # Text("4. 過去の住所履歴", size=18, weight=FontWeight.BOLD, color=Colors.BLACK),
                    # # 過去の住所を追加するボタン
                    # Row(
                    #     [
                    #         ElevatedButton(
                    #             "過去の住所を追加",
                    #             icon=Icons.ADD,
                    #             on_click=add_past_address,
                    #             bgcolor=Colors.BLUE_600,
                    #             color=Colors.WHITE,
                    #         )
                    #     ],
                    #     alignment=MainAxisAlignment.END,
                    # ),
                    # 過去の住所リストコンテナ
                    Container(
                        content=past_addresses_column,
                        # border=border.all(1, Colors.GREY_300),
                        padding=10,
                        alignment=alignment.top_left,
                    ),
                    Divider(),
                    Text("5. 本籍地", size=18, weight=FontWeight.BOLD, color=Colors.BLACK),
                    Row([dialog_hometown_field]),
                    Divider(),
                    Row(
                        [
                            ElevatedButton(
                                "キャンセル",
                                on_click=lambda e: page.go(
                                    f"/detail/{target_id}" if target_id > 0 else "/"
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
            # 背景色を白にして、テキストの視認性を上げる
            bgcolor=Colors.WHITE,
        ),
    ]

    view = View(f"/deceased_edit/{target_id}", view_controls, scroll=ScrollMode.ADAPTIVE)

    # ロード時にフィールドを最新の状態に更新
    view.on_view_show = lambda e: load_data()

    return view
