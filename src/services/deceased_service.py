# src/services/deceased_service.py
import datetime
from typing import List, Optional, Dict, Any, Union
import requests
# 💡 修正: os, re のインポートを追加
import os 
import re 
from sqlalchemy import func, desc
from sqlalchemy.orm import joinedload, Session

from src.models.database import SessionLocal
from src.models.tables import (
    Case,
    Deceased,
    Heir,
    Address,
    Contact,
    User,
    CaseStatus,
    H_AddressHistory,
    H_ContactLink,
    D_AddressHistory,
    D_ContactLink,
    Task,
    FinancialAsset,
    BankMaster,
    BranchMaster,
    AccountTypeMaster
)
from src.utils.date_utils import parse_all_flexible_date # 💡 修正: date_utilsのインポートをファイル先頭に移動

# --- パス正規化ロジック (新規関数をここに配置) ---

def normalize_folder_path(raw_path: str) -> str:
    """
    WindowsのUNCパス（ネットワーク共有パス）を正規化する。
    \\\\192.168.11.20\\... のような過剰なバックスラッシュを修正する。
    """
    if not raw_path:
        return ""
    
    # 1. バックスラッシュをスラッシュに一旦置換して解析しやすくする
    normalized = raw_path.replace("\\", "/")
    
    if os.name == "nt":
        # Windows環境の場合
        
        # 先頭の二重スラッシュ（UNCパスの開始）を二重バックスラッシュ（Python文字列として '\\\\'）に戻す
        if normalized.startswith("//"):
            normalized = normalized.lstrip("/")
            normalized = f"\\\\{normalized}"
            
        # 連続するバックスラッシュ（Python表記 \\\\, \\\\, ...）を単一のバックスラッシュに修正
        # Pythonの文字列として '\\' は \ を表す
        normalized = re.sub(r"\\{2,}", r"\\", normalized)
        
        # 先頭の二重バックスラッシュだけを維持し、それ以外を単一にする
        if normalized.startswith("\\\\"):
            # 先頭の \\ を保持し、残りのパスを修正
            path_parts = normalized[2:].split("\\")
            normalized = "\\\\" + "\\".join(path_parts)
        
    else:
        # POSIX環境の場合、スラッシュに統一
        normalized = normalized.replace("\\", "/")
    
    return normalized


# --- ユーティリティ ---

def get_db():
    return SessionLocal()

# --- ユーザー・ステータス関連 ---

def get_all_users() -> Dict[int, str]:
    """全てのユーザーIDと名前を取得する"""
    db = SessionLocal()
    try:
        users = db.query(User.id, User.name).order_by(User.id).all()
        return {u.id: u.name for u in users}
    finally:
        db.close()

def get_all_case_statuses():
    db = SessionLocal()
    try:
        return db.query(CaseStatus).order_by(CaseStatus.order_num).all()
    finally:
        db.close()

# --- 案件 (Case) 関連 ---

def get_case_by_id(case_id: int) -> Optional[Case]:
    db = SessionLocal()
    try:
        return db.query(Case).filter(Case.case_id == case_id).first()
    finally:
        db.close()

def get_contracting_party_name(case_id: int) -> str:
    """案件の契約者名を取得する"""
    db = SessionLocal()
    try:
        case = db.query(Case).get(case_id)
        return case.client_name if case else ""
    finally:
        db.close()

def get_case_folder_path(case_id: int) -> Optional[str]:
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.case_id == case_id).first()
        # 💡 修正: 取得時に正規化を行う
        return normalize_folder_path(case.folder_path) if case and case.folder_path else None
    finally:
        db.close()

def get_case_folder_path_service(case_id: int) -> Optional[str]:
    # 💡 修正: normalize_folder_pathを含むget_case_folder_pathを呼び出す
    return get_case_folder_path(case_id)

def update_case_folder_path(case_id: int, folder_path: str) -> bool:
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.case_id == case_id).first()
        if case:
            # 💡 修正: 保存前に正規化を行う
            case.folder_path = normalize_folder_path(folder_path)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Error updating folder path: {e}")
        return False
    finally:
        db.close()

def update_case_assignment(case_id: int, manager_id: Optional[int], operator_id: Optional[int]) -> bool:
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.case_id == case_id).first()
        if case:
            case.manager_id = manager_id
            case.operator_id = operator_id
            db.commit()
            return True
        return False
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()

def get_next_case_number_service() -> str:
    db = SessionLocal()
    try:
        return f"G{datetime.datetime.now().strftime('%y%m%d%H%M')}"
    finally:
        db.close()

def is_case_number_duplicate(case_number: str) -> bool:
    db = SessionLocal()
    try:
        exists = db.query(Case).filter(Case.case_number == case_number).first()
        return exists is not None
    finally:
        db.close()

def delete_case_and_all_related_data(case_number: str) -> bool:
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.case_number == case_number).first()
        if case:
            db.delete(case) 
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Delete Error: {e}")
        return False
    finally:
        db.close()

def get_case_progress_summary(case_id: int) -> dict:
    return {"status": "進行中", "progress": 50}

# --- 被相続人 (Deceased) 関連 ---

def get_deceased_by_case_id(case_id: int) -> Optional[Deceased]:
    db = SessionLocal()
    try:
        return db.query(Deceased).options(joinedload(Deceased.case)).filter(Deceased.case_id == case_id).first()
    finally:
        db.close()

def get_deceased_by_id(deceased_id: int) -> Optional[Deceased]:
    db = SessionLocal()
    try:
        return db.query(Deceased).options(
            joinedload(Deceased.heirs),
            joinedload(Deceased.case),
            joinedload(Deceased.last_address)
        ).filter(Deceased.id == deceased_id).first()
    finally:
        db.close()

def get_case_id_by_deceased_id(deceased_id: int) -> Optional[int]:
    db = SessionLocal()
    try:
        d = db.query(Deceased).filter(Deceased.id == deceased_id).first()
        return d.case_id if d else None
    finally:
        db.close()

def update_deceased(
    deceased_id: int,
    name_last: str,
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
    past_addresses: list = None,
    phone_contacts: list = None,
    email_contacts: list = None,
) -> bool:
    db = SessionLocal()
    try:
        d = db.query(Deceased).get(deceased_id)
        if not d:
            return False

        d.name_last = name_last
        d.name_first = name_first
        d.name_last_kana = kana_last
        d.name_first_kana = kana_first
        d.hometown = hometown
        
        # from src.utils.date_utils import parse_all_flexible_date # 削除 (ファイル先頭でインポート済み)
        if dob: d.date_of_birth = parse_all_flexible_date(dob)
        if dod: d.date_of_death = parse_all_flexible_date(dod)

        if last_pref or last_street:
            if d.last_address_id:
                addr = db.query(Address).get(d.last_address_id)
                addr.zip_code = last_zip_code
                addr.prefecture = last_pref
                addr.city_ward_town = last_city
                addr.street_address = last_street
                addr.building_name = last_building
            else:
                new_addr = Address(
                    zip_code=last_zip_code, prefecture=last_pref,
                    city_ward_town=last_city, street_address=last_street,
                    building_name=last_building
                )
                db.add(new_addr)
                db.flush()
                d.last_address_id = new_addr.id

        _update_contacts(db, "deceased", deceased_id, phone_contacts, "PHONE")
        _update_contacts(db, "deceased", deceased_id, email_contacts, "EMAIL")

        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Update Deceased Error: {e}")
        raise e
    finally:
        db.close()

# --- 相続人 (Heir) 関連 ---

def get_heir_by_id(heir_id: int) -> Optional[Heir]:
    db = SessionLocal()
    try:
        return db.query(Heir).get(heir_id)
    finally:
        db.close()

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
    phone_contacts: list = None,
    email_contacts: list = None
) -> int:
    db = SessionLocal()
    try:
        parts = name.split(" ", 1)
        last = parts[0]
        first = parts[1] if len(parts) > 1 else ""

        # from src.utils.date_utils import parse_all_flexible_date # 削除 (ファイル先頭でインポート済み)
        dob_date = parse_all_flexible_date(dob) if dob else None

        new_heir = Heir(
            deceased_id=deceased_id,
            name_last=last,
            name_first=first,
            name_last_kana=kana_last,
            name_first_kana=kana_first,
            relationship_type=rel,
            hometown=hometown,
            date_of_birth=dob_date
        )
        db.add(new_heir)
        db.flush()

        if pref or street:
            new_addr = Address(
                zip_code=zip_code, prefecture=pref, city_ward_town=city,
                street_address=street, building_name=building
            )
            db.add(new_addr)
            db.flush()
            db.add(H_AddressHistory(heir_id=new_heir.id, address_id=new_addr.id, is_current_address=True))

        _add_contacts_to_heir(db, new_heir.id, phone_contacts, "PHONE")
        _add_contacts_to_heir(db, new_heir.id, email_contacts, "EMAIL")

        db.commit()
        return new_heir.id
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

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
    phone_contacts: list = None,
    email_contacts: list = None,
    dob: str = None,
    hometown: str = None
) -> bool:
    db = SessionLocal()
    try:
        heir = db.query(Heir).get(heir_id)
        if not heir: return False

        parts = name.split(" ", 1)
        heir.name_last = parts[0]
        heir.name_first = parts[1] if len(parts) > 1 else ""
        heir.relationship_type = rel
        heir.name_last_kana = kana_last
        heir.name_first_kana = kana_first
        heir.hometown = hometown
        
        if dob:
            # from src.utils.date_utils import parse_all_flexible_date # 削除 (ファイル先頭でインポート済み)
            heir.date_of_birth = parse_all_flexible_date(dob)

        if pref or street:
            current_link = db.query(H_AddressHistory).filter(
                H_AddressHistory.heir_id == heir_id,
                H_AddressHistory.is_current_address == True
            ).first()
            
            if current_link:
                addr = db.query(Address).get(current_link.address_id)
                addr.zip_code = zip_code
                addr.prefecture = pref
                addr.city_ward_town = city
                addr.street_address = street
                addr.building_name = building
            else:
                new_addr = Address(
                    zip_code=zip_code, prefecture=pref, city_ward_town=city,
                    street_address=street, building_name=building
                )
                db.add(new_addr)
                db.flush()
                db.add(H_AddressHistory(heir_id=heir_id, address_id=new_addr.id, is_current_address=True))

        _update_contacts(db, "heir", heir_id, phone_contacts, "PHONE")
        _update_contacts(db, "heir", heir_id, email_contacts, "EMAIL")

        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def delete_heir(heir_id: int) -> bool:
    db = SessionLocal()
    try:
        heir = db.query(Heir).get(heir_id)
        if heir:
            db.delete(heir)
            db.commit()
            return True
        return False
    finally:
        db.close()

def add_new_case_for_client_registration(
    case_number, name, kana_last, kana_first, rel, hometown,
    zip_code, pref, city, street, building,
    dob, dod, manager_id, operator_id,
    phone_contacts, email_contacts
) -> int:
    db = SessionLocal()
    try:
        new_case = Case(
            case_number=case_number,
            client_name=name,
            client_name_kana=f"{kana_last} {kana_first}".strip(),
            manager_id=manager_id,
            operator_id=operator_id,
            current_status_id=1,
            contract_date=datetime.date.today()
        )
        db.add(new_case)
        db.flush()

        new_deceased = Deceased(
            case_id=new_case.case_id,
            name_last="",
            name_first="",
            relationship_type="本人"
        )
        if dod:
            # from src.utils.date_utils import parse_all_flexible_date # 削除 (ファイル先頭でインポート済み)
            new_deceased.date_of_death = parse_all_flexible_date(dod)
            
        db.add(new_deceased)
        db.flush()

        parts = name.split(" ", 1)
        n_last = parts[0]
        n_first = parts[1] if len(parts) > 1 else ""
        
        new_heir = Heir(
            deceased_id=new_deceased.id,
            name_last=n_last,
            name_first=n_first,
            name_last_kana=kana_last,
            name_first_kana=kana_first,
            relationship_type=rel,
            hometown=hometown,
            is_contracting_party=True
        )
        db.add(new_heir)
        db.flush()

        if pref or street:
            addr = Address(
                zip_code=zip_code, prefecture=pref, city_ward_town=city,
                street_address=street, building_name=building
            )
            db.add(addr)
            db.flush()
            db.add(H_AddressHistory(heir_id=new_heir.id, address_id=addr.id, is_current_address=True))

        _add_contacts_to_heir(db, new_heir.id, phone_contacts, "PHONE")
        _add_contacts_to_heir(db, new_heir.id, email_contacts, "EMAIL")

        db.commit()
        return new_deceased.id

    except Exception as e:
        db.rollback()
        print(f"Registration Error: {e}")
        return -1
    finally:
        db.close()

# --- 住所・連絡先ヘルパー ---

def get_address_by_id(address_id: int) -> Optional[Address]:
    db = SessionLocal()
    try:
        return db.query(Address).get(address_id)
    finally:
        db.close()

def get_address_info(target_type: str, target_id: int) -> dict:
    db = SessionLocal()
    try:
        addr = None
        if target_type == "heir":
            link = db.query(H_AddressHistory).filter(
                H_AddressHistory.heir_id == target_id,
                H_AddressHistory.is_current_address == True
            ).first()
            if link:
                addr = db.query(Address).get(link.address_id)
        elif target_type == "deceased":
            d = db.query(Deceased).get(target_id)
            if d and d.last_address_id:
                addr = db.query(Address).get(d.last_address_id)
        
        if addr:
            return {
                "zip_code": addr.zip_code,
                "prefecture": addr.prefecture,
                "city_ward_town": addr.city_ward_town,
                "street_address": addr.street_address,
                "building_name": addr.building_name
            }
        return {}
    finally:
        db.close()

def get_contact_info(target_type: str, target_id: int) -> List[dict]:
    db = SessionLocal()
    try:
        contacts = []
        if target_type == "heir":
            links = db.query(H_ContactLink).filter(H_ContactLink.heir_id == target_id).all()
            for link in links:
                c = db.query(Contact).get(link.contact_id)
                if c: contacts.append({"id": c.id, "type": c.type, "value": c.value, "sub_type": c.sub_type})
        elif target_type == "deceased":
            links = db.query(D_ContactLink).filter(D_ContactLink.deceased_id == target_id).all()
            for link in links:
                c = db.query(Contact).get(link.contact_id)
                if c: contacts.append({"id": c.id, "type": c.type, "value": c.value, "sub_type": c.sub_type})
        return contacts
    finally:
        db.close()

def get_deceased_address_history(deceased_id: int) -> List[dict]:
    db = SessionLocal()
    try:
        links = db.query(D_AddressHistory).filter(D_AddressHistory.deceased_id == deceased_id).all()
        history = []
        for link in links:
            if not link.is_last_address:
                addr = db.query(Address).get(link.address_id)
                if addr:
                    history.append({
                        "address_id": addr.id,
                        "zip_code": addr.zip_code,
                        "prefecture": addr.prefecture,
                        "city_ward_town": addr.city_ward_town,
                        "street_address": addr.street_address,
                        "building_name": addr.building_name
                    })
        return history
    finally:
        db.close()

# --- 内部ヘルパー ---

def _add_contacts_to_heir(db, heir_id, contact_list, type_str):
    if not contact_list: return
    for c in contact_list:
        val = c.get("value")
        sub = c.get("sub_type", "Primary")
        if val:
            new_c = Contact(value=val, type=type_str, sub_type=sub)
            db.add(new_c)
            db.flush()
            db.add(H_ContactLink(heir_id=heir_id, contact_id=new_c.id))

def _update_contacts(db, target_type, target_id, contact_list, type_str):
    if target_type == "heir":
        links = db.query(H_ContactLink).join(Contact).filter(
            H_ContactLink.heir_id == target_id,
            Contact.type == type_str
        ).all()
        for link in links:
            db.delete(link) 
        _add_contacts_to_heir(db, target_id, contact_list, type_str)
    
    elif target_type == "deceased":
        links = db.query(D_ContactLink).join(Contact).filter(
            D_ContactLink.deceased_id == target_id,
            Contact.type == type_str
        ).all()
        for link in links:
            db.delete(link)
            
        if contact_list:
            for c in contact_list:
                val = c.get("value")
                sub = c.get("sub_type", "Primary")
                if val:
                    new_c = Contact(value=val, type=type_str, sub_type=sub)
                    db.add(new_c)
                    db.flush()
                    db.add(D_ContactLink(deceased_id=target_id, contact_id=new_c.id))

# --- その他 ---

def search_address_by_zip_api(zip_code: str) -> Optional[dict]:
    if not zip_code: return None
    clean_zip = zip_code.replace("-", "")
    if len(clean_zip) != 7: return None
    try:
        url = f"https://zipcloud.ibsnet.co.jp/api/search?zipcode={clean_zip}"
        res = requests.get(url)
        data = res.json()
        if data and data.get("results"):
            r = data["results"][0]
            return {
                "prefecture": r["address1"],
                "city_ward_town": r["address2"],
                "street_address": r["address3"]
            }
        return {}
    except Exception:
        return None

def get_kintone_integration_data(case_id: int) -> dict:
    case = get_case_by_id(case_id)
    if not case: return {}
    deceased = get_deceased_by_case_id(case_id)
    deceased_name = f"{deceased.name_last} {deceased.name_first}" if deceased else ""
    return {
        "case_number": case.case_number,
        "client_name": case.client_name,
        "deceased_name": deceased_name
    }

# --- 金融資産・書類作成関連 ---

def get_financial_asset_by_case(case_id: int):
    db = SessionLocal()
    try:
        assets = db.query(FinancialAsset).filter(FinancialAsset.case_id == case_id).all()
        return [
            {
                "id": a.id,
                "bank_code": a.bank_ref.bank_code if a.bank_ref else "",
                "bank_name": a.bank_ref.bank_name if a.bank_ref else "",
                "branch_name": a.branch_ref.branch_name if a.branch_ref else "",
                "branch_code": a.branch_ref.branch_code if a.branch_ref else "",
                "account_type": a.account_type_ref.type_name if a.account_type_ref else "",
                "account_number": a.account_number,
                "balance": a.balance,
                "status": a.status
            }
            for a in assets
        ]
    finally:
        db.close()

def get_bank_cert_document_data(case_id: int, bank_code: str) -> dict:
    db = SessionLocal()
    try:
        case = db.query(Case).get(case_id)
        if not case: return {}

        deceased = db.query(Deceased).filter(Deceased.case_id == case_id).first()
        client = None
        if deceased:
            client = db.query(Heir).filter(Heir.deceased_id == deceased.id, Heir.is_contracting_party == True).first()

        assets = db.query(FinancialAsset).join(BankMaster).filter(
            FinancialAsset.case_id == case_id,
            BankMaster.bank_code == bank_code
        ).all()

        res = {
            "case_number": case.case_number,
            "deceased": {
                "last_name": deceased.name_last if deceased else "",
                "first_name": deceased.name_first if deceased else "",
                "date_of_death": deceased.date_of_death if deceased else None,
            } if deceased else {},
            "contracting_party": {
                "last_name": client.name_last if client else "",
                "first_name": client.name_first if client else "",
            } if client else {},
            "bank_assets": []
        }
        
        for a in assets:
            branch_name = a.branch_ref.branch_name if a.branch_ref else ""
            branch_code = a.branch_ref.branch_code if a.branch_ref else ""
            type_name = a.account_type_ref.type_name if a.account_type_ref else ""
            
            res["bank_assets"].append({
                "id": a.id,
                "bank_name": a.bank_ref.bank_name,
                "branch_name": branch_name,
                "branch_code": branch_code,
                "account_type": type_name,
                "account_number": a.account_number,
                "balance": a.balance
            })
            
        return res
    finally:
        db.close()

def get_financial_assets_by_bank_code(case_id: int, bank_code: str) -> List[dict]:
    data = get_bank_cert_document_data(case_id, bank_code)
    return data.get("bank_assets", [])

def get_financial_asset_automation_data(case_id: int, bank_code: str) -> dict:
    """
    Web自動化（来店予約など）に必要なデータを辞書形式で取得する
    """
    db = SessionLocal()
    try:
        # 1. 案件と被相続人
        case = db.query(Case).get(case_id)
        deceased = db.query(Deceased).filter(Deceased.case_id == case_id).first()
        
        if not case or not deceased:
            return {}

        # 2. 契約者
        client = db.query(Heir).filter(Heir.deceased_id == deceased.id, Heir.is_contracting_party == True).first()
        
        # 3. 指定された銀行の資産情報 (最初に見つかったものを使用)
        asset = (
            db.query(FinancialAsset)
            .join(BankMaster, FinancialAsset.bank_id == BankMaster.id)
            .outerjoin(BranchMaster, FinancialAsset.branch_id == BranchMaster.id)
            .filter(FinancialAsset.case_id == case_id, BankMaster.bank_code == bank_code)
            .first()
        )

        # 4. 契約者の連絡先取得
        client_tel = ""
        client_mail = ""
        if client:
            contacts = get_contact_info("heir", client.id)
            # 携帯電話を優先、なければ最初の電話番号
            client_tel = next((c["value"] for c in contacts if c["type"] == "PHONE" and c.get("sub_type") == "携帯"), "")
            if not client_tel:
                client_tel = next((c["value"] for c in contacts if c["type"] == "PHONE"), "")
            
            client_mail = next((c["value"] for c in contacts if c["type"] == "EMAIL"), "")

        # 5. データ構築
        data = {
            "case_number": case.case_number,
            "deceased_name": f"{deceased.name_last} {deceased.name_first}",
            "deceased_dob": deceased.date_of_birth.isoformat() if deceased.date_of_birth else "",
            
            # 契約者（担当者扱い）情報
            "contractor_name": f"{client.name_last} {client.name_first}" if client else "",
            "contractor_name_kana": f"{client.name_last_kana} {client.name_first_kana}" if client else "",
            
            # 自動化スクリプトが期待するキー名
            "staff_code": case.case_number, # 便宜上案件番号を使用
            "staff_name_kanji": f"{client.name_last} {client.name_first}" if client else "",
            "staff_name_kana": f"{client.name_last_kana} {client.name_first_kana}" if client else "",
            "staff_tel": client_tel,
            "staff_mail": client_mail,
            "client_phone": client_tel,
            "client_email": client_mail,

            # 銀行情報
            "bank_branch_code": asset.branch_ref.branch_code if asset and asset.branch_ref else "",
            "bank_account_number": asset.account_number if asset else "",
            
            # 法人/事務所 固定情報 (デフォルト値)
            "firm_name_kanji": "行政書士法人チェスター",
            "firm_name_kana": "ギョウセイショシホウジンチェスター",
            "firm_zip": "1030028",
            "firm_addr2": "八重洲口会館2階",
            "firm_dob_year": "2000",
            "firm_dob_month": "1",
            "firm_dob_day": "1",
        }
        return data
    finally:
        db.close()

# --- 金融資産・マスタ管理 ---

def get_bank_masters(db=None) -> List[BankMaster]:
    """全ての銀行マスタを取得"""
    # 互換性のため db 引数を受け取るが、渡されなければ内部で生成
    local_session = False
    if db is None:
        db = SessionLocal()
        local_session = True
    try:
        return db.query(BankMaster).order_by(BankMaster.bank_code).all()
    finally:
        if local_session:
            db.close()

def get_bank_master_by_id(bank_id: int) -> Optional[BankMaster]:
    db = SessionLocal()
    try:
        return db.query(BankMaster).get(bank_id)
    finally:
        db.close()

def get_branch_masters_by_bank_id(bank_id: int) -> List[BranchMaster]:
    db = SessionLocal()
    try:
        return db.query(BranchMaster).filter(BranchMaster.bank_id == bank_id).all()
    finally:
        db.close()

def get_account_type_masters(db=None) -> List[AccountTypeMaster]:
    """全ての口座種類マスタを取得"""
    local_session = False
    if db is None:
        db = SessionLocal()
        local_session = True
    try:
        return db.query(AccountTypeMaster).all()
    finally:
        if local_session:
            db.close()

def add_or_update_bank_master(bank_id: Optional[int], name: str, code: str) -> Optional[BankMaster]:
    db = SessionLocal()
    try:
        if bank_id:
            bank = db.query(BankMaster).get(bank_id)
            if bank:
                bank.bank_name = name
                bank.bank_code = code
        else:
            # 重複チェック
            if db.query(BankMaster).filter(BankMaster.bank_code == code).first():
                return None # 簡易エラー処理
            bank = BankMaster(bank_name=name, bank_code=code)
            db.add(bank)
        
        db.commit()
        db.refresh(bank)
        return bank
    except Exception as e:
        db.rollback()
        print(f"Bank Master Error: {e}")
        return None
    finally:
        db.close()

def add_branch_master(bank_id: int, name: str, code: str) -> Optional[BranchMaster]:
    db = SessionLocal()
    try:
        if db.query(BranchMaster).filter(BranchMaster.bank_id == bank_id, BranchMaster.branch_code == code).first():
            raise ValueError("Duplicate branch code")
        
        branch = BranchMaster(bank_id=bank_id, branch_name=name, branch_code=code)
        db.add(branch)
        db.commit()
        db.refresh(branch)
        return branch
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def add_account_type_master(db=None, type_name: str = "") -> Optional[AccountTypeMaster]:
    """口座種類マスタを追加"""
    local_session = False
    if db is None:
        db = SessionLocal()
        local_session = True
    try:
        if db.query(AccountTypeMaster).filter(AccountTypeMaster.type_name == type_name).first():
            return None
        
        new_type = AccountTypeMaster(type_name=type_name)
        db.add(new_type)
        db.commit()
        db.refresh(new_type)
        return new_type
    except Exception as e:
        db.rollback()
        print(f"Account Type Error: {e}")
        return None
    finally:
        if local_session:
            db.close()

def get_financial_asset_by_case_and_type(case_id: int, asset_type: str) -> List[dict]:
    db = SessionLocal()
    try:
        assets = db.query(FinancialAsset).filter(
            FinancialAsset.case_id == case_id,
            FinancialAsset.asset_type == asset_type
        ).all()
        
        res = []
        for a in assets:
            res.append({
                "id": a.id,
                "asset_type": a.asset_type,
                "bank_id": a.bank_id,
                "bank_name": a.bank_ref.bank_name if a.bank_ref else "不明",
                "bank_code": a.bank_ref.bank_code if a.bank_ref else "",
                "branch_id": a.branch_id,
                "branch_name": a.branch_ref.branch_name if a.branch_ref else "",
                "branch_code": a.branch_ref.branch_code if a.branch_ref else "",
                "account_type_id": a.account_type_id,
                "account_type": a.account_type_ref.type_name if a.account_type_ref else "",
                "account_number": a.account_number,
                "balance": a.balance,
                "status": a.status
            })
        return res
    finally:
        db.close()

def add_financial_asset_with_type(
    case_id: int, asset_type: str, bank_id: int, branch_id: Optional[int],
    account_type_id: Optional[int], account_number: str, balance: float, status: str
) -> bool:
    db = SessionLocal()
    try:
        asset = FinancialAsset(
            case_id=case_id,
            asset_type=asset_type,
            bank_id=bank_id,
            branch_id=branch_id,
            account_type_id=account_type_id,
            account_number=account_number,
            balance=balance,
            status=status
        )
        db.add(asset)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Add Asset Error: {e}")
        return False
    finally:
        db.close()

# 💡 ラッパー関数: デフォルトで銀行資産として登録
def add_financial_asset(
    case_id: int, bank_id: int, branch_id: Optional[int],
    account_type_id: Optional[int], account_number: str, balance: float, status: str
) -> bool:
    return add_financial_asset_with_type(
        case_id, "BANK", bank_id, branch_id, account_type_id, account_number, balance, status
    )

def update_financial_asset(
    asset_id: int, bank_id: int, branch_id: Optional[int],
    account_type_id: Optional[int], account_number: str, balance: float, status: str
) -> bool:
    db = SessionLocal()
    try:
        asset = db.query(FinancialAsset).get(asset_id)
        if asset:
            asset.bank_id = bank_id
            asset.branch_id = branch_id
            asset.account_type_id = account_type_id
            asset.account_number = account_number
            asset.balance = balance
            asset.status = status
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Update Asset Error: {e}")
        return False
    finally:
        db.close()

def delete_financial_asset(asset_id: int) -> bool:
    db = SessionLocal()
    try:
        asset = db.query(FinancialAsset).get(asset_id)
        if asset:
            db.delete(asset)
            db.commit()
            return True
        return False
    finally:
        db.close()

# --- タスク管理用関数 ---

def get_all_tasks_for_case(case_id: int) -> List[dict]:
    """案件に関連する全てのタスクを取得"""
    db = SessionLocal()
    try:
        tasks = (
            db.query(Task, User.name)
            .outerjoin(User, Task.assigned_user_id == User.id)
            .filter(Task.case_id == case_id)
            .order_by(Task.due_date)
            .all()
        )
        result = []
        for task, user_name in tasks:
            result.append({
                "task_id": task.task_id,
                "case_id": task.case_id,
                "description": task.description,
                "due_date": task.due_date.strftime("%Y-%m-%d") if task.due_date else None,
                "assigned_user_id": task.assigned_user_id,
                "assigned_user_name": user_name if user_name else "未割当",
                "is_completed": task.is_completed,
            })
        return result
    finally:
        db.close()

def save_task(case_id: int, task_id: Optional[int], description: str, due_date: str, assigned_user_id: Optional[int], is_completed: bool = False) -> bool:
    """タスクの作成または更新"""
    db = SessionLocal()
    try:
        # 日付変換
        dt_due = None
        if due_date:
            # from src.utils.date_utils import parse_all_flexible_date # 削除 (ファイル先頭でインポート済み)
            d = parse_all_flexible_date(due_date)
            if d:
                # datetime型へ変換
                dt_due = datetime.datetime.combine(d, datetime.time.min)

        if task_id:
            task = db.query(Task).get(task_id)
            if task:
                task.description = description
                task.due_date = dt_due
                task.assigned_user_id = assigned_user_id
                task.is_completed = is_completed
        else:
            new_task = Task(
                case_id=case_id,
                description=description,
                due_date=dt_due,
                assigned_user_id=assigned_user_id,
                is_completed=is_completed,
            )
            db.add(new_task)
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Save Task Error: {e}")
        return False
    finally:
        db.close()

def delete_task(task_id: int) -> bool:
    """タスクの削除"""
    db = SessionLocal()
    try:
        task = db.query(Task).get(task_id)
        if task:
            db.delete(task)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Delete Task Error: {e}")
        return False
    finally:
        db.close()

# 既存の関数との整合性を維持
def get_incomplete_tasks(user_id=None):
    db = SessionLocal()
    try:
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
    finally:
        db.close()

def get_case_list(search_term="", status_id=None, user_id=None):
    db = SessionLocal()
    try:
        query = (
            db.query(
                Case,
                Deceased.name_last,
                Deceased.name_first,
                CaseStatus.name.label("status_name"),
                Task.description,
                Task.last_updated_at,
            )
            .join(Case.deceased_ref, isouter=True)
            .join(Case.status_ref, isouter=True)
            .join(Task, Case.case_id == Task.case_id, isouter=True)
            .order_by(Case.contract_date.desc())
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

        cases_data = query.limit(100).all()

        case_list = []
        processed_ids = set()

        for case, d_last, d_first, status_name, description, last_updated_at in cases_data:
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
                    "contract_date": case.contract_date.strftime("%Y/%m/%d")
                    if case.contract_date
                    else "N/A",
                    "status": status_name if status_name else "未設定",
                    "role_label": role_label,
                    "manager_id": case.manager_id,
                    "operator_id": case.operator_id,
                    "description": description if description else "",
                    "last_updated_at": last_updated_at.strftime("%Y/%m/%d")
                    if last_updated_at
                    else "N/A",
                }
            )
        return case_list
    finally:
        db.close()

def get_my_cases(user_id: int, limit: int = 10):
    db = SessionLocal()
    try:
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
                if case.deceased_ref
                else "N/A"
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
    finally:
        db.close()

def get_user_capacity_data():
    db = SessionLocal()
    try:
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
    finally:
        db.close()