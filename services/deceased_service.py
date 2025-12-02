# services/deceased_service.py

from datetime import date, datetime

import requests
from sqlalchemy import func, Integer
from sqlalchemy.orm import Session, joinedload

from services.db_setup import (
    AccountTypeMaster,
    Address,
    BankMaster,
    BranchMaster,
    Case,
    CaseContactPoint,
    CaseStatus,
    Contact,
    D_AddressHistory,
    D_ContactLink,
    Deceased,
    Engine,
    FinancialAsset,
    H_AddressHistory,
    H_ContactLink,
    Heir,
    Session,
    Task,
    User,
)

# --- 内部ヘルパー関数 ---


def get_account_type_masters(db: Session) -> list[AccountTypeMaster]:
    """全口座種類マスタを取得"""
    return db.query(AccountTypeMaster).all()


def add_account_type_master(db: Session, type_name: str) -> AccountTypeMaster | None:
    """口座種類マスタを新規登録する（重複チェックあり）"""
    type_name = type_name.strip()
    if not type_name:
        return None

    try:
        # 重複チェック
        existing = db.query(AccountTypeMaster).filter(AccountTypeMaster.type_name == type_name).first()
        if existing:
            return existing

        new_type = AccountTypeMaster(type_name=type_name)
        db.add(new_type)
        db.commit()
        db.refresh(new_type)
        return new_type
    except Exception as e:
        db.rollback()
        print(f"口座種類マスタの登録エラー: {e}")
        return None


def get_bank_masters(db: Session) -> list[BankMaster]:
    """全銀行マスタを取得"""
    return db.query(BankMaster).order_by(BankMaster.bank_name).all()


def get_branch_masters_by_bank_id(db: Session, bank_id: int) -> list[BranchMaster]:
    """指定された銀行IDに紐づく全支店マスタを取得"""
    return (
        db.query(BranchMaster)
        .filter(BranchMaster.bank_id == bank_id)
        .order_by(BranchMaster.branch_name)
        .all()
    )


def get_bank_master_by_id(db: Session, bank_id: int) -> BankMaster | None:
    """銀行マスタをIDで取得"""
    return db.query(BankMaster).filter(BankMaster.id == bank_id).first()


def add_or_update_bank_master(
    db: Session, bank_id: int | None, name: str, code: str
) -> BankMaster | None:
    """銀行マスタを新規登録または更新する"""
    name = name.strip()
    code = code.strip()

    if not name or not code:
        return None  # 必須項目が欠落

    try:
        if bank_id:
            # 更新
            bank = db.query(BankMaster).filter(BankMaster.id == bank_id).first()
            if not bank:
                return None
            bank.bank_name = name
            bank.bank_code = code
        else:
            # 新規登録
            bank = BankMaster(bank_name=name, bank_code=code)
            db.add(bank)

        db.commit()
        db.refresh(bank)
        return bank
    except Exception as e:
        db.rollback()
        print(f"銀行マスタの登録/更新中にエラーが発生しました: {e}")
        return None


def add_financial_asset(
    case_id: int,
    bank_id: int,
    branch_id: int | None,
    account_type_id: int,
    account_number: str,
    balance: float,
    status: str,
) -> bool:
    """金融資産レコードを新規登録する"""
    with Session(bind=Engine) as db:
        try:
            new_asset = FinancialAsset(
                case_id=case_id,
                bank_id=bank_id,
                branch_id=branch_id,
                account_type_id=account_type_id,
                account_number=account_number,
                balance=balance,
                status=status,
            )
            db.add(new_asset)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"金融資産の登録中にエラーが発生しました: {e}")
            return False


def get_bank_cert_document_data(case_id: int, bank_code: str) -> dict | None:
    """
    指定された銀行コードの残高証明書申請に必要な、案件、被相続人、契約者の詳細情報を統合して取得する。
    """

    with Session(bind=Engine) as session:
        # 1. Case, Deceased, 契約者Heir の統合取得
        deceased = session.query(Deceased).filter(Deceased.case_id == case_id).first()
        if not deceased:
            return None

        # 契約者 Heir (is_contracting_party=True) を取得
        contracting_heir = (
            session.query(Heir)
            .filter(Heir.deceased_id == deceased.id)
            .filter(Heir.is_contracting_party == True)
            .first()
        )

        # 2. 被相続人住所情報の取得 (最新の住所)
        deceased_address_info = get_address_info("deceased", deceased.id)

        # 3. 契約者情報、住所、連絡先の取得
        heir_info = {}
        if contracting_heir:
            # 契約者住所の取得 (最新の住所)
            heir_address_info = get_address_info("heir", contracting_heir.id)
            # 契約者連絡先の取得
            heir_contacts = get_contact_info("heir", contracting_heir.id)

            # 電話番号の抽出 (Primary/携帯などを優先)
            heir_phone = next((c["value"] for c in heir_contacts if c["type"] == "PHONE"), None)

            heir_info = {
                "last_name": contracting_heir.name_last,
                "first_name": contracting_heir.name_first,
                "last_kana": contracting_heir.name_last_kana,
                "first_kana": contracting_heir.name_first_kana,
                "phone": heir_phone,
                "address": heir_address_info,
            }

        # 4. 銀行情報（指定された bank_code）の取得
        target_bank_assets = get_financial_assets_by_bank_code(case_id, bank_code)

        # 5. 結果の構築
        result = {
            "case_number": deceased.case.case_number if deceased.case else "N/A",
            # 被相続人情報
            "deceased": {
                "last_name": deceased.name_last,
                "first_name": deceased.name_first,
                "last_kana": deceased.name_last_kana,
                "first_kana": deceased.name_first_kana,
                "date_of_death": deceased.date_of_death,
                "address": deceased_address_info,
            },
            # 契約者情報
            "contracting_party": heir_info,
            # 銀行情報
            "bank_assets": target_bank_assets,
        }

        return result


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
    """指定された案件IDに紐づく全ての金融資産を取得する"""
    with Session(bind=Engine) as session:
        assets = session.query(FinancialAsset).filter(FinancialAsset.case_id == case_id).all()

        return [
            {
                "id": a.id,
                "bank_id": a.bank_id,
                "branch_id": a.branch_id,
                "account_type_id": a.account_type_id,
                "bank_name": a.bank_ref.bank_name if a.bank_ref else "N/A",
                "bank_code": a.bank_ref.bank_code if a.bank_ref else "N/A",
                "branch_name": a.branch_ref.branch_name if a.branch_ref else "N/A",
                "branch_code": a.branch_ref.branch_code if a.branch_ref else "N/A",
                "account_type": a.account_type_ref.type_name if a.account_type_ref else "N/A",
                "account_number": a.account_number,
                "balance": a.balance,
                "status": a.status,
            }
            for a in assets
        ]


def get_financial_assets_by_bank_code(case_id: int, bank_code: str) -> list[dict]:
    """指定された案件IDと銀行コードに紐づく全ての金融資産を取得する"""
    with Session(bind=Engine) as session:
        assets = (
            session.query(FinancialAsset)
            .join(BankMaster, FinancialAsset.bank_id == BankMaster.id)
            .filter(FinancialAsset.case_id == case_id)
            .filter(BankMaster.bank_code == bank_code)
            .all()
        )

        return [
            {
                "id": a.id,
                "bank_name": a.bank_ref.bank_name if a.bank_ref else "N/A",
                "bank_code": a.bank_ref.bank_code if a.bank_ref else "N/A",
                "branch_name": a.branch_ref.branch_name if a.branch_ref else "N/A",
                "branch_code": a.branch_ref.branch_code if a.branch_ref else "N/A",
                "account_type": a.account_type_ref.type_name if a.account_type_ref else "N/A",
                "account_number": a.account_number,
                "balance": a.balance,
                "status": a.status,
            }
            for a in assets
        ]


def update_financial_asset(
    asset_id: int,
    bank_id: int,
    branch_id: int | None,
    account_type_id: int,
    account_number: str,
    balance: float | None,
    status: str = "調査中",
) -> bool:
    """既存の金融資産レコードを更新する"""
    with Session(bind=Engine) as session:
        asset_to_update = (
            session.query(FinancialAsset).filter(FinancialAsset.id == asset_id).first()
        )

        if asset_to_update:
            asset_to_update.bank_id = bank_id
            asset_to_update.branch_id = branch_id
            asset_to_update.account_type_id = account_type_id
            asset_to_update.account_number = account_number
            if balance is not None:
                asset_to_update.balance = balance
            asset_to_update.status = status

            try:
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                print(f"金融資産の更新中にエラーが発生しました: {e}")
                return False

        return False


def delete_financial_asset(asset_id: int) -> bool:
    """指定された asset_id の金融資産レコードを削除する"""
    with Session(bind=Engine) as session:
        asset_to_delete = (
            session.query(FinancialAsset).filter(FinancialAsset.id == asset_id).first()
        )
        if asset_to_delete:
            session.delete(asset_to_delete)
            session.commit()
            return True
        return False


# --- 💡 以下の関数群を db_setup から移動して実装 ---

def get_all_users():
    """全てのユーザーIDと名前を取得する"""
    with Session(bind=Engine) as db:
        users = db.query(User.id, User.name).order_by(User.id).all()
        return {id: name for id, name in users}


def get_next_case_number():
    """
    既存の案件番号 'GXXXX' のうち最大の番号を取得し、次の番号 (GXXXX+1) を生成する。
    """
    with Session(bind=Engine) as db:
        max_num_str = (
            db.query(func.max(func.cast(func.substr(Case.case_number, 2), Integer)))
            .filter(Case.case_number.like("G%"))
            .scalar()
        )
        if max_num_str is None:
            next_number = 1
        else:
            next_number = int(max_num_str) + 1
        return f"G{next_number:04d}"


def get_next_case_number_service() -> str:
    """次の案件番号を取得する (ラッパー)"""
    return get_next_case_number()


def get_case_folder_path(case_id: int) -> str | None:
    """Case ID に紐づくフォルダパスを取得する"""
    with Session(bind=Engine) as session:
        case = session.query(Case).filter(Case.case_id == case_id).first()
        return case.folder_path if case and case.folder_path else None


def get_case_folder_path_service(case_id: int) -> str | None:
    """Case ID に紐づくフォルダパスを取得する (ラッパー)"""
    return get_case_folder_path(case_id)


def get_case_by_number(case_number: str):
    """案件番号を指定して、Caseレコードを一つ取得する"""
    with Session(bind=Engine) as db:
        return db.query(Case).filter(Case.case_number == case_number).first()


def get_all_case_statuses():
    """全ての案件ステータスを取得する"""
    with Session(bind=Engine) as db:
        return db.query(CaseStatus).order_by(CaseStatus.order_num).all()


def get_case_list(search_term="", status_id=None, user_id=None):
    """
    案件一覧を取得する
    ※ home.pyでのKeyErrorを防ぐため、Taskテーブルを結合し、last_updated_at と description を取得できるようにする。
    """
    with Session(bind=Engine) as db:
        query = (
            db.query(
                Case,
                Deceased.name_last,
                Deceased.name_first,
                CaseStatus.name.label("status_name"),
                # 💡 Task情報を追加取得
                Task.description,
                Task.last_updated_at,
            )
            .join(Case.deceased_ref, isouter=True)
            .join(Case.status_ref, isouter=True)
            # 💡 Taskを結合 (案件ごとの最新タスクを取得するために、後でPython側で重複排除する想定)
            .join(Task, Case.case_id == Task.case_id, isouter=True)
            # タスクの更新日順 -> 案件の契約日順でソート
            .order_by(Task.last_updated_at.desc(), Case.contract_date.desc())
        )

        if search_term:
            query = query.filter(
                (Case.case_number.ilike(f"%{search_term}%"))
                | (Case.client_name.ilike(f"%{search_term}%"))
                | (Case.client_name_kana.ilike(f"%{search_term}%"))
            )

        if status_id:
            query = query.filter(Case.current_status_id == status_id)

        if user_id:
            query = query.filter((Case.manager_id == user_id) | (Case.operator_id == user_id))

        # 100件ほど取得して、Python側でCase IDの重複を排除する（最新タスク優先）
        cases_data = query.limit(100).all()

        case_list = []
        processed_ids = set()

        for case, d_last, d_first, status_name, description, last_updated_at in cases_data:
            # 重複排除
            if case.case_id in processed_ids:
                continue
            processed_ids.add(case.case_id)

            deceased_name = f"{d_last} {d_first}" if d_last else "N/A"
            role_label = ""
            if user_id:
                if case.manager_id == user_id and case.operator_id == user_id:
                    role_label = "担当1 & 2"
                elif case.manager_id == user_id:
                    role_label = "担当1"
                elif case.operator_id == user_id:
                    role_label = "担当2"

            case_list.append(
                {
                    "case_id": case.case_id,
                    "case_number": case.case_number,
                    "client_name": case.client_name,
                    "deceased_name": deceased_name,
                    "contract_date": case.contract_date.strftime("%Y/%m/%d") if case.contract_date else "N/A",
                    "status": status_name,
                    "role_label": role_label,
                    "manager_id": case.manager_id,
                    "operator_id": case.operator_id,
                    # 💡 home.pyで必要なキーを追加
                    "description": description if description else "",
                    "last_updated_at": last_updated_at.strftime("%Y/%m/%d") if last_updated_at else "N/A",
                }
            )
        return case_list


def get_my_cases(user_id: int, limit: int = 10):
    """特定のユーザーが担当する案件を取得する"""
    with Session(bind=Engine) as db:
        query = (
            db.query(Case)
            .options(joinedload(Case.deceased_ref), joinedload(Case.status_ref))
            .filter((Case.manager_id == user_id) | (Case.operator_id == user_id))
            .order_by(Case.current_status_id, Case.contract_date.desc())
        )
        cases = query.limit(limit).all()
        case_list = []
        for case in cases:
            deceased_name = (
                case.deceased_ref.name_last + " " + case.deceased_ref.name_first
                if case.deceased_ref else "N/A"
            )
            case_list.append(
                {
                    "case_id": case.case_id,
                    "case_number": case.case_number,
                    "client_name": case.client_name,
                    "deceased_name": deceased_name,
                    "status": case.status_ref.name if case.status_ref else "N/A",
                }
            )
        return case_list


def get_incomplete_tasks(user_id=None):
    """未完了のタスクを取得する"""
    with Session(bind=Engine) as db:
        query = (
            db.query(Task, Case.case_number, User.name, Case.client_name)
            .join(Case, Task.case_id == Case.case_id)
            .join(User, Task.assigned_user_id == User.id)
            .filter(Task.is_completed == False)
        )
        
        if user_id:
            query = query.filter(Task.assigned_user_id == user_id)
            
        tasks = query.order_by(Task.due_date).limit(10).all()

        tasks_data = []
        for task, case_number, assigned_user_name, client_name in tasks:
            tasks_data.append(
                {
                    "task_id": task.task_id,
                    "case_id": task.case_id,
                    "case_number": case_number,
                    "description": task.description,
                    "due_date": task.due_date.strftime("%Y/%m/%d") if task.due_date else "N/A",
                    "assigned_user": assigned_user_name,
                    "client_name": client_name,
                }
            )
        return tasks_data


def get_user_capacity_data():
    """全担当者の業務キャパシティを取得する"""
    with Session(bind=Engine) as db:
        users = db.query(User).all()
        capacity_data = []
        for user in users:
            user_id = user.id
            task_count = (
                db.query(func.count(Task.task_id))
                .filter(Task.assigned_user_id == user_id, Task.is_completed == False)
                .scalar()
            )
            case_count = (
                db.query(func.count(Case.case_id))
                .filter((Case.manager_id == user_id) | (Case.operator_id == user_id))
                .scalar()
            )
            capacity_data.append(
                {
                    "user_id": user_id,
                    "name": user.name,
                    "role": user.role,
                    "total_incomplete_tasks": task_count,
                    "total_cases_handled": case_count,
                }
            )
        capacity_data.sort(key=lambda x: x["total_incomplete_tasks"], reverse=True)
        return capacity_data


def delete_case_and_all_related_data(case_number: str) -> bool:
    """指定された案件番号のCaseレコードと関連データを削除する"""
    with Session(bind=Engine) as db:
        try:
            case_to_delete = db.query(Case).filter(Case.case_number == case_number).first()
            if not case_to_delete:
                print(f"案件番号 {case_number} は見つかりませんでした。")
                return False

            case_id = case_to_delete.case_id
            print(f"案件ID {case_id} ({case_number}) の削除を開始します...")

            # 関連IDの取得
            deceased = db.query(Deceased).filter(Deceased.case_id == case_id).first()
            deceased_id = deceased.id if deceased else None

            # Case削除 (カスケード削除)
            db.delete(case_to_delete)
            db.commit()
            print(f"Case ID {case_id} の削除が完了しました。")

            # 孤立データのクリーンアップ
            subquery_deceased = db.query(D_AddressHistory.address_id)
            subquery_heir = db.query(H_AddressHistory.address_id)
            db.query(Address).filter(~Address.id.in_(subquery_deceased), ~Address.id.in_(subquery_heir)).delete(synchronize_session="fetch")
            db.commit()

            subquery_d = db.query(D_ContactLink.contact_id)
            subquery_h = db.query(H_ContactLink.contact_id)
            subquery_c = db.query(CaseContactPoint.contact_id)
            db.query(Contact).filter(~Contact.id.in_(subquery_d), ~Contact.id.in_(subquery_h), ~Contact.id.in_(subquery_c)).delete(synchronize_session="fetch")
            db.commit()

            return True
        except Exception as e:
            db.rollback()
            print(f"データ削除中にエラーが発生しました: {e}")
            return False


def delete_case_by_case_number(case_number: str) -> bool:
    """案件削除のラッパー関数"""
    return delete_case_and_all_related_data(case_number)


# --- 住所検索 API ユーティリティ関数 ---


def search_address_by_zip_api(zip_code: str) -> dict | None:
    """郵便番号から住所を検索する"""
    cleaned_zip = zip_code.replace("-", "").strip()
    if len(cleaned_zip) != 7 or not cleaned_zip.isdigit():
        return None

    try:
        api_url = f"https://zipcloud.ibsnet.co.jp/api/search?zipcode={cleaned_zip}"
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()

        if data and data.get("results"):
            address_data = data["results"][0]
            return {
                "prefecture": address_data["address1"],
                "city_ward_town": address_data["address2"],
                "street_address": address_data["address3"],
            }
        else:
            return {}
    except Exception as ex:
        print(f"APIエラー: {ex}")
        return None


def convert_gengo_to_seireki(gengo_date_string):
    """元号を西暦に変換"""
    gengo = gengo_date_string[0].upper()
    gengo_base_year = {"T": 1911, "S": 1925, "H": 1988, "R": 2018}

    if gengo in gengo_base_year:
        try:
            gengo_year_part = gengo_date_string[1:].split("-", 1)[0].split("/", 1)[0].split(".", 1)[0]
            gengo_year = int(gengo_year_part)
            seireki_year = gengo_year + gengo_base_year[gengo]
            gengo_part_length = len(gengo) + len(gengo_year_part)
            return str(seireki_year) + gengo_date_string[gengo_part_length:]
        except ValueError:
            pass
    return gengo_date_string


def parse_all_flexible_date(date_string):
    """日付文字列を解析してdateオブジェクトを返す"""
    processed_string = convert_gengo_to_seireki(date_string)

    if len(processed_string.split("/", 2)) == 2 or len(processed_string.split("-", 2)) == 2 or len(processed_string.split(".", 2)) == 2:
        formats_to_try_no_year = ["%m/%d", "%m-%d", "%m.%d"]
        for fmt in formats_to_try_no_year:
            try:
                dt_object_no_year = datetime.strptime(processed_string, fmt)
                return date(date.today().year, dt_object_no_year.month, dt_object_no_year.day)
            except ValueError:
                continue

    formats_to_try_full = ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]
    for fmt in formats_to_try_full:
        try:
            return datetime.strptime(processed_string, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"日付文字列 '{date_string}' は無効な形式です。")


def get_case_progress_summary(case_id: int):
    """案件の進捗サマリーを取得する"""
    with Session(bind=Engine) as session:
        next_task = (
            session.query(Task)
            .filter(Task.case_id == case_id)
            .filter(Task.is_completed == False)
            .order_by(Task.due_date)
            .first()
        )
        last_update_date = (
            session.query(func.max(Task.last_updated_at))
            .filter(Task.case_id == case_id)
            .scalar()
        )
        return {
            "next_action": next_task.description if next_task else "全て完了/未割り当て",
            "next_due_date": next_task.due_date.strftime("%Y-%m-%d") if next_task and next_task.due_date else "N/A",
            "last_updated_at": last_update_date.strftime("%Y-%m-%d %H:%M") if last_update_date else "N/A",
        }


def _update_address(db: Session, address_data: dict, existing_address_id: int | None = None) -> int | None:
    """住所データの更新・作成ヘルパー"""
    zip_code = address_data.get("zip_code")
    prefecture = address_data.get("prefecture")
    city_ward_town = address_data.get("city_ward_town")
    street_address = address_data.get("street_address")
    building_name = address_data.get("building_name")

    if not prefecture or not street_address:
        return None

    address_args = {
        "zip_code": zip_code,
        "prefecture": prefecture,
        "city_ward_town": city_ward_town,
        "street_address": street_address,
        "building_name": building_name,
    }

    if existing_address_id:
        db.query(Address).filter(Address.id == existing_address_id).update(address_args)
        return existing_address_id
    else:
        new_address = Address(**address_args)
        db.add(new_address)
        db.flush()
        return new_address.id


def _update_or_create_address(session, owner_id, owner_type, zip_code, pref, city, street, building, is_last: bool = True):
    """住所履歴の更新ヘルパー"""
    if owner_type == "deceased":
        AddressHistory = D_AddressHistory
        owner_id_col = AddressHistory.deceased_id
        is_flag_col = AddressHistory.is_last_address
        is_flag_value = is_last
    else:
        AddressHistory = H_AddressHistory
        owner_id_col = AddressHistory.heir_id
        is_flag_col = AddressHistory.is_current_address
        is_flag_value = True

    if owner_type == "deceased" and is_flag_value is True:
        session.query(AddressHistory).filter(owner_id_col == owner_id, is_flag_col == True).update({is_flag_col: False})

    new_address = Address(
        zip_code=zip_code,
        prefecture=pref,
        city_ward_town=city,
        street_address=street,
        building_name=building,
    )
    session.add(new_address)
    session.flush()

    if owner_type == "deceased":
        new_link = D_AddressHistory(deceased_id=owner_id, address_id=new_address.id, is_last_address=is_flag_value)
    else:
        new_link = H_AddressHistory(heir_id=owner_id, address_id=new_address.id, is_current_address=is_flag_value)
    session.add(new_link)


def _create_contact_and_link_to_heir(db: Session, heir_id: int, contacts: list[dict], contact_type: str):
    """相続人の連絡先登録ヘルパー"""
    for contact_data in contacts:
        value = contact_data.get("value")
        sub_type = "Primary"
        if value:
            new_contact = Contact(value=value, type=contact_type, sub_type=sub_type)
            db.add(new_contact)
            db.flush()
            link = H_ContactLink(heir_id=heir_id, contact_id=new_contact.id)
            db.add(link)


def _sync_heir_contacts(db: Session, heir_id: int, phone_contacts: list[dict], email_contacts: list[dict]):
    """相続人の連絡先同期ヘルパー"""
    existing_links = db.query(H_ContactLink).filter(H_ContactLink.heir_id == heir_id).all()
    contact_ids_to_delete = [link.contact_id for link in existing_links]
    db.query(H_ContactLink).filter(H_ContactLink.heir_id == heir_id).delete(synchronize_session=False)
    
    if contact_ids_to_delete:
        db.query(Contact).filter(Contact.id.in_(contact_ids_to_delete)).delete(synchronize_session=False)

    if phone_contacts:
        _create_contact_and_link_to_heir(db, heir_id, phone_contacts, "PHONE")
    if email_contacts:
        _create_contact_and_link_to_heir(db, heir_id, email_contacts, "EMAIL")


def _create_contact_and_link_to_deceased(db: Session, deceased_id: int, contacts: list[dict], contact_type: str):
    """被相続人の連絡先登録ヘルパー"""
    for contact_data in contacts:
        value = contact_data.get("value")
        sub_type = "Primary"
        if value:
            new_contact = Contact(value=value, type=contact_type, sub_type=sub_type)
            db.add(new_contact)
            db.flush()
            link = D_ContactLink(deceased_id=deceased_id, contact_id=new_contact.id)
            db.add(link)


def _sync_deceased_contacts(db: Session, deceased_id: int, phone_contacts: list[dict], email_contacts: list[dict]):
    """被相続人の連絡先同期ヘルパー"""
    existing_links = db.query(D_ContactLink).filter(D_ContactLink.deceased_id == deceased_id).all()
    contact_ids_to_delete = [link.contact_id for link in existing_links]
    db.query(D_ContactLink).filter(D_ContactLink.deceased_id == deceased_id).delete(synchronize_session=False)

    if contact_ids_to_delete:
        db.query(Contact).filter(Contact.id.in_(contact_ids_to_delete)).delete(synchronize_session=False)

    if phone_contacts:
        _create_contact_and_link_to_deceased(db, deceased_id, phone_contacts, "PHONE")
    if email_contacts:
        _create_contact_and_link_to_deceased(db, deceased_id, email_contacts, "EMAIL")


def get_all_deceased():
    """全被相続人のリストを返す"""
    with Session(bind=Engine) as session:
        return session.query(Deceased).all()


def get_deceased_by_id(identifier_id: int):
    """被相続人詳細を取得する"""
    with Session(bind=Engine) as session:
        options_load = (
            joinedload(Deceased.heirs),
            joinedload(Deceased.case).joinedload(Case.manager),
            joinedload(Deceased.case).joinedload(Case.operator),
            joinedload(Deceased.case).joinedload(Case.status_ref),
            joinedload(Deceased.last_address),
        )
        deceased = session.query(Deceased).options(*options_load).filter(Deceased.id == identifier_id).first()
        if deceased:
            return deceased
        
        return session.query(Deceased).options(*options_load).filter(Deceased.case_id == identifier_id).first()


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
        new_case = Case(
            case_number=f"T{datetime.now().strftime('%y%m%d%H%M%S')}",
            client_name=name_last,
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
    """被相続人を削除"""
    with Session(bind=Engine) as session:
        deceased_to_delete = session.query(Deceased).get(deceased_id)
        if deceased_to_delete:
            case_to_delete = session.query(Case).get(deceased_to_delete.case_id)
            if case_to_delete:
                session.delete(case_to_delete)
                session.commit()


def update_deceased(
    deceased_id: int,
    name_last: str = None,
    name_first: str = None,
    dob: str = None,
    dod: str = None,
    kana_last: str = None,
    kana_first: str = None,
    hometown: str = None,
    last_zip_code: str = None,
    last_pref: str = None,
    last_city: str = None,
    last_street: str = None,
    last_building: str = None,
    past_addresses: list[dict] = None,
    phone_contacts: list[dict] = None,
    email_contacts: list[dict] = None,
):
    """被相続人データを更新する"""
    try:
        dob_date = parse_all_flexible_date(dob) if dob else None
        dod_date = parse_all_flexible_date(dod) if dod else None
    except ValueError:
        dob_date, dod_date = None, None

    with Session(bind=Engine) as db:
        try:
            deceased = db.query(Deceased).filter(Deceased.id == deceased_id).first()
            if not deceased:
                raise ValueError(f"Deceased ID {deceased_id} not found.")

            deceased.name_last = name_last
            deceased.name_first = name_first
            deceased.name_last_kana = kana_last
            deceased.name_first_kana = kana_first
            deceased.date_of_birth = dob_date
            deceased.date_of_death = dod_date
            deceased.hometown = hometown

            # 最後の住所
            last_address_data = {
                "zip_code": last_zip_code, "prefecture": last_pref,
                "city_ward_town": last_city, "street_address": last_street, "building_name": last_building,
            }
            new_last_address_id = _update_address(db, last_address_data, deceased.last_address_id)
            deceased.last_address_id = new_last_address_id

            # 過去の住所履歴
            if not past_addresses: past_addresses = []
            existing_history = db.query(D_AddressHistory).filter(D_AddressHistory.deceased_id == deceased_id).all()
            address_ids_to_delete = [h.address_id for h in existing_history if h.address_id != new_last_address_id]
            
            if address_ids_to_delete:
                db.query(D_AddressHistory).filter(D_AddressHistory.address_id.in_(address_ids_to_delete), D_AddressHistory.deceased_id == deceased_id).delete(synchronize_session=False)
                db.query(Address).filter(Address.id.in_(address_ids_to_delete)).delete(synchronize_session=False)

            for addr_data in past_addresses:
                address_id = _update_address(db, addr_data, addr_data.get("address_id"))
                if address_id:
                    d_history = db.query(D_AddressHistory).filter(D_AddressHistory.deceased_id == deceased_id, D_AddressHistory.address_id == address_id).first()
                    if not d_history:
                        db.add(D_AddressHistory(deceased_id=deceased_id, address_id=address_id, is_last_address=False))

            db.query(D_AddressHistory).filter(D_AddressHistory.deceased_id == deceased_id, D_AddressHistory.address_id == new_last_address_id).delete(synchronize_session=False)

            # 連絡先同期
            _sync_deceased_contacts(db, deceased_id, phone_contacts or [], email_contacts or [])
            db.commit()
        except Exception as e:
            db.rollback()
            raise e


def update_case_folder_path(case_id: int, folder_path: str | None) -> bool:
    """案件IDに基づいて、Case.folder_path を更新する"""
    with Session(bind=Engine) as session:
        case = session.query(Case).filter(Case.case_id == case_id).first()
        if case:
            case.folder_path = folder_path
            session.commit()
            return True
        return False


def add_new_case_for_client_registration(
    case_number: str, name: str, kana_last: str = None, kana_first: str = None,
    rel: str = None, hometown: str = None, zip_code: str = None, pref: str = None,
    city: str = None, street: str = None, building: str = None, dob: str = None, dod: str = None,
    manager_id: int | None = None, operator_id: int | None = None,
    phone_contacts: list[dict] = None, email_contacts: list[dict] = None,
) -> int:
    """新規案件・契約者・被相続人を登録する"""
    parts = name.split(" ", 1)
    name_last = parts[0].strip()
    name_first = parts[1].strip() if len(parts) > 1 else ""
    
    try: dob_date = parse_all_flexible_date(dob) if dob else None
    except ValueError: dob_date = None
    try: dod_date = parse_all_flexible_date(dod) if dod else None
    except ValueError: dod_date = None

    with Session(bind=Engine) as session:
        try:
            new_case = Case(
                case_number=case_number,
                client_name=f"{name_last} {name_first}",
                client_name_kana=f"{kana_last} {kana_first}" if kana_last else None,
                contract_date=date.today(),
                manager_id=manager_id,
                operator_id=operator_id,
            )
            session.add(new_case)
            session.flush()

            new_deceased = Deceased(
                case_id=new_case.case_id,
                name_last="", name_first="", name_last_kana="", name_first_kana="",
                hometown="", date_of_birth=None, date_of_death=None, relationship_type="本人",
            )
            session.add(new_deceased)
            session.flush()

            new_client_heir = Heir(
                deceased_id=new_deceased.id,
                name_last=name_last, name_first=name_first,
                name_last_kana=kana_last, name_first_kana=kana_first,
                hometown=hometown, date_of_birth=dob_date, relationship_type=rel,
                is_contracting_party=True,
            )
            session.add(new_client_heir)
            session.flush()

            if pref and street:
                _update_or_create_address(session, new_client_heir.id, "heir", zip_code, pref, city, street, building)

            if phone_contacts: _create_contact_and_link_to_heir(session, new_client_heir.id, phone_contacts, "PHONE")
            if email_contacts: _create_contact_and_link_to_heir(session, new_client_heir.id, email_contacts, "EMAIL")

            session.commit()
            return new_deceased.id
        except Exception as e:
            session.rollback()
            print(f"契約者登録エラー: {e}")
            return -1


def get_all_heirs():
    """全相続人のリストを返す"""
    with Session(bind=Engine) as session:
        return session.query(Heir).options(joinedload(Heir.deceased).joinedload(Deceased.case)).all()


def get_heir_by_id(heir_id: int):
    """指定IDの相続人詳細を取得"""
    with Session(bind=Engine) as session:
        return session.query(Heir).get(heir_id)


def add_heir(deceased_id: int, name: str, rel: str, kana_last: str = None, kana_first: str = None, dob: str = None, hometown: str = None, zip_code: str = None, pref: str = None, city: str = None, street: str = None, building: str = None, phone_contacts: list[dict] = None, email_contacts: list[dict] = None):
    """相続人を追加"""
    parts = name.split(" ", 1)
    name_last = parts[0].strip()
    name_first = parts[1].strip() if len(parts) > 1 else ""
    try: dob_date = parse_all_flexible_date(dob) if dob else None
    except ValueError: dob_date = None

    new_heir = Heir(
        deceased_id=deceased_id, name_last=name_last, name_first=name_first, relationship_type=rel,
        name_last_kana=kana_last, name_first_kana=kana_first, date_of_birth=dob_date, hometown=hometown,
    )
    with Session(bind=Engine) as session:
        session.add(new_heir)
        session.flush()
        if pref and street:
            _update_or_create_address(session, new_heir.id, "heir", zip_code, pref, city, street, building)
        if phone_contacts: _create_contact_and_link_to_heir(session, new_heir.id, phone_contacts, "PHONE")
        if email_contacts: _create_contact_and_link_to_heir(session, new_heir.id, email_contacts, "EMAIL")
        session.commit()


def update_heir(heir_id: int, name: str, rel: str, kana_last: str = None, kana_first: str = None, hometown: str = None, zip_code: str = None, pref: str = None, city: str = None, street: str = None, building: str = None, phone_contacts: list[dict] = None, email_contacts: list[dict] = None):
    """相続人情報を更新"""
    parts = name.split(" ", 1)
    name_last = parts[0].strip()
    name_first = parts[1].strip() if len(parts) > 1 else ""

    with Session(bind=Engine) as session:
        heir = session.query(Heir).get(heir_id)
        if heir:
            heir.name_last = name_last
            heir.name_first = name_first
            heir.name_last_kana = kana_last
            heir.name_first_kana = kana_first
            heir.relationship_type = rel
            heir.hometown = hometown
            if pref and street:
                _update_or_create_address(session, heir_id, "heir", zip_code, pref, city, street, building)
            _sync_heir_contacts(session, heir_id, phone_contacts or [], email_contacts or [])
            session.commit()


def delete_heir(heir_id: int):
    """相続人を削除"""
    with Session(bind=Engine) as session:
        heir_to_delete = session.query(Heir).get(heir_id)
        if heir_to_delete:
            session.delete(heir_to_delete)
            session.commit()


def get_address_info(owner_type: str, owner_id: int):
    """指定されたエンティティの最新住所を取得"""
    with Session(bind=Engine) as session:
        address_link = None
        if owner_type == "deceased":
            address_link = session.query(D_AddressHistory).filter(D_AddressHistory.deceased_id == owner_id, D_AddressHistory.is_last_address == True).first()
        elif owner_type == "heir":
            address_link = session.query(H_AddressHistory).filter(H_AddressHistory.heir_id == owner_id, H_AddressHistory.is_current_address == True).first()

        if address_link:
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


def get_deceased_address_history(deceased_id: int) -> list[dict]:
    """被相続人の過去の住所履歴を取得"""
    with Session(bind=Engine) as session:
        deceased = session.query(Deceased.last_address_id).filter(Deceased.id == deceased_id).first()
        last_address_id = deceased.last_address_id if deceased else None
        query = session.query(D_AddressHistory, Address).join(Address, D_AddressHistory.address_id == Address.id).filter(D_AddressHistory.deceased_id == deceased_id)
        if last_address_id:
            query = query.filter(D_AddressHistory.address_id != last_address_id)
        history = query.all()
        results = []
        for link, address in history:
            results.append({
                "address_id": address.id, "is_last_address": False,
                "zip_code": address.zip_code or "", "prefecture": address.prefecture or "",
                "city_ward_town": address.city_ward_town or "", "street_address": address.street_address or "",
                "building_name": address.building_name or "",
            })
        return results


def update_case_assignment(case_id: int, manager_id: int | None, operator_id: int | None):
    """案件の担当者を更新"""
    with Session(bind=Engine) as session:
        try:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case:
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
    """連絡先情報を取得"""
    with Session(bind=Engine) as session:
        contact_links = []
        if owner_type == "heir":
            contact_links = session.query(H_ContactLink).options(joinedload(H_ContactLink.contact)).filter(H_ContactLink.heir_id == owner_id).all()
        elif owner_type == "deceased":
            contact_links = session.query(D_ContactLink).options(joinedload(D_ContactLink.contact)).filter(D_ContactLink.deceased_id == owner_id).all()

        contacts = []
        for link in contact_links:
            contact = link.contact
            if contact:
                contacts.append({"value": contact.value or "N/A", "type": contact.type or "N/A", "sub_type": contact.sub_type or "N/A"})
        return contacts


def get_case_id_by_deceased_id(deceased_id: int) -> int | None:
    """Deceased ID から Case ID を取得"""
    with Session(bind=Engine) as session:
        deceased = session.query(Deceased.case_id).filter(Deceased.id == deceased_id).first()
        return deceased.case_id if deceased else None


def is_case_number_duplicate(case_number: str) -> bool:
    """案件番号の重複チェック"""
    existing_case = get_case_by_number(case_number)
    return existing_case is not None


def get_address_by_id(address_id: int) -> Address | None:
    """Address ID から Address レコードを取得"""
    if not address_id: return None
    with Session(bind=Engine) as session:
        return session.query(Address).filter(Address.id == address_id).first()


def get_case_by_id(case_id: int) -> Case | None:
    """Case ID から Case レコードを取得"""
    if case_id is None or case_id <= 0: return None
    with Session(bind=Engine) as session:
        return session.query(Case).filter(Case.case_id == case_id).first()


# 💡 修正: 欠落していた自動化用データ取得関数を追加
def get_financial_asset_automation_data(case_id: int, target_bank_code: str) -> dict | None:
    """Web自動化に必要なデータを取得する"""
    with Session(bind=Engine) as session:
        # Deceased, Case, 住所情報をまとめてロード
        deceased = session.query(Deceased).filter(Deceased.case_id == case_id).options(
            joinedload(Deceased.case),
            joinedload(Deceased.last_address)
        ).first()
        
        if not deceased:
            return None

        # 契約者 Heir を取得
        contracting_heir = session.query(Heir).filter(
            Heir.deceased_id == deceased.id,
            Heir.is_contracting_party == True
        ).first()

        # 契約者の連絡先
        contact_phone = None
        contact_email = None
        if contracting_heir:
            contacts = get_contact_info("heir", contracting_heir.id)
            contact_phone = next((c["value"] for c in contacts if c["type"] == "PHONE"), None)
            contact_email = next((c["value"] for c in contacts if c["type"] == "EMAIL"), None)

        # 代表金融資産を取得（指定された銀行コードに一致するもの）
        representative_asset = session.query(FinancialAsset).join(
            BankMaster, FinancialAsset.bank_id == BankMaster.id
        ).filter(
            FinancialAsset.case_id == case_id,
            BankMaster.bank_code == target_bank_code
        ).options(joinedload(FinancialAsset.branch_ref)).first()

        # 被相続人住所情報
        last_addr = deceased.last_address

        # 結果辞書の構築
        return {
            "case_id": case_id,
            "case_number": deceased.case.case_number,
            "deceased_name": f"{deceased.name_last} {deceased.name_first}",
            "deceased_dob": deceased.date_of_birth.strftime("%Y-%m-%d") if deceased.date_of_birth else None,
            "deceased_last_zip": last_addr.zip_code if last_addr else None,
            "deceased_last_addr1": f"{last_addr.prefecture}{last_addr.city_ward_town}{last_addr.street_address}" if last_addr else None,
            "deceased_last_addr2": last_addr.building_name if last_addr else None,
            # 口座情報（見つかった場合）
            "bank_branch_code": representative_asset.branch_ref.branch_code if representative_asset and representative_asset.branch_ref else None,
            "bank_account_number": representative_asset.account_number if representative_asset else None,
            # 契約者連絡先
            "client_phone": contact_phone,
            "client_email": contact_email,
            "staff_code": deceased.case.manager_id,
            # --- 固定値 (デモ用) ---
            "firm_name_kanji": "行政書士法人チェスター",
            "firm_name_kana": "ギョウセイショシホウジンチェスター",
            "staff_name_kanji": "森町 翼",
            "staff_name_kana": "モリマチ　ツバサ",
            "staff_tel": "050-6864-7034",
            "staff_mail": "t.morimachi_gy@chester-tax.com",
            "firm_zip": "1030028",
            "firm_addr2": "八重洲口会館2階",
            "firm_dob_year": "2013",
            "firm_dob_month": "9",
            "firm_dob_day": "4",
        }


def add_financial_asset_with_type(case_id: int, asset_type: str, bank_id: int, branch_id: int | None, account_type_id: int | None, account_number: str, balance: float, status: str) -> bool:
    """資産種別を指定して金融資産を追加"""
    with Session(bind=Engine) as db:
        try:
            new_asset = FinancialAsset(
                case_id=case_id, asset_type=asset_type, bank_id=bank_id, branch_id=branch_id,
                account_type_id=account_type_id, account_number=account_number, balance=balance, status=status,
            )
            db.add(new_asset)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"金融資産({asset_type})登録エラー: {e}")
            return False


def get_financial_asset_by_case_and_type(case_id: int, asset_type: str) -> list[dict]:
    """資産種別でフィルタリングして金融資産を取得"""
    with Session(bind=Engine) as session:
        assets = session.query(FinancialAsset).filter(FinancialAsset.case_id == case_id, FinancialAsset.asset_type == asset_type).all()
        return [
            {
                "id": a.id, "bank_id": a.bank_id, "branch_id": a.branch_id, "account_type_id": a.account_type_id,
                "bank_name": a.bank_ref.bank_name if a.bank_ref else "N/A",
                "bank_code": a.bank_ref.bank_code if a.bank_ref else "N/A",
                "branch_name": a.branch_ref.branch_name if a.branch_ref else "N/A",
                "branch_code": a.branch_ref.branch_code if a.branch_ref else "N/A",
                "account_type": a.account_type_ref.type_name if a.account_type_ref else "N/A",
                "account_number": a.account_number, "balance": a.balance, "status": a.status,
            }
            for a in assets
        ]


def get_all_tasks_for_case(case_id: int) -> list[dict]:
    """案件の全タスクを取得"""
    with Session(bind=Engine) as session:
        tasks = session.query(Task).filter(Task.case_id == case_id).order_by(Task.due_date, Task.task_id).options(joinedload(Task.assigned_user)).all()
        return [
            {
                "task_id": t.task_id, "description": t.description,
                "due_date": t.due_date.strftime("%Y-%m-%d") if t.due_date else None,
                "is_completed": t.is_completed, "assigned_user_id": t.assigned_user_id,
                "assigned_user_name": t.assigned_user.name if t.assigned_user else "未割当",
                "last_updated_at": t.last_updated_at.strftime("%Y-%m-%d") if t.last_updated_at else None,
            }
            for t in tasks
        ]


def save_task(case_id: int, task_id: int | None, description: str, due_date: str | None, assigned_user_id: int | None, is_completed: bool = False) -> bool:
    """タスクを保存または更新"""
    due_date_obj = None
    if due_date:
        try: due_date_obj = datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError: pass

    with Session(bind=Engine) as session:
        try:
            if task_id:
                task = session.query(Task).get(task_id)
                if not task: return False
                task.description = description
                task.due_date = due_date_obj
                task.assigned_user_id = assigned_user_id
                task.is_completed = is_completed
                task.last_updated_at = datetime.now()
            else:
                new_task = Task(case_id=case_id, description=description, due_date=due_date_obj, assigned_user_id=assigned_user_id, is_completed=is_completed, last_updated_at=datetime.now())
                session.add(new_task)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"タスク保存エラー: {e}")
            return False


def delete_task(task_id: int) -> bool:
    """タスクを削除"""
    with Session(bind=Engine) as session:
        try:
            task = session.query(Task).get(task_id)
            if task:
                session.delete(task)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"タスク削除エラー: {e}")
            return False


def toggle_task_completion(task_id: int, is_completed: bool) -> bool:
    """タスク完了状態を切り替え"""
    with Session(bind=Engine) as session:
        try:
            task = session.query(Task).get(task_id)
            if task:
                task.is_completed = is_completed
                task.last_updated_at = datetime.now()
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"タスク状態更新エラー: {e}")
            return False


# 💡 修正: 欠落していたKintone連携用データ取得関数を追加
def get_kintone_integration_data(case_id: int) -> dict | None:
    """Kintone連携用データを取得"""
    with Session(bind=Engine) as session:
        # DeceasedをCaseと共に取得
        deceased = session.query(Deceased).filter(Deceased.case_id == case_id).options(
            joinedload(Deceased.case)
        ).first()
        
        if not deceased:
            return None
        
        case = deceased.case
        
        # 契約者(Heir)を取得
        contracting_heir = session.query(Heir).filter(
            Heir.deceased_id == deceased.id, 
            Heir.is_contracting_party == True
        ).first()

        # 変数初期化
        client_name, client_kana, client_zip, client_addr, client_tel, client_mail = "", "", "", "", "", ""

        if contracting_heir:
            client_name = f"{contracting_heir.name_last}　{contracting_heir.name_first}"
            client_kana = f"{contracting_heir.name_last_kana}　{contracting_heir.name_first_kana}"
            
            # 住所取得
            addr_info = get_address_info("heir", contracting_heir.id)
            client_zip = addr_info.get("zip_code", "")
            client_addr = f"{addr_info.get('prefecture','')}{addr_info.get('city_ward_town','')}{addr_info.get('street_address','')}"
            if addr_info.get("building_name"):
                client_addr += f" {addr_info.get('building_name')}"
            
            # 連絡先取得
            contacts = get_contact_info("heir", contracting_heir.id)
            client_tel = next((c["value"] for c in contacts if c["type"] == "PHONE"), "")
            client_mail = next((c["value"] for c in contacts if c["type"] == "EMAIL"), "")

        deceased_name = f"{deceased.name_last}　{deceased.name_first}"
        deceased_kana = f"{deceased.name_last_kana}　{deceased.name_first_kana}"
        inheritance_date = deceased.date_of_death.strftime("%Y-%m-%d") if deceased.date_of_death else ""

        return {
            "case_number": case.case_number,
            "client_name": client_name,
            "client_kana": client_kana,
            "client_zip": client_zip,
            "client_addr": client_addr,
            "client_tel": client_tel,
            "client_mail": client_mail,
            "deceased_name": deceased_name,
            "deceased_kana": deceased_kana,
            "inheritance_date": inheritance_date,
        }


def get_deceased_by_case_id(case_id: int):
    """案件IDから被相続人情報を取得（Eager Load）"""
    with Session(bind=Engine) as session:
        options_load = (
            joinedload(Deceased.heirs),
            joinedload(Deceased.case).joinedload(Case.manager),
            joinedload(Deceased.case).joinedload(Case.operator),
            joinedload(Deceased.case).joinedload(Case.status_ref),
            joinedload(Deceased.last_address),
        )
        return session.query(Deceased).options(*options_load).filter(Deceased.case_id == case_id).first()