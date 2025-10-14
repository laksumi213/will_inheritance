# /services/deceased_service.py

from datetime import date, datetime

from sqlalchemy.orm import Session, joinedload

from services.db_setup import (
    Address,
    Case,
    D_AddressHistory,
    Deceased,
    Engine,
    H_AddressHistory,
    Heir,
)

# --- 内部ヘルパー関数 ---


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


# --- 被相続人関連のデータアクセスロジック ---


def get_all_deceased():
    """全被相続人のリストを返す"""
    with Session(bind=Engine) as session:
        return session.query(Deceased).all()


def get_deceased_by_id(deceased_id: int):
    """指定IDの被相続人詳細とその相続人リストを取得"""
    with Session(bind=Engine) as session:
        # Heirリレーションを結合ロード
        deceased = (
            session.query(Deceased)
            .options(
                joinedload(Deceased.heirs),  # 相続人リスト
                joinedload(Deceased.case),  # 案件情報
            )
            .get(deceased_id)
        )
        return deceased
        # deceased = (
        #     session.query(Deceased).options(joinedload(Deceased.heirs)).get(deceased_id)
        # )
        # return deceased


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
            deceased_name=name,
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
        dob_date = date.fromisoformat(dob)
    except ValueError:
        dob_date = None

    try:
        dod_date = date.fromisoformat(dod) if dod else None
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


def add_new_case_for_client_registration(
    full_name: str,
    kana: str,
    zip_code: str,
    address_raw: str,
    address_info: dict,
    dob_str: str,
    dod_str: str,
    case_number: str,
    # 💡 変更点: 担当者IDの引数を追加 (Noneを許容)
    manager_id: int | None = None,
    operator_id: int | None = None,
) -> int:
    """契約者情報に基づいて新しい案件と被相続人レコードを作成する"""
    db = Session()
    try:
        # 1. 新しい案件 (Case) を作成
        new_case = Case(
            case_number=case_number,
            status="進行中",
            # 💡 変更点: 担当者IDを設定
            manager_id=manager_id,
            operator_id=operator_id,
        )
        db.add(new_case)
        db.flush()  # New case_id is generated

        # 2. 被相続人 (Deceased) レコードを作成
        new_deceased = Deceased(
            full_name=full_name,
            kana=kana,
            zip_code=zip_code,
            address_raw=address_raw,
            address_info=address_info,
            dob_str=dob_str,
            dod_str=dod_str,
            case_id=new_case.case_id,  # 案件IDを紐づけ
        )
        db.add(new_deceased)
        db.commit()
        return new_deceased.deceased_id
    except Exception as e:
        db.rollback()
        print(f"契約者登録エラー: {e}")
        return -1
    finally:
        db.close()


# def add_new_case_for_client_registration(
#     case_number: str,
#     name: str,
#     kana_last: str = None,
#     kana_first: str = None,
#     hometown: str = None,
#     zip_code: str = None,
#     pref: str = None,
#     city: str = None,
#     street: str = None,
#     building: str = None,
#     dob: str = None,  # 被相続人情報として登録される
#     dod: str = None,  # 被相続人情報として登録される
# ):
#     """
#     新規案件を登録し、同時に契約者（依頼者: Heir）と被相続人（Deceased）を登録する。
#     """

#     parts = name.split(" ", 1)
#     name_last = parts[0].strip()
#     name_first = parts[1].strip() if len(parts) > 1 else ""

#     try:
#         dob_date = date.fromisoformat(dob) if dob else None
#     except ValueError:
#         dob_date = None

#     try:
#         dod_date = date.fromisoformat(dod) if dod else None
#     except ValueError:
#         dod_date = None

#     with Session(bind=Engine) as session:
#         # 1. 新しい案件 (Case) を作成
#         new_case = Case(
#             # case_number=f"G{datetime.now().strftime('%y%m%d%H%M%S')}",
#             case_number=case_number,
#             client_name=f"{name_last} {name_first}",  # 契約者名を設定
#             client_name_kana=f"{kana_last} {kana_first}" if kana_last else None,
#             contract_date=date.today(),  # 簡易的に今日を受託日とする
#             # manager_id, current_status_id は後で設定
#         )
#         session.add(new_case)
#         session.flush()

#         # 2. 被相続人 (Deceased) を作成（名前は空欄や仮置きでもよいが、ここでは契約者情報から類推）
#         new_deceased = Deceased(
#             case_id=new_case.case_id,
#             name_last="",
#             name_first="",
#             name_last_kana="",
#             name_first_kana="",
#             hometown="",
#             date_of_birth=None,
#             date_of_death=None,
#             # name_last=name_last,  # 契約者の姓を仮の被相続人姓とする
#             # name_first="氏名未定",
#             # name_last_kana=kana_last,
#             # name_first_kana=kana_first,
#             # date_of_birth=dob_date,
#             # date_of_death=dod_date,
#             relationship_type="本人",  # 仮の被相続人として作成
#         )
#         session.add(new_deceased)
#         session.flush()

#         # 3. 契約者（依頼者）を相続人 (Heir) として作成し、is_contracting_party=True を設定
#         new_client_heir = Heir(
#             deceased_id=new_deceased.id,
#             name_last=name_last,
#             name_first=name_first,
#             name_last_kana=kana_last,
#             name_first_kana=kana_first,
#             hometown=hometown,
#             relationship_type="契約者",  # 続柄は「契約者」と明記
#             is_contracting_party=True,  # 契約者フラグを立てる
#         )
#         session.add(new_client_heir)
#         session.flush()

#         # 4. 契約者（相続人）の住所情報を更新/作成
#         if pref and street:
#             _update_or_create_address(
#                 session,
#                 new_client_heir.id,
#                 "heir",  # 相続人として登録
#                 zip_code,
#                 pref,
#                 city,
#                 street,
#                 building,
#             )

#         session.commit()
#         return (
#             new_deceased.id
#         )  # 新規作成されたDeceasedオブジェクトを返す（IDを取得するため）


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
):
    """相続人を追加 (全フィールド対応)"""

    parts = name.split(" ", 1)
    name_last = parts[0].strip()
    name_first = parts[1].strip() if len(parts) > 1 else ""

    try:
        dob_date = date.fromisoformat(dob) if dob else None
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
        # 💡 修正: new_heir のIDを確定させるために flush が必要
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

        session.commit()


def update_heir(
    heir_id: int,
    name: str,
    rel: str,
    kana_last: str = None,
    kana_first: str = None,
    zip_code: str = None,
    pref: str = None,
    city: str = None,
    street: str = None,
    building: str = None,
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

            # 2. 住所情報の更新/作成
            if pref and street:
                _update_or_create_address(
                    session, heir_id, "heir", zip_code, pref, city, street, building
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
