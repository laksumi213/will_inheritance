# /components/pages/detail.py

from datetime import date

import requests
from flet import (
    AlertDialog,
    AppBar,
    ButtonStyle,
    Colors,
    Column,
    Container,
    CrossAxisAlignment,
    Divider,
    Dropdown,  # ドロップダウン
    ElevatedButton,
    FontWeight,
    IconButton,
    Icons,
    MainAxisAlignment,
    Page,
    Row,
    ScrollMode,
    Text,
    TextButton,
    TextField,
    View,
    border,
    dropdown,  # ドロップダウンオプション用
)

from services import deceased_service

# 担当者リストを取得する関数をインポート
from services.db_setup import get_all_users, get_next_case_number
from services.deceased_service import (
    get_address_info,
    parse_all_flexible_date,
)


# --- 西暦から和暦への変換ユーティリティ ---
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
        # 範囲外の場合は西暦をそのまま返す
        return date_obj.isoformat()

    wareki_year_str = "元年" if wareki_year == 1 else str(wareki_year) + "年"
    return f"{gengo}{wareki_year_str}{m}月{d}日"


def on_date_blur_handler(e, wareki_text: Text):
    """TextFieldがフォーカスを失ったときに実行されるハンドラー。和暦表示を更新する。"""

    input_value = e.control.value  # e.control は操作された TextField
    wareki_text.value = ""  # 初期化

    if not input_value:
        e.control.error_text = None
        wareki_text.update()
        e.control.update()
        return

    try:
        # 柔軟な解析関数で日付オブジェクトを取得 (date.date型が返る想定)
        validated_date = parse_all_flexible_date(input_value)

        # YYYY-MM-DD 形式にフォーマットし直し、TextFieldの値を更新
        e.control.value = validated_date.isoformat()
        e.control.error_text = None  # エラーメッセージをクリア

        # ★ 和暦に変換してTEXTコントロールを更新 ★
        wareki_text.value = convert_seireki_to_wareki(validated_date)

    except ValueError:
        # 解析に失敗した場合
        e.control.error_text = "無効な日付形式です"
        wareki_text.value = ""

    wareki_text.update()  # Textコントロールを更新
    e.control.update()  # TextFieldの見た目を更新


# --- 1. モーダル編集で使用するフィールド定義 (DeceasedDetailView関数の外で定義) ---

# 氏名・基本情報
dialog_name_last_field = TextField(label="氏名 (姓)", width=150, autofocus=True)
dialog_name_first_field = TextField(label="氏名 (名)", width=150)
dialog_kana_last_field = TextField(label="ふりがな (姓)", width=150)
dialog_kana_first_field = TextField(label="ふりがな (名)", width=150)
dialog_rel_field = TextField(label="続柄", width=200)
# dialog_phone_field = TextField(label="電話番号", width=200)
# dialog_email_field = TextField(label="メールアドレス", width=300)

# 住所・本籍地
dialog_hometown_field = TextField(label="本籍地 (全体)")
dialog_zip_field = TextField(label="郵便番号", width=150)
dialog_pref_field = TextField(label="都道府県", width=150)
dialog_city_field = TextField(label="市区町村", width=200)
dialog_street_field = TextField(label="番地", width=150)
dialog_building_field = TextField(label="建物名・部屋番号")

# 連絡先入力のコンテナ (動的フォームを保持)
phone_inputs_column = Column(controls=[], spacing=5)
email_inputs_column = Column(controls=[], spacing=5)

# 連絡先タイプオプション
PHONE_OPTIONS = [
    dropdown.Option("携帯", "携帯"),
    dropdown.Option("自宅", "自宅"),
    dropdown.Option("勤務先", "勤務先"),
]

# メールタイプオプション
EMAIL_OPTIONS = [
    dropdown.Option("自宅", "自宅"),
    dropdown.Option("勤務先", "勤務先"),
]


def create_contact_input_row(
    column_container: Column, initial_value="", initial_sub_type="", is_email=False
):
    """電話またはメールの入力行と削除ボタンを作成する"""

    # 削除ボタンのアクションを定義（クロージャで現在のRowを捕捉）
    def remove_row(e):
        column_container.controls.remove(row)
        column_container.update()
        e.page.update()

    # # タイプドロップダウンの定義
    # sub_type_dropdown = Dropdown(
    #     label="種別",
    #     width=100,
    #     options=EMAIL_OPTIONS if is_email else PHONE_OPTIONS,
    #     value=initial_sub_type
    #     or (EMAIL_OPTIONS[0].key if is_email else PHONE_OPTIONS[0].key),
    # )
    # 🚨 最終手段: Dropdown を TextField に置き換える
    sub_type_field = TextField(
        label="種別 (携帯/自宅/会社など)",
        value=initial_sub_type or ("自宅" if is_email else "携帯"),
        width=100,
        # Dropdown は使用しない
    )

    # 値入力フィールドの定義
    value_field = TextField(
        label="メールアドレス" if is_email else "電話番号",
        value=initial_value,
        width=400 if is_email else 250,
        data="contact_value",  # データを収集するための識別子
    )

    row = Row(
        [
            sub_type_field,
            value_field,
            IconButton(
                Icons.DELETE,
                icon_color=Colors.RED_500,
                on_click=remove_row,
                tooltip="削除",
            ),
        ],
        alignment=MainAxisAlignment.START,
    )

    return row, value_field


def add_initial_contact_rows(column_container: Column, is_email: bool, count: int = 1):
    """初期ロード時に入力行をクリアし、指定数（デフォルト1）の空行を追加する"""
    column_container.controls.clear()
    for _ in range(count):
        new_row, _ = create_contact_input_row(column_container, is_email=is_email)
        column_container.controls.append(new_row)
    # page.update()
    # column_container.update()


def add_new_contact_row(e, column_container: Column, is_email: bool):
    """ボタンクリックで新しい入力行を追加する"""
    new_row, new_field = create_contact_input_row(column_container, is_email=is_email)
    column_container.controls.append(new_row)
    column_container.update()
    new_field.focus()
    e.page.update()


# 日付
dialog_dob_field = TextField(
    label="生年月日 (YYYY-MM-DD)",
    width=180,
)
wareki_dob_text = Text(
    value="", width=250, color=Colors.BLUE_GREY_600, weight=FontWeight.W_500
)
dialog_dob_field.on_blur = lambda e: on_date_blur_handler(e, wareki_dob_text)

dialog_dod_field = TextField(
    label="死亡日 (YYYY-MM-DD)",
    width=180,
)
wareki_dod_text = Text(
    value="", width=250, color=Colors.BLUE_GREY_600, weight=FontWeight.W_500
)
dialog_dod_field.on_blur = lambda e: on_date_blur_handler(e, wareki_dod_text)

# タイトルコントロール
dialog_title_control = Text("情報編集", weight=FontWeight.BOLD)
# 案件番号入力フィールド
dialog_case_number_field = TextField(label="案件番号", width=250)

# 💡 担当者情報フィールドの定義
USER_MAP = get_all_users()
USER_OPTIONS = [dropdown.Option(str(id), name) for id, name in USER_MAP.items()]
USER_OPTIONS.insert(
    0, dropdown.Option("", "未割当")
)  # 値がNone/空文字の場合は未割当とする

dialog_manager_field = Dropdown(
    label="担当者1 (進捗管理)",
    width=200,
    options=USER_OPTIONS,
    value="",
    autofocus=True,
)
dialog_operator_field = Dropdown(
    label="担当者2 (実務担当)",
    width=200,
    options=USER_OPTIONS,
    value="",
)


def DeceasedDetailView(page: Page, deceased_id: int):
    # --- サービス層からデータを取得 ---
    # Eager Loadでcase情報も取得済み
    deceased = deceased_service.get_deceased_by_id(deceased_id)

    # 💡 新規モードのフラグを定義
    is_new_client_case = deceased_id == -1  # 新規案件（契約者登録）モード
    is_new_deceased = deceased_id == 0  # 被相続人単独の新規登録モード

    # 進捗サマリーを取得
    progress_summary = {}
    if deceased_id > 0:  # 既存案件または単独新規完了後
        # 案件IDが必要なので、caseオブジェクトからcase_idを取得
        case_id_for_progress = (
            deceased.case.case_id if deceased and deceased.case else None
        )
        if case_id_for_progress:
            progress_summary = deceased_service.get_case_progress_summary(
                case_id_for_progress
            )

    # 案件情報を取得
    case = deceased.case if deceased and deceased.case else None

    if deceased and not is_new_client_case:
        # 既存/単独新規完了後の表示ロジック
        full_name = f"{deceased.name_last} {deceased.name_first}"
        dob_str = str(deceased.date_of_birth) if deceased.date_of_birth else ""
        dod_str = str(deceased.date_of_death) if deceased.date_of_death else "未登録"
        # is_new_deceased は deceased_id=0 で処理

    elif is_new_client_case or is_new_deceased or deceased is None:
        # 新規登録の場合のロジック (DetachedInstanceError対策で一つのブロックにまとめる)
        full_name = "【未登録】新規登録が必要です"
        dob_str = "N/A"
        dod_str = "N/A"
        # モーダルを開くためにダミーのオブジェクトを使用
        deceased = type(
            "DummyDeceased",
            (object,),
            {
                "name_last": "",
                "name_first": "",
                "name_last_kana": "",
                "name_first_kana": "",
                "date_of_birth": None,
                "date_of_death": None,
                "relationship_type": "本人",
                "hometown": "",
                "heirs": [],
                "case": None,  # case属性をダミーに追加
                "case_id": None,  # case_id属性をダミーに追加
            },
        )()
        # caseオブジェクトもNoneに設定
        case = None

    # else: (このブロックは上記で吸収されるため削除)
    #     pass

    heirs_controls = Column()

    # --- 新規追加: 案件削除確認ダイアログの定義 ---
    def create_delete_confirm_dialog(case_num: str):
        """案件削除の確認ダイアログ"""

        def confirm_delete_case(e):
            """削除サービスを呼び出し、削除後にトップ画面に戻る"""
            # サービス層の削除関数を呼び出す（db_setup.pyに実装された前提）
            # deceased_serviceに delete_case_and_all_related_data がインポートされている必要があります

            # サービスが deceased_service にあると仮定して呼び出す
            try:
                # 案件番号を渡して削除を実行
                success = deceased_service.delete_case_and_all_related_data(case_num)
                if success:
                    print(f"案件 {case_num} の削除が完了しました。")
                    page.go("/")  # 成功したらトップ画面に戻る
                else:
                    # 削除失敗の通知 (実際にはSnackbarなどを使うべき)
                    print(f"案件 {case_num} の削除に失敗しました。")
            except Exception as ex:
                print(f"削除処理中に予期せぬエラー: {ex}")

            # ダイアログを閉じる
            delete_confirm_dialog.open = False
            page.update()

        # 💡 キャンセルボタンの動作を定義
        def close_delete_dialog(e):
            delete_confirm_dialog.open = False
            page.update()

        delete_confirm_dialog = AlertDialog(
            modal=True,
            title=Text("案件削除の確認", weight=FontWeight.BOLD, color=Colors.RED_700),
            content=Text(
                f"案件番号 {case_num} に紐づく全ての情報（被相続人、相続人、財産、タスク等）を完全に削除します。よろしいですか？",
                size=14,
            ),
            actions=[
                TextButton("キャンセル", on_click=close_delete_dialog),
                ElevatedButton(
                    "完全に削除",
                    on_click=confirm_delete_case,
                    color=Colors.WHITE,
                    bgcolor=Colors.RED_600,
                ),
            ],
            actions_alignment=MainAxisAlignment.END,
        )
        return delete_confirm_dialog

    # --- 担当者専用モーダル定義 ---
    def create_assignment_dialog():
        """担当者情報のみを編集するためのモーダル"""
        return AlertDialog(
            modal=True,
            title=Text("案件担当者 編集", weight=FontWeight.BOLD),
            content=Container(
                content=Column(
                    [
                        Text(
                            f"案件番号: {case.case_number if case else 'N/A'}",
                            weight=FontWeight.W_500,
                        ),
                        Divider(),
                        Row([dialog_manager_field, dialog_operator_field]),
                    ],
                    tight=True,
                    spacing=15,
                ),
                width=450,
                height=200,
            ),
            actions=[
                TextButton("キャンセル", on_click=lambda e: close_dialog()),
                ElevatedButton(
                    "保存", on_click=lambda e: save_assignment_dialog(), data="submit"
                ),
            ],
            actions_alignment=MainAxisAlignment.END,
        )

    # --- 共通モーダル定義 ---
    def create_edit_dialog(is_deceased: bool):
        # 続柄フィールドは被相続人（本人）の場合は表示しない
        rel_row = Row([dialog_rel_field])
        if is_deceased:
            rel_row.visible = False

        date_rows = [
            Row(
                [dialog_dob_field, wareki_dob_text],
                spacing=10,
                vertical_alignment=CrossAxisAlignment.END,
            )
        ]
        if is_deceased:
            date_rows.append(
                Row(
                    [dialog_dod_field, wareki_dod_text],
                    spacing=10,
                    vertical_alignment=CrossAxisAlignment.END,
                )
            )

        # 案件番号フィールド
        case_num_row = Row([dialog_case_number_field])

        # 担当者選択フィールド
        assignment_row = Row([dialog_manager_field, dialog_operator_field])

        # 既存の被相続人編集時は非表示（担当者専用モーダルを使うため）
        # 新規案件登録時（is_new_client_case）のみ表示
        if is_deceased:
            assignment_row.visible = is_new_client_case
        elif is_new_client_case:
            assignment_row.visible = True
        else:
            # 相続人編集時は常に非表示
            assignment_row.visible = False

        # 💡 on_submit の設定: building_field が最後の入力フィールドなので、on_submit を設定するクロージャを作成
        def on_submit_handler(e):
            save_dialog(is_deceased)

        # 既存フィールドの on_submit を上書き (または設定)
        # Note: on_submit はフォーカスのある TextField で Enter が押されたときに発火
        dialog_building_field.on_submit = on_submit_handler
        dialog_hometown_field.on_submit = (
            on_submit_handler  # 案件番号の下がこれになる可能性があるため
        )
        dialog_case_number_field.on_submit = on_submit_handler

        # 💡 on_submit が発火した際に保存を実行するための ElevatedButton を作成
        save_button = ElevatedButton(
            "保存", on_click=lambda e: save_dialog(is_deceased), data="submit"
        )

        return AlertDialog(
            modal=True,
            title=dialog_title_control,
            content=Container(
                content=Column(
                    [
                        Divider(),
                        case_num_row,
                        assignment_row,  # 💡 担当者選択行を追加
                        Divider(),
                        Text("基本情報", weight=FontWeight.BOLD),
                        Row([dialog_name_last_field, dialog_name_first_field]),
                        Row([dialog_kana_last_field, dialog_kana_first_field]),
                        Divider(),
                        Text("連絡先情報", weight=FontWeight.BOLD),
                        # 電話番号入力セクション
                        Row(
                            [
                                Text("📞 電話番号", size=14, weight=FontWeight.W_500),
                                IconButton(
                                    Icons.ADD,
                                    icon_color=Colors.BLUE_500,
                                    on_click=lambda e: add_new_contact_row(
                                        e, phone_inputs_column, is_email=False
                                    ),
                                    tooltip="電話番号を追加",
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                            width=550,
                        ),
                        phone_inputs_column,
                        # メールアドレス入力セクション
                        Row(
                            [
                                Text(
                                    "📧 メールアドレス",
                                    size=14,
                                    weight=FontWeight.W_500,
                                ),
                                IconButton(
                                    Icons.ADD,
                                    icon_color=Colors.BLUE_500,
                                    on_click=lambda e: add_new_contact_row(
                                        e, email_inputs_column, is_email=True
                                    ),
                                    tooltip="メールアドレスを追加",
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                            width=550,
                        ),
                        email_inputs_column,
                        # Row([dialog_phone_field, dialog_email_field]),
                        Divider(),
                        rel_row,
                        *date_rows,
                        Divider(),
                        Text("住所情報", weight=FontWeight.BOLD),
                        Row([dialog_zip_field, dialog_pref_field, dialog_city_field]),
                        Row([dialog_street_field, dialog_building_field]),
                        Divider(),
                        dialog_hometown_field,
                        Text(
                            f"【タイプ: {'被相続人' if is_deceased else '相続人'}】",
                            color=Colors.BLUE_500,
                        ),
                    ],
                    scroll=ScrollMode.AUTO,
                    tight=True,
                    spacing=10,
                ),
                width=650,
                height=550,
            ),
            actions=[
                TextButton("キャンセル", on_click=lambda e: close_dialog()),
                save_button,
            ],
            actions_alignment=MainAxisAlignment.END,
        )

    # モーダルインスタンスを生成
    if is_new_client_case == -1:
        heir_edit_dialog = create_edit_dialog(is_deceased=True)
        deceased_edit_dialog = create_edit_dialog(is_deceased=False)
    else:
        heir_edit_dialog = create_edit_dialog(is_deceased=False)
        deceased_edit_dialog = create_edit_dialog(is_deceased=True)

    assignment_edit_dialog = create_assignment_dialog()

    # 💡 案件削除確認ダイアログを生成
    delete_confirm_dialog = create_delete_confirm_dialog(
        case.case_number if case else "N/A"
    )

    # --- モーダル制御関数 ---
    def close_dialog():
        # 💡 モーダルを閉じると同時に、新規案件登録モーダルならトップに戻る
        is_closing_new_client_case = (
            heir_edit_dialog.open and heir_edit_dialog.data == "NEW_CLIENT_CASE"
        )

        if deceased_edit_dialog.open:
            deceased_edit_dialog.open = False
        elif heir_edit_dialog.open:
            heir_edit_dialog.open = False
        elif assignment_edit_dialog.open:
            assignment_edit_dialog.open = False
        update_heirs_list()
        page.update()

        # 新規案件登録モーダルが閉じた場合にトップ画面に戻る
        if is_closing_new_client_case:
            page.go("/")
            return

    # 担当者情報保存ロジック
    def save_assignment_dialog():
        if not case:
            print("⚠️ 案件情報がないため、担当者を保存できません。")
            close_dialog()
            return

        def _get_id_from_dropdown(value):
            if value is None or value in ("", "None", "未割当"):
                return None

            try:
                return int(value)
            except ValueError:
                # 想定外の文字列が来た場合はエラーを回避し、Noneを返す（またはログを出力）
                print(f"Warning: Attempted to convert invalid value to int: {value}")
                return None

        manager_id = _get_id_from_dropdown(dialog_manager_field.value)
        operator_id = _get_id_from_dropdown(dialog_operator_field.value)

        # Caseの担当者情報のみを更新
        deceased_service.update_case_assignment(
            case_id=case.case_id,
            manager_id=manager_id,
            operator_id=operator_id,
        )

        close_dialog()

        # 画面を再読み込みして表示を更新
        # 注: DeceasedDetailViewはViewオブジェクトを返す関数なので、そのcontrolsを取得
        new_view_controls = DeceasedDetailView(page, deceased_id).controls
        current_view = page.views[-1]
        current_view.controls.clear()
        current_view.controls.extend(new_view_controls)
        page.update()

    def save_dialog(is_deceased: bool):
        # 動的フォームから連絡先データを収集する
        def collect_contacts(column: Column):
            contacts = []
            for row in column.controls:
                if isinstance(row, Row) and len(row.controls) >= 2:
                    sub_type_control = row.controls[0]
                    value_control = row.controls[1]

                    if isinstance(sub_type_control, TextField) and isinstance(
                        value_control, TextField
                    ):
                        value = value_control.value.strip()
                        sub_type = sub_type_control.value  # TextField の値を取得
                        if value:
                            contacts.append({"value": value, "sub_type": sub_type})
            return contacts

        case_number = dialog_case_number_field.value.strip()
        name = f"{dialog_name_last_field.value.strip()} {dialog_name_first_field.value.strip()}"
        kana_last = dialog_kana_last_field.value.strip()
        kana_first = dialog_kana_first_field.value.strip()
        all_phone_contacts = collect_contacts(phone_inputs_column)
        all_email_contacts = collect_contacts(email_inputs_column)
        zip_code = dialog_zip_field.value.strip()
        pref = dialog_pref_field.value.strip()
        city = dialog_city_field.value.strip()
        street = dialog_street_field.value.strip()
        building = dialog_building_field.value.strip()
        dob_value = dialog_dob_field.value.strip()
        dod_value = dialog_dod_field.value.strip()
        rel = dialog_rel_field.value.strip()
        hometown = dialog_hometown_field.value.strip()

        # 担当者IDの取得
        # Dropdownの値は文字列ID、空文字、または "None" なので、Noneまたはintに変換
        def _get_id_from_dropdown(value):
            if value and value not in ("", "None"):
                return int(value)
            return None

        manager_id = _get_id_from_dropdown(dialog_manager_field.value)
        operator_id = _get_id_from_dropdown(dialog_operator_field.value)

        if is_new_client_case:
            # 1. 契約者登録用の新規IDを発行 (deceased_id が実際のDB IDに更新される)
            # 担当者IDを渡し、戻り値はID（整数）
            new_deceased_id = deceased_service.add_new_case_for_client_registration(
                case_number=case_number,
                name=name,
                kana_last=kana_last,
                kana_first=kana_first,
                rel=rel,
                hometown=hometown,
                zip_code=zip_code,
                pref=pref,
                city=city,
                street=street,
                building=building,
                dob=dob_value,
                dod=dod_value,
                manager_id=manager_id,
                operator_id=operator_id,
                phone_contacts=all_phone_contacts,
                email_contacts=all_email_contacts,
            )

            # 新しいdeceased_idでリダイレクトし直す
            page.go(f"/detail/{new_deceased_id}")
            return  # ここで処理を終了

        # 2. 被相続人の情報保存 (is_deceased=True かつ 既存または単独新規(ID=0))
        elif is_deceased:
            deceased_service.update_deceased(
                deceased_id,
                name,
                dob=dob_value,
                dod=dod_value,
                kana_last=kana_last,
                kana_first=kana_first,
                zip_code=zip_code,
                pref=pref,
                city=city,
                street=street,
                building=building,
            )

        # 3. 通常の相続人の情報保存 (is_deceased=False)
        else:
            heir_id = heir_edit_dialog.data

            # heir_id が None の場合は新規追加として add_heir を呼び出す
            if heir_id is None:
                # 新規最新の add_heir 関数（全フィールド対応）を使用
                deceased_service.add_heir(
                    deceased_id=deceased_id,
                    name=name,
                    rel=rel,
                    kana_last=kana_last,
                    kana_first=kana_first,
                    dob=dob_value,
                    hometown=hometown,
                    zip_code=zip_code,
                    pref=pref,
                    city=city,
                    street=street,
                    building=building,
                )
            else:
                # 既存の相続人更新
                deceased_service.update_heir(
                    heir_id,
                    name,
                    rel,
                    kana_last=kana_last,
                    kana_first=kana_first,
                    zip_code=zip_code,
                    pref=pref,
                    city=city,
                    street=street,
                    building=building,
                )

            # 登録内容をprintで表示するロジック
            if deceased_id > 0:
                # サービス層から登録されたばかりのデータを取得
                registered_deceased = deceased_service.get_deceased_by_id(deceased_id)

                print("========================================")
                print("✅ 新規案件（契約者登録）データ:")

                if registered_deceased:
                    case_data = registered_deceased.case

                    # 案件情報
                    print("--- 案件情報 (CASE) ---")
                    print(f"  案件ID: {case_data.case_id if case_data else 'N/A'}")
                    print(
                        f"  案件番号: {case_data.case_number if case_data else 'N/A'}"
                    )
                    print(
                        f"  依頼者名: {case_data.client_name if case_data else 'N/A'}"
                    )
                    print(
                        f"  担当1 (ID): {case_data.manager_id if case_data else 'N/A'}"
                    )
                    print(
                        f"  担当2 (ID): {case_data.operator_id if case_data else 'N/A'}"
                    )

                    # 被相続人情報
                    print("--- 被相続人情報 (DECEASED) ---")
                    print(f"  ID: {registered_deceased.id}")
                    print(
                        f"  氏名 (姓/名): {registered_deceased.name_last} {registered_deceased.name_first}"
                    )
                    print(f"  生年月日: {registered_deceased.date_of_birth}")
                    print(f"  死亡日: {registered_deceased.date_of_death}")
                    print(f"  本籍地: {registered_deceased.hometown}")

                    # 契約者情報 (Heir - 契約者は必ず1人いるはず)
                    contracting_heir = next(
                        (
                            h
                            for h in registered_deceased.heirs
                            if h.is_contracting_party
                        ),
                        None,
                    )
                    if contracting_heir:
                        print("--- 契約者情報 (HEIR) ---")
                        print(f"  契約者ID: {contracting_heir.id}")
                        print(
                            f"  氏名: {contracting_heir.name_last} {contracting_heir.name_first}"
                        )
                        print(f"  続柄: {contracting_heir.relationship_type}")

                        # 住所情報（別途サービスを呼んで取得）
                        address_info = deceased_service.get_address_info(
                            "heir", contracting_heir.id
                        )
                        print("--- 契約者住所 ---")
                        print(f"  郵便番号: {address_info.get('zip_code', 'N/A')}")
                        print(
                            f"  住所: {address_info.get('prefecture', '')}{address_info.get('city_ward_town', '')}{address_info.get('street_address', '')}{address_info.get('building_name', '')}"
                        )

                    else:
                        print("⚠️ 契約者(Heir)レコードが見つかりません。")

                else:
                    print(
                        f"⚠️ データベースからID {new_deceased_id} のデータを取得できませんでした。"
                    )

                print("========================================")

        close_dialog()

        if page.views:
            # 現在のViewのcontrolsをクリア
            current_view = page.views[-1]

            # DeceasedDetailView を再実行し、最新のデータで新しいコントロールを取得
            # 注: DeceasedDetailViewはViewオブジェクトを返す関数なので、そのcontrolsを取得
            new_view_controls = DeceasedDetailView(page, deceased_id).controls

            # controlsをクリアして再設定
            current_view.controls.clear()
            current_view.controls.extend(new_view_controls)

            page.update()

        # --- 💡 on_open 時のフォーカス処理と Enter キー押下処理を追加 💡 ---

    def handle_modal_open(dialog, first_field):
        """モーダルを開く際にフォーカスを移動し、Enterキーのハンドラーを設定する"""

        # 💡 on_open 時の処理
        def on_dialog_open(e):
            # 氏名性のフィールドにフォーカスを強制的に当てる
            if first_field:
                page.run_thread(lambda: first_field.focus())

        # 💡 Enter/Escape キー押下時の処理
        def on_dialog_keyboard_event(e):
            # モーダルが開いている場合のみ処理
            if not dialog.open:
                return

            if e.key == "Enter":
                # Enter キーが押されたら保存ボタンをクリック
                save_button = next(
                    (
                        action
                        for action in dialog.actions
                        if getattr(action, "data", "") == "submit"
                    ),
                    None,
                )
                if save_button:
                    if callable(save_button.on_click):
                        save_button.on_click(e)
                    e.skip_internal_handling = True
                    page.update()

            # 💡 Escape キーが押されたらキャンセル処理を実行
            elif e.key == "Escape":
                close_dialog()
                e.skip_internal_handling = True
                page.update()

        # モーダルに on_open と on_keyboard_event を設定
        dialog.on_open = on_dialog_open
        dialog.on_keyboard_event = on_dialog_keyboard_event

    # 担当者モーダルを開く関数
    def open_assignment_dialog(e):
        """担当者専用モーダルを開く"""
        if not case:
            print("案件情報がないため、担当者編集を開けません。")
            return

        dialog_manager_field.visible = True
        dialog_operator_field.visible = True
        assignment_edit_dialog.data = None

        # 担当者ドロップダウンの初期値を設定
        dialog_manager_field.value = str(case.manager_id) if case.manager_id else ""
        dialog_operator_field.value = str(case.operator_id) if case.operator_id else ""

        # 案件番号表示を更新 (dialog_case_number_field を使用しないため)
        assignment_edit_dialog.content.content.controls[
            0
        ].value = f"案件番号: {case.case_number if case else 'N/A'}"

        # 💡 担当者モーダルの on_open と Enter 設定
        handle_modal_open(assignment_edit_dialog, dialog_manager_field)

        page.open(assignment_edit_dialog)
        page.update()

    def open_deceased_dialog(e):
        # 被相続人データをロード
        dialog_title_control.value = "被相続人情報 編集"
        deceased_edit_dialog.data = None

        dialog_name_last_field.value = deceased.name_last
        dialog_name_first_field.value = deceased.name_first
        dialog_kana_last_field.value = getattr(deceased, "name_last_kana", "") or ""
        dialog_kana_first_field.value = getattr(deceased, "name_first_kana", "") or ""

        # 日付フィールドの設定
        dob_date = deceased.date_of_birth
        dod_date = deceased.date_of_death

        dialog_dob_field.value = str(dob_date) if dob_date else ""
        dialog_dod_field.value = str(dod_date) if dod_date else ""

        # ★ 和暦テキストの初期設定 ★
        wareki_dob_text.value = convert_seireki_to_wareki(dob_date)
        wareki_dod_text.value = convert_seireki_to_wareki(dod_date)

        dialog_rel_field.value = getattr(deceased, "relationship_type", "本人")
        dialog_hometown_field.value = getattr(deceased, "hometown", "") or ""

        # 案件番号フィールドの表示制御
        dialog_case_number_field.visible = is_new_client_case
        dialog_case_number_field.value = (
            deceased.case.case_number if deceased.case else ""
        )

        # 💡 既存の被相続人編集時は担当者フィールドを非表示にする (save_dialogの修正と連動)
        is_assignment_visible = is_new_client_case
        dialog_manager_field.visible = is_assignment_visible
        dialog_operator_field.visible = is_assignment_visible

        # 新規契約者登録の場合、担当者の初期値を設定
        if is_new_client_case and case:
            dialog_manager_field.value = str(case.manager_id) if case.manager_id else ""
            dialog_operator_field.value = (
                str(case.operator_id) if case.operator_id else ""
            )
        # それ以外の場合は、非表示だが念のため値をクリア (必須ではない)
        else:
            dialog_manager_field.value = ""
            dialog_operator_field.value = ""

        # 住所データを取得し、フィールドを更新
        address_info = (
            get_address_info("deceased", deceased_id) if not is_new_deceased else {}
        )
        dialog_zip_field.value = address_info.get("zip_code", "")
        dialog_pref_field.value = address_info.get("prefecture", "")
        dialog_city_field.value = address_info.get("city_ward_town", "")
        dialog_street_field.value = address_info.get("street_address", "")
        dialog_building_field.value = address_info.get("building_name", "")

        # 💡 被相続人モーダルの on_open と Enter 設定
        handle_modal_open(deceased_edit_dialog, dialog_name_last_field)

        page.open(deceased_edit_dialog)
        page.update()

    def _on_mount(e):
        # 新規モードの場合、遅延処理を導入してモーダルを開く
        if is_new_client_case or is_new_deceased:

            def delayed_open():
                import time

                time.sleep(0.1)  # 100ms 待つ

                if is_new_client_case:
                    open_heir_dialog_for_new_client(None)
                elif is_new_deceased:
                    open_deceased_dialog(None)

            page.run_thread(delayed_open)

        page.update()

    # 契約者（相続人）として新規登録するためのダイアログオープン関数
    def open_heir_dialog_for_new_client(e):
        """新規案件登録ボタンから呼ばれる、契約者情報入力用のモーダルを開く"""

        heir_edit_dialog.data = "NEW_CLIENT_CASE"
        dialog_title_control.value = "新規案件登録 (契約者情報)"

        # 💡 案件番号・担当者フィールドを表示
        dialog_case_number_field.visible = True
        dialog_manager_field.visible = True
        dialog_operator_field.visible = True

        # フィールドを空に設定
        dialog_case_number_field.value = get_next_case_number()
        dialog_name_last_field.value = ""
        dialog_name_first_field.value = ""
        dialog_kana_last_field.value = ""
        dialog_kana_first_field.value = ""
        # dialog_phone_field.value = ""
        # dialog_email_field.value = ""
        dialog_rel_field.value = ""
        dialog_zip_field.value = ""
        dialog_pref_field.value = ""
        dialog_city_field.value = ""
        dialog_street_field.value = ""
        dialog_building_field.value = ""
        dialog_dob_field.value = ""
        dialog_manager_field.value = ""
        dialog_operator_field.value = ""

        add_initial_contact_rows(phone_inputs_column, is_email=False, count=1)
        add_initial_contact_rows(email_inputs_column, is_email=True, count=1)

        # ★ 和暦テキストをクリア ★
        wareki_dob_text.value = ""
        wareki_dod_text.value = ""

        # 続柄フィールドを表示 (heir_edit_dialogのcontentからアクセス)
        rel_row = heir_edit_dialog.content.content.controls[4]
        rel_row.visible = True

        # # 死亡日フィールドは非表示
        # date_rows = heir_edit_dialog.content.content.controls[5].controls
        # if len(date_rows) > 1:
        #     date_rows[1].visible = False  # 死亡日フィールドを非表示

        # 💡 新規案件登録モーダルの on_open と Enter 設定
        handle_modal_open(heir_edit_dialog, dialog_name_last_field)

        page.open(heir_edit_dialog)
        page.update()

    # ★ 新しい相続人を追加するためのモーダルオープン関数 ★
    def open_new_heir_dialog(e):
        """新しい相続人の追加ボタンから呼ばれる、新規相続人情報入力用のモーダルを開く"""

        heir_edit_dialog.data = None  # 既存のIDがないことを示す
        dialog_title_control.value = "新しい相続人情報 新規登録"

        # 💡 案件番号・担当者フィールドを非表示
        dialog_case_number_field.visible = False
        dialog_manager_field.visible = False
        dialog_operator_field.visible = False

        # フィールドを空に設定
        # 案件番号フィールドは非表示なのでクリアは不要
        dialog_name_last_field.value = ""
        dialog_name_first_field.value = ""
        dialog_kana_last_field.value = ""
        dialog_kana_first_field.value = ""
        dialog_rel_field.value = ""
        dialog_zip_field.value = ""
        dialog_pref_field.value = ""
        dialog_city_field.value = ""
        dialog_street_field.value = ""
        dialog_building_field.value = ""
        dialog_dob_field.value = ""
        # 担当者フィールドは非表示なのでクリアは不要

        # ★ 和暦テキストをクリア ★
        wareki_dob_text.value = ""
        wareki_dod_text.value = ""

        # 続柄フィールドを表示 (heir_edit_dialogのcontentからアクセス)
        # heir_edit_dialog の content の controls の 4番目が rel_row に相当する
        rel_row = heir_edit_dialog.content.content.controls[4]
        rel_row.visible = True

        # # 死亡日フィールドは非表示
        # # heir_edit_dialog の content の controls の 5番目が date_rows に相当する
        # date_rows_container = heir_edit_dialog.content.content.controls[5]
        # if date_rows_container.controls and len(date_rows_container.controls) > 1:
        #     date_rows_container.controls[1].visible = False  # 死亡日フィールドを非表示

        # 💡 新しい相続人追加モーダルの on_open と Enter 設定
        handle_modal_open(heir_edit_dialog, dialog_name_last_field)

        page.open(heir_edit_dialog)
        page.update()

    def open_heir_dialog(e, heir_id: int):
        current_deceased = deceased_service.get_deceased_by_id(deceased_id)
        heir_to_edit = next(
            (h for h in current_deceased.heirs if h.id == heir_id), None
        )

        if heir_to_edit:
            heir_edit_dialog.data = heir_id
            dialog_title_control.value = (
                f"相続人情報 編集 ({heir_to_edit.name_last} {heir_to_edit.name_first})"
            )

            # 💡 担当者フィールドの非表示制御
            dialog_manager_field.visible = False
            dialog_operator_field.visible = False
            dialog_case_number_field.visible = False

            dialog_name_last_field.value = heir_to_edit.name_last
            dialog_name_first_field.value = heir_to_edit.name_first
            dialog_kana_last_field.value = heir_to_edit.name_last_kana or ""
            dialog_kana_first_field.value = heir_to_edit.name_first_kana or ""
            dialog_rel_field.value = heir_to_edit.relationship_type
            dialog_dob_field.value = (
                str(heir_to_edit.date_of_birth) if heir_to_edit.date_of_birth else ""
            )
            dialog_hometown_field.value = heir_to_edit.hometown or ""

            # ★ 住所データを取得し、フィールドを更新 ★
            address_info = get_address_info("heir", heir_id)
            dialog_zip_field.value = address_info.get("zip_code", "")
            dialog_pref_field.value = address_info.get("prefecture", "")
            dialog_city_field.value = address_info.get("city_ward_town", "")
            dialog_street_field.value = address_info.get("street_address", "")
            dialog_building_field.value = address_info.get("building_name", "")

            # # 死亡日フィールドは非表示
            # date_rows = heir_edit_dialog.content.content.controls[5].controls
            # if len(date_rows) > 1:
            #     date_rows[1].visible = False

            # 💡 既存相続人編集モーダルの on_open と Enter 設定
            handle_modal_open(heir_edit_dialog, dialog_name_last_field)

            page.open(heir_edit_dialog)
            page.update()

    # --- 住所自動入力ロジック ---
    def search_address_by_zip(e):
        zip_code = dialog_zip_field.value.replace("-", "").strip()
        if len(zip_code) == 7 and zip_code.isdigit():
            try:
                api_url = f"https://zipcloud.ibsnet.co.jp/api/search?zipcode={zip_code}"
                response = requests.get(api_url)
                data = response.json()
                if data and data.get("results"):
                    address_data = data["results"][0]
                    dialog_pref_field.value = address_data["address1"]
                    dialog_city_field.value = address_data["address2"]
                    dialog_street_field.value = address_data["address3"]
                    page.update()
                else:
                    dialog_pref_field.value = "住所が見つかりません"
                    dialog_city_field.value = ""
                    dialog_street_field.value = ""
                    page.update()
            except Exception as ex:
                print(f"APIエラー: {ex}")
        dialog_street_field.focus()

    dialog_zip_field.on_blur = search_address_by_zip

    # --- 相続人リストの表示ロジック ---
    def update_heirs_list():
        heirs_controls.controls.clear()
        # 💡 Eager Loadされたdeceasedオブジェクトを使用
        current_deceased = deceased_service.get_deceased_by_id(deceased_id)

        if current_deceased is None or not current_deceased.heirs:
            page.update()
            return

        for heir in current_deceased.heirs:
            heir_full_name = f"{heir.name_last} {heir.name_first}"

            # 契約者マークを追加するロジック
            contract_mark = (
                "【契約者】" if getattr(heir, "is_contracting_party", False) else ""
            )

            heirs_controls.controls.append(
                Row(
                    [
                        Text(f"ID:{heir.id}", width=50),
                        Text(
                            f"名前: {heir_full_name} {contract_mark}", width=250
                        ),  # 契約者マークを追加
                        Text(f"続柄: {heir.relationship_type}", width=150),
                        IconButton(
                            Icons.EDIT,
                            icon_color=Colors.BLUE_500,
                            data=heir.id,
                            on_click=lambda e, h_id=heir.id: open_heir_dialog(e, h_id),
                        ),
                        IconButton(
                            Icons.DELETE,
                            icon_color=Colors.RED_500,
                            data=heir.id,
                            on_click=delete_heir,
                        ),
                    ],
                    alignment=MainAxisAlignment.START,
                )
            )
        page.update()

    # --- 削除ロジック ---
    def delete_heir(e):
        heir_id_to_delete = e.control.data
        deceased_service.delete_heir(heir_id_to_delete)
        update_heirs_list()

    # 初期リストの表示
    if not is_new_deceased and not is_new_client_case:
        update_heirs_list()

    # 案件削除確認ダイアログを開く関数
    def open_delete_confirm_dialog(e):
        page.open(delete_confirm_dialog)
        page.update()

    # View の定義
    view_controls = [
        AppBar(title=Text("被相続人 詳細/相続人管理"), bgcolor=Colors.BLUE_GREY_700),
        Container(
            content=Column(
                [
                    # 💡 案件番号表示セクション 💡
                    Container(
                        content=Column(
                            [
                                Row(
                                    [
                                        Text(
                                            f"案件番号: {case.case_number if case and case.case_number else 'N/A (未登録)'}",
                                            size=18,
                                            weight=FontWeight.BOLD,
                                            color=Colors.DEEP_ORANGE_600,  # 案件番号を目立たせる色に変更
                                        ),
                                        ElevatedButton(
                                            "案件を完全に削除",
                                            on_click=open_delete_confirm_dialog,
                                            icon=Icons.DELETE_FOREVER,
                                            icon_color=Colors.RED,
                                            style=ButtonStyle(bgcolor=Colors.RED_100),
                                        ),
                                    ],
                                    alignment=MainAxisAlignment.SPACE_BETWEEN,
                                    vertical_alignment=CrossAxisAlignment.CENTER,
                                ),
                                Divider(
                                    height=10, color=Colors.TRANSPARENT
                                ),  # 案件番号と担当者情報を少し離す
                                # 💡 担当者情報表示 (被相続人情報の上に移動) 💡
                                Row(
                                    [
                                        Text(
                                            "👥 担当者情報",
                                            size=18,
                                            weight=FontWeight.BOLD,
                                        ),
                                        # 💡 編集ボタンを追加 💡
                                        IconButton(
                                            Icons.EDIT,
                                            icon_color=Colors.BLUE_500,
                                            tooltip="案件担当者を編集",
                                            on_click=open_assignment_dialog,
                                        ),
                                    ],
                                    alignment=MainAxisAlignment.START,
                                ),
                                Row(
                                    [
                                        # 担当者1の表示
                                        Text(
                                            # caseがNone、またはmanager_idがNoneの場合は「未割当」を表示
                                            f"担当1 (進捗): {USER_MAP.get(case.manager_id, '未割当')}"
                                            if case is not None
                                            and case.manager_id is not None
                                            else "担当1 (進捗): 未割当",
                                            size=14,
                                            width=250,
                                        ),
                                        # 担当者2の表示
                                        Text(
                                            # caseがNone、またはoperator_idがNoneの場合は「未割当」を表示
                                            f"担当2 (実務): {USER_MAP.get(case.operator_id, '未割当')}"
                                            if case is not None
                                            and case.operator_id is not None
                                            else "担当2 (実務): 未割当",
                                            size=14,
                                            width=250,
                                        ),
                                    ],
                                    alignment=MainAxisAlignment.START,
                                ),
                            ]
                        ),
                        # 新規案件モード（-1）または単独新規被相続人モード（0）以外で、case情報がある場合に表示
                        visible=not is_new_client_case
                        and not is_new_deceased
                        and case is not None,
                    ),
                    Divider(
                        visible=not is_new_client_case
                        and not is_new_deceased
                        and case is not None
                    ),
                    # 被相続人情報
                    Row(
                        [
                            Text(
                                # "👤 被相続人情報 ✏️ ",
                                "👤 被相続人情報",
                                size=18,
                                weight=FontWeight.BOLD,
                            ),
                            Text(
                                "【新規登録モード】",
                                size=16,
                                color=Colors.RED_500,
                                visible=is_new_deceased or is_new_client_case,
                            ),
                            IconButton(
                                Icons.EDIT,
                                icon_color=Colors.BLUE_500,
                                tooltip="被相続人を編集",
                                on_click=open_deceased_dialog,
                            ),
                        ]
                    ),
                    Row(
                        [
                            Text(
                                f"名前: {full_name}",
                                weight=FontWeight.BOLD,
                                size=16,
                                width=200,
                            ),
                            Text(f"生年月日: {dob_str}", size=14, width=150),
                            Text(f"死亡日: {dod_str}", size=14, width=150),
                            # IconButton(
                            #     Icons.EDIT,
                            #     icon_color=Colors.BLUE_500,
                            #     tooltip="被相続人を編集",
                            #     on_click=open_deceased_dialog,
                            # ),
                        ],
                        alignment=MainAxisAlignment.START,
                    ),
                    Divider(),
                    # 相続人リスト
                    Column(
                        [
                            Row(
                                [
                                    Text(
                                        "👨‍👩‍👧‍👦 相続人リスト",
                                        size=16,
                                    ),
                                    # 💡 新しい相続人追加ボタン 💡
                                    ElevatedButton(
                                        "新しい相続人を追加",
                                        icon=Icons.ADD,
                                        on_click=open_new_heir_dialog,
                                    ),
                                ],
                                alignment=MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=CrossAxisAlignment.CENTER,
                            ),
                            Container(
                                content=heirs_controls,
                                border=border.all(1, Colors.BLACK12),
                                padding=10,
                                width=page.width * 0.8,
                            ),
                        ],
                        # 新規案件モード（-1）または単独新規被相続人モード（0）では非表示
                        visible=not is_new_deceased and not is_new_client_case,
                    ),
                    Divider(),
                    Row(
                        [
                            ElevatedButton(
                                "👈 一覧へ戻る", on_click=lambda e: page.go("/")
                            ),
                        ],
                        spacing=20,
                    ),
                ],
                horizontal_alignment=CrossAxisAlignment.START,
            ),
            padding=20,
        ),
    ]

    view = View(
        f"/detail/{deceased_id}",
        view_controls,
        scroll=ScrollMode.AUTO,
    )

    # ページがマウントされた時に自動でモーダルを開く設定
    view.on_view_show = _on_mount

    # 新規登録時、on_view_showが遅延またはスキップされる場合に備えて、
    #         手動で_on_mountを起動し、モーダルを開く処理を強制実行する。
    if is_new_client_case or is_new_deceased:
        _on_mount(None)

    # 初期リストの表示 (新規の場合、heirs_controlsは空のまま)
    if not is_new_deceased and not is_new_client_case:
        update_heirs_list()

    return view
