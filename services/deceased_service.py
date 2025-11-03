# /services/deceased_service.py

from datetime import date, datetime

import requests
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from services.db_setup import (
    Address,
    Case,
    Contact,
    D_AddressHistory,
    Deceased,
    Engine,
    FinancialAsset,
    H_AddressHistory,
    H_ContactLink,
    Heir,
    Session,
    Task,
    delete_case_and_all_related_data,
    get_all_users,
    get_case_by_number,
    get_case_folder_path,
    get_next_case_number,
)

# --- 内部ヘルパー関数 ---


def get_case_folder_path_service(case_id: int) -> str | None:
    """
    Case ID に紐づくフォルダパス (Case.folder_path) を取得する。
    """
    return get_case_folder_path()

    # with Session(bind=Engine) as session:
    #     case = session.query(Case).filter(Case.case_id == case_id).first()
    #     # フォルダパスが存在しない場合や Case が見つからない場合は None を返す
    #     return case.folder_path if case and case.folder_path else None


def get_user_name_map() -> dict[int, str]:
    """
    担当者IDと名前のマップ {ID: Name} を取得する (db_setupから転送)
    """
    # db_setup.py の関数を呼び出すだけの中間関数
    return get_all_users()


# 案件番号取得のためのサービスラッパー
def get_next_case_number_service() -> str:
    """
    次の案件番号を取得する (DBアクセス層のラッパー)
    """
    return get_next_case_number()


# 💡 案件ハブタイトル用
def get_contracting_party_name(case_id: int) -> str:
    """Case IDに紐づく契約者（is_contracting_party=TrueのHeir）の氏名を取得する。"""
    with Session(bind=Engine) as session:
        deceased = session.query(Deceased).filter(Deceased.case_id == case_id).first()
        if not deceased:
            return "案件が見つかりません"

        contracting_heir = (
            session.query(Heir)
            .filter(Heir.deceased_id == deceased.id)
            .filter(Heir.is_contracting_party == True)
            .first()
        )

        if contracting_heir:
            return f"{contracting_heir.name_last} {contracting_heir.name_first}"
        else:
            return deceased.case.client_name if deceased.case else "契約者情報なし"


def get_financial_asset_by_case(case_id: int) -> list[dict]:
    """
    指定された案件IDに紐づく全ての金融資産を取得する。
    """
    with Session(bind=Engine) as session:
        assets = (
            session.query(FinancialAsset)
            .filter(FinancialAsset.case_id == case_id)
            .all()
        )

        # 簡易的な辞書形式に変換して返す
        return [
            {
                "id": a.asset_id,
                "bank_name": a.bank_name,
                "account_number": a.account_number,
                "balance": a.balance,
                "status": a.status,
            }
            for a in assets
        ]


def add_financial_asset(
    case_id: int,
    bank_name: str,
    account_number: str,
    balance: float,
    status: str = "調査中",
) -> int:
    """
    新しい金融資産レコードを追加する。
    """
    with Session(bind=Engine) as session:
        new_asset = FinancialAsset(
            case_id=case_id,
            bank_name=bank_name,
            account_number=account_number,
            balance=balance,
            status=status,
        )
        session.add(new_asset)
        session.commit()
        return new_asset.asset_id


def delete_case_by_case_number(case_number: str) -> bool:
    """
    案件番号を指定して、案件と全ての関連データを削除するサービスラッパー。
    """
    return delete_case_and_all_related_data(case_number)


# --- 住所検索 API ユーティリティ関数 ---


def search_address_by_zip_api(zip_code: str) -> dict | None:
    """
    郵便番号を引数に取り、住所情報をAPIから取得する。
    成功した場合、住所情報を含む辞書を返し、失敗した場合、Noneを返す。
    """
    cleaned_zip = zip_code.replace("-", "").strip()

    if len(cleaned_zip) != 7 or not cleaned_zip.isdigit():
        return None  # 無効な形式の場合は処理しない

    try:
        api_url = f"https://zipcloud.ibsnet.co.jp/api/search?zipcode={cleaned_zip}"

        response = requests.get(api_url)
        response.raise_for_status()  # HTTPエラー（4xx, 5xx）があれば例外を発生
        data = response.json()

        if data and data.get("results"):
            address_data = data["results"][0]

            # 必要な住所情報を抽出して返す
            return {
                "prefecture": address_data["address1"],
                "city_ward_town": address_data["address2"],
                "street_address": address_data["address3"],
            }
        else:
            return {}  # 住所が見つからなかったが、API通信は成功

    except requests.exceptions.RequestException as req_ex:
        print(f"APIリクエストエラー: {req_ex}")
        return None  # 通信エラー
    except Exception as ex:
        print(f"予期せぬAPIエラー: {ex}")
        return None


def convert_gengo_to_seireki(gengo_date_string):
    """
    元号の略称（s60, h20など）を含む文字列を西暦に変換し、年-月-日形式にする。
    例: 's60-1-15' -> '1985-1-15'
    """
    gengo = gengo_date_string[0].upper()  # 最初の文字を取得し大文字化 (S, H, R)

    # 基準年を定義 (和暦年 + 基準年 = 西暦年)
    gengo_base_year = {
        "T": 1911,  # 大正 (Taisho 1年 = 1912年)
        "S": 1925,  # 昭和 (Showa 1年 = 1926年)
        "H": 1988,  # 平成 (Heisei 1年 = 1989年)
        "R": 2018,  # 令和 (Reiwa 1年 = 2019年)
    }

    if gengo in gengo_base_year:
        # 1. 元号部分を抽出 (例: s60)
        try:
            # 2. 年の部分を数値として抽出 (例: 60)
            gengo_year_part = (
                gengo_date_string[1:].split("-", 1)[0].split("/", 1)[0].split(".", 1)[0]
            )
            gengo_year = int(gengo_year_part)

            # 3. 西暦を計算 (例: 60 + 1925 = 1985)
            seireki_year = gengo_year + gengo_base_year[gengo]

            # 4. 元の文字列の元号部分を西暦に置き換えて返す
            # 元号部分の文字列長 (例: 's60' は3文字)
            gengo_part_length = len(gengo) + len(gengo_year_part)

            # 西暦 + 残りの日付部分 (例: '1985' + '-1-15')
            return str(seireki_year) + gengo_date_string[gengo_part_length:]

        except ValueError:
            # 年の数値変換に失敗した場合など、元号形式ではないと判断
            pass

    # 元号の形式でなかった場合は、元の文字列をそのまま返す
    return gengo_date_string


def parse_all_flexible_date(date_string):
    """
    元号、西暦、様々な区切り文字、年なしの入力に対応する統合日付解析関数。
    """

    # 1. 元号を西暦に変換
    processed_string = convert_gengo_to_seireki(date_string)

    # 2. 年がない入力（例: 1/15）かチェックし、年を補完する（前回の回答のロジックを簡略化）
    # 区切り文字が一つだけ見つかり、年が最初の部分に含まれていない場合などを想定
    if (
        len(processed_string.split("/", 2)) == 2
        or len(processed_string.split("-", 2)) == 2
        or len(processed_string.split(".", 2)) == 2
    ):
        # 年なしフォーマットで試行
        formats_to_try_no_year = ["%m/%d", "%m-%d", "%m.%d"]
        for fmt in formats_to_try_no_year:
            try:
                dt_object_no_year = datetime.strptime(processed_string, fmt)
                # 今年の年を補完
                return date(
                    date.today().year, dt_object_no_year.month, dt_object_no_year.day
                )
            except ValueError:
                continue

    # 3. 完全な日付形式で試行 (元号変換後の西暦、または最初から西暦で入力された場合)
    # %Y-%m-%d  (例: 1985-1-15)
    # %Y/%m/%d  (例: 1985/1/15)
    # %Y.%m.%d  (例: 1985.1.15)
    formats_to_try_full = ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]

    for fmt in formats_to_try_full:
        try:
            return datetime.strptime(processed_string, fmt).date()
        except ValueError:
            continue

    # 4. すべての形式で失敗した場合
    raise ValueError(
        f"日付文字列 '{date_string}' (処理後: '{processed_string}') は無効な形式です。"
    )


def get_case_progress_summary(case_id: int):
    """
    案件の進捗サマリー（次のアクションと最終更新日）を取得する。
    """
    with Session(bind=Engine) as session:
        # 1. 「次のアクション」の取得
        # 未完了 (is_completed=False) のタスクのうち、due_dateが最も早いものを取得
        next_task = (
            session.query(Task)
            .filter(Task.case_id == case_id)
            .filter(Task.is_completed == False)
            .order_by(Task.due_date)  # 期限が早い順にソート
            .first()  # 最初の一つ（最も期限が近いタスク）を取得
        )

        # 2. 「進捗管理の更新日」の取得
        # 全タスクの中で、last_updated_atが最新のものの日付を取得
        last_update_date = (
            session.query(
                func.max(Task.last_updated_at)
            )  # last_updated_atの最大値を取得
            .filter(Task.case_id == case_id)
            .scalar()  # 結果を単一の値として取得
        )

        # 結果を辞書形式で返す
        return {
            "next_action": next_task.description
            if next_task
            else "全て完了/未割り当て",
            "next_due_date": next_task.due_date.strftime("%Y-%m-%d")
            if next_task and next_task.due_date
            else "N/A",
            "last_updated_at": last_update_date.strftime("%Y-%m-%d %H:%M")
            if last_update_date
            else "N/A",
        }


def _update_or_create_address(
    session, owner_id, owner_type, zip_code, pref, city, street, building
):
    """
    住所リンク/レコードを検索し、存在すれば更新、なければ新規作成する。
    is_last_address (deceased) または is_current_address (heir) がTrueのレコードを操作する。
    """

    # 1. 依存するテーブルとカラムの特定
    if owner_type == "deceased":
        AddressHistory = D_AddressHistory
        owner_id_col = AddressHistory.deceased_id
        is_flag_col = AddressHistory.is_last_address
    else:  # 'heir'
        AddressHistory = H_AddressHistory
        owner_id_col = AddressHistory.heir_id
        is_flag_col = AddressHistory.is_current_address

    # 2. 既存の住所リンクを検索
    address_link = (
        session.query(AddressHistory)
        .filter(owner_id_col == owner_id)
        .filter(is_flag_col == True)
        .first()
    )

    if address_link:
        # 3. 既存のAddressレコードを更新
        address_to_update = session.query(Address).get(address_link.address_id)
        if address_to_update:
            address_to_update.zip_code = zip_code
            address_to_update.prefecture = pref
            address_to_update.city_ward_town = city
            address_to_update.street_address = street
            address_to_update.building_name = building
    else:
        # 4. 既存のリンクがない場合、新規Addressレコードを作成し、リンクを作成
        new_address = Address(
            zip_code=zip_code,
            prefecture=pref,
            city_ward_town=city,
            street_address=street,
            building_name=building,
        )
        session.add(new_address)
        session.flush()  # ID確定

        # 新しいリンクを作成
        if owner_type == "deceased":
            new_link = D_AddressHistory(
                deceased_id=owner_id, address_id=new_address.id, is_last_address=True
            )
        else:
            new_link = H_AddressHistory(
                heir_id=owner_id, address_id=new_address.id, is_current_address=True
            )
        session.add(new_link)


# 連絡先登録ヘルパー関数の追加
def _create_contact_and_link_to_heir(
    db: Session, heir_id: int, contacts: list[dict], contact_type: str
):
    """
    収集された連絡先リストを Contact テーブルに登録し、H_ContactLink を介して相続人に紐づける。
    UIで種別が選択されなくなったため、sub_typeは「Primary」固定とする。

    Args:
        db (Session): SQLAlchemy セッション
        heir_id (int): 紐づける相続人のID
        contacts (list[dict]): [{'value': '090...', 'sub_type': '携帯'}, ...]
        contact_type (str): "PHONE" または "EMAIL"
    """
    for contact_data in contacts:
        value = contact_data.get("value")
        # ★ 修正: sub_type は UI から渡されなくなったため、固定値を設定 ★
        sub_type = "Primary"

        if value:
            # 1. Contact レコードの作成
            new_contact = Contact(value=value, type=contact_type, sub_type=sub_type)
            db.add(new_contact)
            db.flush()  # IDを取得

            # 2. H_ContactLink レコードの作成
            link = H_ContactLink(heir_id=heir_id, contact_id=new_contact.id)
            db.add(link)


def _sync_heir_contacts(
    db: Session, heir_id: int, phone_contacts: list[dict], email_contacts: list[dict]
):
    """
    既存の連絡先リンクとContactレコードを削除し、新しい連絡先を登録する。
    更新処理において、古い連絡先を削除し、フォームで送られた最新のリストで置き換える。
    """

    # 1. 既存の H_ContactLink を取得・削除
    existing_links = (
        db.query(H_ContactLink).filter(H_ContactLink.heir_id == heir_id).all()
    )

    # 削除対象の Contact ID を収集
    contact_ids_to_delete = [link.contact_id for link in existing_links]

    # H_ContactLink を削除
    db.query(H_ContactLink).filter(H_ContactLink.heir_id == heir_id).delete(
        synchronize_session=False
    )

    # 2. リンクが切れた Contact レコードを削除
    if contact_ids_to_delete:
        # H_ContactLink から参照されなくなった Contact を削除
        # 💡 注: Contact レコードは他のテーブル (D_ContactLink, CaseContactPoint) から参照されていないことを前提とする
        db.query(Contact).filter(Contact.id.in_(contact_ids_to_delete)).delete(
            synchronize_session=False
        )

    # 3. 新しい連絡先を登録
    if phone_contacts:
        _create_contact_and_link_to_heir(db, heir_id, phone_contacts, "PHONE")

    if email_contacts:
        _create_contact_and_link_to_heir(db, heir_id, email_contacts, "EMAIL")


# --- 被相続人関連のデータアクセスロジック ---


def get_all_deceased():
    """全被相続人のリストを返す"""
    with Session(bind=Engine) as session:
        return session.query(Deceased).all()


# IDがCase IDでもDeceasedオブジェクトを取得できるように拡張
def get_deceased_by_id(identifier_id: int):  # 💡 変数名を identifier_id に変更
    """
    指定IDの被相続人詳細とその相続人リストを取得。
    IDが Deceased.id として見つからない場合、Case.case_id として検索を試みる。
    """
    with Session(bind=Engine) as session:
        # 共通のオプション定義
        options_load = (
            joinedload(Deceased.heirs),  # 相続人リスト
            joinedload(Deceased.case).joinedload(
                Case.manager
            ),  # Case.manager/operatorも取得
            joinedload(Deceased.case).joinedload(Case.operator),
            joinedload(Deceased.case).joinedload(Case.status_ref),  # CaseStatusも取得
        )

        # 1. まず Deceased ID (Deceased.id) として検索を試みる
        deceased = (
            session.query(Deceased)
            .options(*options_load)
            .filter(Deceased.id == identifier_id)
            .first()
        )

        if deceased:
            return deceased

        # 2. 見つからなかった場合、Case ID (Deceased.case_id) として検索を試みる
        deceased = (
            session.query(Deceased)
            .options(*options_load)
            .filter(Deceased.case_id == identifier_id)  # 💡 Case IDで検索
            .first()
        )
        return deceased


def add_deceased(name: str, dob: str):
    """被相続人を新規追加 (簡易実装)"""

    parts = name.split(" ", 1)
    name_last = parts[0].strip()
    name_first = parts[1].strip() if len(parts) > 1 else ""

    try:
        dob_date = date.fromisoformat(dob)
    except ValueError:
        dob_date = None

    with Session(bind=Engine) as session:
        # 簡易的な案件データを作成
        new_case = Case(
            case_number=f"T{datetime.now().strftime('%y%m%d%H%M%S')}",
            client_name=name_last,
            # deceased_name=name,
        )
        session.add(new_case)
        session.flush()

        new_deceased = Deceased(
            case_id=new_case.case_id,
            name_last=name_last,
            name_first=name_first,
            date_of_birth=dob_date,
        )
        session.add(new_deceased)
        session.commit()
        return new_deceased.id


def delete_deceased(deceased_id: int):
    """被相続人を削除 (案件Caseも同時に削除)"""
    with Session(bind=Engine) as session:
        deceased_to_delete = session.query(Deceased).get(deceased_id)
        if deceased_to_delete:
            case_to_delete = session.query(Case).get(deceased_to_delete.case_id)
            if case_to_delete:
                session.delete(case_to_delete)
                session.commit()


def update_deceased(
    deceased_id: int,
    name: str,
    dob: str,
    dod: str = None,
    kana_last: str = None,
    kana_first: str = None,
    hometown: str = None,  # 追加: hometownを引数に追加
    zip_code: str = None,
    pref: str = None,
    city: str = None,
    street: str = None,
    building: str = None,
):
    """被相続人の基本情報と最新の住所情報を更新する。"""

    # 基本情報処理
    parts = name.split(" ", 1)
    name_last = parts[0].strip()
    name_first = parts[1].strip() if len(parts) > 1 else ""
    try:
        dob_date = parse_all_flexible_date(dob) if dob else None
    except ValueError:
        dob_date = None

    try:
        dod_date = parse_all_flexible_date(dod) if dod else None
    except ValueError:
        dod_date = None

    with Session(bind=Engine) as session:
        deceased = session.query(Deceased).get(deceased_id)
        if deceased:
            # 1. 基本情報の更新
            deceased.name_last = name_last
            deceased.name_first = name_first
            deceased.name_last_kana = kana_last
            deceased.name_first_kana = kana_first
            deceased.date_of_birth = dob_date
            deceased.date_of_death = dod_date
            deceased.hometown = hometown  # 追加: hometownを更新

            case = session.query(Case).get(deceased.case_id)
            if case:
                # Caseモデルに deceased_name はないので client_name は更新しない
                # case.deceased_name = name
                pass

            # 2. 住所情報の更新/作成
            if pref and street:
                _update_or_create_address(
                    session,
                    deceased_id,
                    "deceased",
                    zip_code,
                    pref,
                    city,
                    street,
                    building,
                )

            session.commit()


def update_case_folder_path(case_id: int, folder_path: str | None) -> bool:
    """
    案件IDに基づいて、Case.folder_path を更新する。
    """
    with Session(bind=Engine) as session:
        case = session.query(Case).filter(Case.case_id == case_id).first()
        if case:
            case.folder_path = folder_path
            session.commit()
            return True
        return False


def add_new_case_for_client_registration(
    case_number: str,
    name: str,
    kana_last: str = None,
    kana_first: str = None,
    rel: str = None,
    hometown: str = None,
    zip_code: str = None,
    pref: str = None,
    city: str = None,
    street: str = None,
    building: str = None,
    dob: str = None,  # 被相続人情報として登録される（UIから渡される）
    dod: str = None,  # 被相続人情報として登録される（UIから渡される）
    manager_id: int | None = None,
    operator_id: int | None = None,
    phone_contacts: list[dict] = None,
    email_contacts: list[dict] = None,
) -> int:
    """
    新規案件を登録し、同時に契約者（依頼者: Heir）と被相続人（Deceased）を登録する。
    登録後、新しい Deceased の ID を返す。
    """

    parts = name.split(" ", 1)
    name_last = parts[0].strip()
    name_first = parts[1].strip() if len(parts) > 1 else ""

    try:
        dob_date = parse_all_flexible_date(dob) if dob else None
    except ValueError:
        dob_date = None

    try:
        dod_date = parse_all_flexible_date(dod) if dod else None
    except ValueError:
        dod_date = None

    with Session(bind=Engine) as session:
        try:
            # 1. 新しい案件 (Case) を作成
            new_case = Case(
                case_number=case_number,
                client_name=f"{name_last} {name_first}",  # 契約者名を設定
                client_name_kana=f"{kana_last} {kana_first}"
                if kana_last and kana_first
                else None,
                contract_date=date.today(),  # 簡易的に今日を受託日とする
                # 担当者IDを設定 (Noneの場合は未割り当て)
                manager_id=manager_id,
                operator_id=operator_id,
                # current_status_id は別途初期ステータスIDを設定する必要があるが、ここでは省略
            )
            session.add(new_case)
            session.flush()  # new_case.case_id を確定させる

            # 2. 被相続人 (Deceased) を作成（仮の被相続人情報）
            # 新規契約者登録モードでは、被相続人情報は空で登録される
            new_deceased = Deceased(
                case_id=new_case.case_id,
                name_last="",
                name_first="",
                name_last_kana="",
                name_first_kana="",
                hometown="",
                date_of_birth=None,
                date_of_death=None,
                relationship_type="本人",
            )
            session.add(new_deceased)
            session.flush()  # new_deceased.id を確定させる

            # 3. 契約者（依頼者）を相続人 (Heir) として作成し、is_contracting_party=True を設定
            new_client_heir = Heir(
                deceased_id=new_deceased.id,
                name_last=name_last,
                name_first=name_first,
                name_last_kana=kana_last,
                name_first_kana=kana_first,
                hometown=hometown,
                date_of_birth=dob_date,  # 契約者の生年月日を登録
                relationship_type=rel,
                is_contracting_party=True,
            )
            session.add(new_client_heir)
            session.flush()

            # 4. 契約者（相続人）の住所情報を更新/作成
            if pref and street:
                _update_or_create_address(
                    session,
                    new_client_heir.id,
                    "heir",  # 相続人として登録
                    zip_code,
                    pref,
                    city,
                    street,
                    building,
                )

            # 連絡先情報を登録
            if phone_contacts:
                _create_contact_and_link_to_heir(
                    session, new_client_heir.id, phone_contacts, "PHONE"
                )

            if email_contacts:
                _create_contact_and_link_to_heir(
                    session, new_client_heir.id, email_contacts, "EMAIL"
                )

            session.commit()

            # 💡 DetachedInstanceError を回避するため、IDのみを返す
            return new_deceased.id

        except Exception as e:
            session.rollback()
            print(f"契約者登録エラー: {e}")
            return -1  # 登録失敗を示すID


# --- 相続人関連のデータアクセスロジック ---


def get_all_heirs():
    """全相続人のリストを返す (確認用)"""
    with Session(bind=Engine) as session:
        # 相続人(Heir)と被相続人(Deceased)を結合して取得
        heirs = (
            session.query(Heir)
            .options(joinedload(Heir.deceased).joinedload(Deceased.case))
            .all()
        )
        return heirs


def get_heir_by_id(heir_id: int):  # 追加: 単一のHeirを取得する関数
    """指定IDの相続人詳細を取得"""
    with Session(bind=Engine) as session:
        heir = session.query(Heir).get(heir_id)
        return heir


def add_heir(
    deceased_id: int,
    name: str,
    rel: str,
    kana_last: str = None,
    kana_first: str = None,
    dob: str = None,
    hometown: str = None,
    zip_code: str = None,
    pref: str = None,
    city: str = None,
    street: str = None,
    building: str = None,
    phone_contacts: list[dict] = None,
    email_contacts: list[dict] = None,
):
    """相続人を追加 (全フィールド対応)"""

    parts = name.split(" ", 1)
    name_last = parts[0].strip()
    name_first = parts[1].strip() if len(parts) > 1 else ""

    try:
        dob_date = parse_all_flexible_date(dob) if dob else None
    except ValueError:
        dob_date = None

    new_heir = Heir(
        deceased_id=deceased_id,
        name_last=name_last,
        name_first=name_first,
        relationship_type=rel,
        name_last_kana=kana_last,
        name_first_kana=kana_first,
        date_of_birth=dob_date,
        hometown=hometown,
        # is_contracting_party はデフォルトの False のまま
    )

    with Session(bind=Engine) as session:
        session.add(new_heir)
        # new_heir のIDを確定させるために flush が必要
        session.flush()

        # 住所情報が提供されていれば、_update_or_create_address を呼び出す
        if pref and street:
            _update_or_create_address(
                session,
                new_heir.id,
                "heir",  # 相続人として登録
                zip_code,
                pref,
                city,
                street,
                building,
            )

        # 💡 連絡先情報の登録
        if phone_contacts:
            _create_contact_and_link_to_heir(
                session, new_heir.id, phone_contacts, "PHONE"
            )

        if email_contacts:
            _create_contact_and_link_to_heir(
                session, new_heir.id, email_contacts, "EMAIL"
            )

        session.commit()


def update_heir(
    heir_id: int,
    name: str,
    rel: str,
    kana_last: str = None,
    kana_first: str = None,
    hometown: str = None,  # 追加: hometownを引数に追加
    zip_code: str = None,
    pref: str = None,
    city: str = None,
    street: str = None,
    building: str = None,
    phone_contacts: list[dict] = None,
    email_contacts: list[dict] = None,
):
    """相続人の基本情報と最新の住所情報を更新する。"""

    # 基本情報処理
    parts = name.split(" ", 1)
    name_last = parts[0].strip()
    name_first = parts[1].strip() if len(parts) > 1 else ""

    with Session(bind=Engine) as session:
        heir = session.query(Heir).get(heir_id)
        if heir:
            # 1. 基本情報の更新
            heir.name_last = name_last
            heir.name_first = name_first
            heir.name_last_kana = kana_last
            heir.name_first_kana = kana_first
            heir.relationship_type = rel
            heir.hometown = hometown  # 追加: hometownを更新

            # 2. 住所情報の更新/作成
            if pref and street:
                _update_or_create_address(
                    session, heir_id, "heir", zip_code, pref, city, street, building
                )

            # 💡 3. 連絡先情報の同期
            # phone_contactsとemail_contactsがNoneで渡された場合でも、空のリストとして処理を続行
            _sync_heir_contacts(
                session,
                heir_id,
                phone_contacts or [],
                email_contacts or [],
            )

            session.commit()


def delete_heir(heir_id: int):
    """相続人を削除"""
    with Session(bind=Engine) as session:
        heir_to_delete = session.query(Heir).get(heir_id)
        if heir_to_delete:
            session.delete(heir_to_delete)
            session.commit()


def get_address_info(owner_type: str, owner_id: int):
    """
    指定されたエンティティ（被相続人または相続人）の最新の住所情報を取得する。
    """
    with Session(bind=Engine) as session:
        address_link = None

        if owner_type == "deceased":
            # 被相続人の場合: is_last_address=True のリンクを取得
            address_link = (
                session.query(D_AddressHistory)
                .filter(D_AddressHistory.deceased_id == owner_id)
                .filter(D_AddressHistory.is_last_address == True)
                .first()
            )

        elif owner_type == "heir":
            # 相続人の場合: is_current_address=True のリンクを取得 (現在の住所)
            address_link = (
                session.query(H_AddressHistory)
                .filter(H_AddressHistory.heir_id == owner_id)
                .filter(H_AddressHistory.is_current_address == True)
                .first()
            )

        if address_link:
            # リンクからAddressマスタの情報を取得
            address_data = session.query(Address).get(address_link.address_id)

            if address_data:
                return {
                    "zip_code": address_data.zip_code or "",
                    "prefecture": address_data.prefecture or "",
                    "city_ward_town": address_data.city_ward_town or "",
                    "street_address": address_data.street_address or "",
                    "building_name": address_data.building_name or "",
                }

        return {}


# --- 案件の担当者情報を更新する関数 ---
def update_case_assignment(
    case_id: int, manager_id: int | None, operator_id: int | None
):
    """案件の担当者1 (manager_id) と担当者2 (operator_id) を更新する"""

    # Session() は db_setup.py で定義されたセッションメーカーを使用
    with Session(bind=Engine) as session:
        try:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case:
                # Noneが渡された場合はDBのNULLに設定される
                case.manager_id = manager_id
                case.operator_id = operator_id
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"担当者割り当て更新エラー: {e}")
            return False


def get_contact_info(owner_type: str, owner_id: int) -> list[dict]:
    """
    指定されたエンティティ（今回は相続人 'heir'）に紐づく全ての連絡先情報を取得する。
    """
    if owner_type != "heir":
        # 被相続人 (deceased) の連絡先はここでは扱わない
        return []

    with Session(bind=Engine) as session:
        # H_ContactLink を介して Contact テーブルを結合し、全ての連絡先を取得
        contact_links = (
            session.query(H_ContactLink)
            .options(joinedload(H_ContactLink.contact))  # Contactレコードを結合ロード
            .filter(H_ContactLink.heir_id == owner_id)
            .all()
        )

        contacts = []
        for link in contact_links:
            contact = link.contact
            if contact:
                contacts.append(
                    {
                        "value": contact.value or "N/A",
                        "type": contact.type or "N/A",
                        "sub_type": contact.sub_type or "N/A",
                    }
                )

        return contacts


def get_case_id_by_deceased_id(deceased_id: int) -> int | None:
    """
    Deceased ID に紐づく Case ID を取得する。
    """
    with Session(bind=Engine) as session:
        # Deceased モデルから case_id を直接取得
        deceased = (
            session.query(Deceased.case_id).filter(Deceased.id == deceased_id).first()
        )
        return deceased.case_id if deceased else None


def get_contracting_party_name(case_id: int) -> str:
    """
    Case IDに紐づく契約者（is_contracting_party=TrueのHeir）の氏名を取得する。
    """
    with Session(bind=Engine) as session:
        # 1. まず Case ID から Deceased を見つける
        deceased = session.query(Deceased).filter(Deceased.case_id == case_id).first()

        if not deceased:
            return "案件が見つかりません"

        deceased_id = deceased.id

        # 2. Deceased ID に紐づく契約者（Heir）を取得する
        contracting_heir = (
            session.query(Heir)
            .filter(Heir.deceased_id == deceased_id)
            .filter(Heir.is_contracting_party == True)
            .first()
        )

        if contracting_heir:
            return f"{contracting_heir.name_last} {contracting_heir.name_first}"
        else:
            # 契約者Heirが見つからない場合、Caseテーブルのclient_nameを参照する（フォールバック）
            return deceased.case.client_name if deceased.case else "契約者情報なし"


def is_case_number_duplicate(case_number: str) -> bool:
    """
    案件番号がすでに存在するかチェックする。
    """
    existing_case = get_case_by_number(case_number)
    return existing_case is not None  # 案件が見つかれば True (重複) を返す
