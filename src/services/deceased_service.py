# src/services/deceased_service.py
import datetime
import os
import shutil
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from sqlalchemy import func, or_
from sqlalchemy.orm import aliased, joinedload

from src.models.database import SessionLocal
from src.models.tables import (
    AccountTypeMaster,
    Address,
    BankMaster,
    BranchMaster,
    Case,
    CaseStatus,
    Contact,
    D_AddressHistory,
    D_ContactLink,
    Deceased,
    FinancialAsset,
    H_AddressHistory,
    H_ContactLink,
    Heir,
    Task,
    User,
    InsuranceAsset,
    OtherAsset,
    Liability,
    Expense,
    CaseSubmissionDoc
)
from src.utils.date_utils import parse_all_flexible_date

# --- 1. ファイル操作・自動仕分け・ステータス更新 ---

def normalize_folder_path(path_str: str) -> str:
    """フォルダパスを正規化しWindows形式に統一する"""
    if not path_str:
        return ""
    cleaned = path_str.strip().strip('"').strip("'")
    return cleaned.replace("/", "\\")

def get_contractor_surname(case_id: int) -> str:
    """案件IDから契約者（依頼者）の姓を取得する"""
    db = SessionLocal()
    try:
        deceased = db.query(Deceased).filter(Deceased.case_id == case_id).first()
        if not deceased: return "様"
        
        contractor = db.query(Heir).filter(
            Heir.deceased_id == deceased.id,
            Heir.is_contracting_party == True
        ).first()
        
        if contractor: return contractor.name_last
        
        case = db.query(Case).get(case_id)
        return case.client_name.split()[0] if case and case.client_name else "顧客"
    finally:
        db.close()

def find_case_subfolder_by_keyword(case_id: int, keyword: str) -> Path:
    """案件フォルダ内からキーワードを含むフォルダを検索し最新のものを返す。なければ作成。"""
    db = SessionLocal()
    case = db.query(Case).get(case_id)
    db.close()

    if not case or not case.folder_path:
        base_dir = Path("output") / str(case_id)
    else:
        base_dir = Path(case.folder_path)

    if not base_dir.exists():
        base_dir.mkdir(parents=True, exist_ok=True)

    matches = [d for d in base_dir.rglob(f"*{keyword}*") if d.is_dir()]
    if not matches:
        new_path = base_dir / keyword
        new_path.mkdir(parents=True, exist_ok=True)
        return new_path
    
    return max(matches, key=lambda d: d.stat().st_mtime)

def move_and_rename_bank_pdf(case_id: int, src_path: str, bank_name: str, doc_type: str) -> Optional[str]:
    """銀行書類PDFをリネームして案件フォルダの『残高証明書』フォルダへ移動する"""
    db = SessionLocal()
    try:
        if not src_path or not os.path.exists(src_path): return None
        
        # 案件情報の取得（案件番号取得のため）
        case = db.query(Case).get(case_id)
        # 案件番号 (例: G2103) を使用。取得できない場合はIDを使用
        case_identifier = case.case_number if case and case.case_number else str(case_id)

        target_dir = find_case_subfolder_by_keyword(case_id, "残高証明書")
        surname = get_contractor_surname(case_id)
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        
        # ファイル名変更: {案件番号}{契約者姓}様_{種別}_{銀行名}{年月日}.pdf
        new_filename = f"{case_identifier}{surname}様_{doc_type}_{bank_name}{date_str}.pdf"
        dest_path = target_dir / new_filename

        # 重複回避
        if dest_path.exists():
            time_suffix = datetime.datetime.now().strftime("%H%M%S")
            new_filename = f"{case_identifier}{surname}様_{doc_type}_{bank_name}{date_str}_{time_suffix}.pdf"
            dest_path = target_dir / new_filename

        shutil.copy2(src_path, dest_path)
        return str(dest_path)
    except Exception as e:
        print(f"File Move Error: {e}"); return None
    finally:
        db.close()

def update_financial_asset_status_fuzzy(case_id: int, bank_name_part: str, new_status: str = "調査完了") -> int:
    """
    銀行名（部分一致）で資産を検索し、ステータスを更新する。
    戻り値: 更新件数
    """
    db = SessionLocal()
    try:
        # 正規化（全角半角、空白除去）
        search_term = unicodedata.normalize("NFKC", bank_name_part).replace(" ", "").replace("銀行", "").strip()
        
        assets = db.query(FinancialAsset).filter(FinancialAsset.case_id == case_id).all()
        count = 0
        for asset in assets:
            if not asset.bank_ref: continue
            
            db_bank_name = unicodedata.normalize("NFKC", asset.bank_ref.bank_name).replace(" ", "").replace("銀行", "")
            
            # 部分一致判定
            if search_term in db_bank_name or db_bank_name in search_term:
                asset.status = new_status
                count += 1
        
        if count > 0:
            db.commit()
        return count
    except Exception as e:
        db.rollback()
        print(f"Status Update Error: {e}")
        return 0
    finally:
        db.close()


# --- 2. 既存の全ロジック (Utilities) ---

def get_db():
    return SessionLocal()

def get_all_users() -> Dict[int, str]:
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

# --- 3. 案件 (Case) 関連 ---

def get_case_by_id(case_id: int) -> Optional[Case]:
    db = SessionLocal()
    try:
        return (
            db.query(Case)
            .options(
                joinedload(Case.financial_assets).joinedload(FinancialAsset.bank_ref),
                joinedload(Case.financial_assets).joinedload(FinancialAsset.branch_ref),
                joinedload(Case.financial_assets).joinedload(FinancialAsset.account_type_ref),
                joinedload(Case.real_estates),
                joinedload(Case.liabilities),
            )
            .filter(Case.case_id == case_id)
            .first()
        )
    finally:
        db.close()

def get_contracting_party_name(case_id: int) -> str:
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
        if not case or not case.folder_path: return None
        normalized = normalize_folder_path(case.folder_path)
        if case.folder_path != normalized:
            case.folder_path = normalized
            db.commit()
        return normalized
    except Exception:
        db.rollback(); return None
    finally:
        db.close()

# 互換性エイリアス
get_case_folder_path_service = get_case_folder_path

def update_case_folder_path(case_id: int, folder_path: str) -> bool:
    db = SessionLocal()
    try:
        case = db.query(Case).get(case_id)
        if case:
            case.folder_path = normalize_folder_path(folder_path) if folder_path else None
            db.commit(); return True
        return False
    except Exception:
        db.rollback(); return False
    finally:
        db.close()

def update_case_assignment(case_id: int, manager_id: Optional[int], operator_id: Optional[int]) -> bool:
    db = SessionLocal()
    try:
        case = db.query(Case).get(case_id)
        if case:
            case.manager_id = manager_id
            case.operator_id = operator_id
            db.commit(); return True
        return False
    finally:
        db.close()

def update_case_number(case_id: int, new_number: str) -> bool:
    db = SessionLocal()
    try:
        existing = db.query(Case).filter(Case.case_number == new_number, Case.case_id != case_id).first()
        if existing: return False
        case = db.query(Case).get(case_id)
        if case:
            case.case_number = new_number
            db.commit(); return True
        return False
    finally:
        db.close()

def get_next_case_number_service() -> str:
    db = SessionLocal()
    try:
        cases = db.query(Case.case_number).all()
        max_num = 0
        for c in cases:
            if c.case_number and c.case_number.isdigit() and len(c.case_number) == 4:
                try:
                    max_num = max(max_num, int(c.case_number))
                except ValueError: continue
        return f"{(max_num + 1):04d}"
    finally:
        db.close()

def is_case_number_duplicate(case_number: str) -> bool:
    db = SessionLocal()
    try:
        return db.query(Case).filter(Case.case_number == case_number).first() is not None
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
    except Exception:
        db.rollback(); return False
    finally:
        db.close()

def get_case_progress_summary(case_id: int) -> dict:
    return {"status": "進行中", "progress": 50}

# --- 4. 被相続人 (Deceased) 関連 ---

def get_deceased_by_case_id(case_id: int) -> Optional[Deceased]:
    db = SessionLocal()
    try:
        return db.query(Deceased).options(joinedload(Deceased.heirs), joinedload(Deceased.case)).filter(Deceased.case_id == case_id).first()
    finally:
        db.close()

def get_deceased_by_id(deceased_id: int) -> Optional[Deceased]:
    db = SessionLocal()
    try:
        return db.query(Deceased).options(
            joinedload(Deceased.heirs), joinedload(Deceased.case), joinedload(Deceased.last_address)
        ).filter(Deceased.id == deceased_id).first()
    finally:
        db.close()

def get_case_id_by_deceased_id(deceased_id: int) -> Optional[int]:
    db = SessionLocal()
    try:
        d = db.query(Deceased).get(deceased_id)
        return d.case_id if d else None
    finally:
        db.close()

def update_deceased(deceased_id: int, **kwargs) -> bool:
    db = SessionLocal()
    try:
        d = db.query(Deceased).get(deceased_id)
        if not d: return False
        d.name_last = kwargs.get("name_last")
        d.name_first = kwargs.get("name_first")
        d.name_last_kana = kwargs.get("kana_last")
        d.name_first_kana = kwargs.get("kana_first")
        d.hometown = kwargs.get("hometown")
        
        if kwargs.get("dob"): d.date_of_birth = parse_all_flexible_date(kwargs["dob"])
        if kwargs.get("dod"): d.date_of_death = parse_all_flexible_date(kwargs["dod"])
        
        if kwargs.get("last_pref") or kwargs.get("last_street"):
            if d.last_address_id:
                addr = db.query(Address).get(d.last_address_id)
                addr.zip_code = kwargs.get("last_zip_code")
                addr.prefecture = kwargs.get("last_pref")
                addr.city_ward_town = kwargs.get("last_city")
                addr.street_address = kwargs.get("last_street")
                addr.building_name = kwargs.get("last_building")
            else:
                new_addr = Address(
                    zip_code=kwargs.get("last_zip_code"), prefecture=kwargs.get("last_pref"),
                    city_ward_town=kwargs.get("last_city"), street_address=kwargs.get("last_street"),
                    building_name=kwargs.get("last_building")
                )
                db.add(new_addr); db.flush(); d.last_address_id = new_addr.id
        
        _update_contacts(db, "deceased", deceased_id, kwargs.get("phone_contacts"), "PHONE")
        _update_contacts(db, "deceased", deceased_id, kwargs.get("email_contacts"), "EMAIL")
        
        db.commit(); return True
    except Exception as e:
        db.rollback(); raise e
    finally:
        db.close()

# --- 5. 相続人 (Heir) 関連 ---

def get_heir_by_id(heir_id: int) -> Optional[Heir]:
    db = SessionLocal()
    try:
        return db.query(Heir).get(heir_id)
    finally:
        db.close()

def add_heir(deceased_id: int, name: str, rel: str, **kwargs) -> int:
    db = SessionLocal()
    try:
        parts = name.split(" ", 1)
        new_heir = Heir(
            deceased_id=deceased_id, name_last=parts[0], name_first=parts[1] if len(parts) > 1 else "",
            name_last_kana=kwargs.get("kana_last"), name_first_kana=kwargs.get("kana_first"),
            relationship_type=rel, hometown=kwargs.get("hometown"), 
            date_of_birth=parse_all_flexible_date(kwargs["dob"]) if kwargs.get("dob") else None
        )
        db.add(new_heir); db.flush()
        
        if kwargs.get("pref") or kwargs.get("street"):
            new_addr = Address(
                zip_code=kwargs.get("zip_code"), prefecture=kwargs.get("pref"), 
                city_ward_town=kwargs.get("city"), street_address=kwargs.get("street"), 
                building_name=kwargs.get("building")
            )
            db.add(new_addr); db.flush()
            db.add(H_AddressHistory(heir_id=new_heir.id, address_id=new_addr.id, is_current_address=True))
        
        _add_contacts_to_heir(db, new_heir.id, kwargs.get("phone_contacts"), "PHONE")
        _add_contacts_to_heir(db, new_heir.id, kwargs.get("email_contacts"), "EMAIL")
        
        db.commit(); return new_heir.id
    except Exception as e:
        db.rollback(); raise e
    finally:
        db.close()

def update_heir(heir_id: int, name: str, rel: str, **kwargs) -> bool:
    db = SessionLocal()
    try:
        heir = db.query(Heir).get(heir_id)
        if not heir: return False
        
        parts = name.split(" ", 1)
        heir.name_last = parts[0]
        heir.name_first = parts[1] if len(parts) > 1 else ""
        heir.relationship_type = rel
        heir.name_last_kana = kwargs.get("kana_last")
        heir.name_first_kana = kwargs.get("kana_first")
        heir.hometown = kwargs.get("hometown")
        if kwargs.get("dob"): heir.date_of_birth = parse_all_flexible_date(kwargs["dob"])

        if kwargs.get("pref") or kwargs.get("street"):
            curr = db.query(H_AddressHistory).filter(H_AddressHistory.heir_id==heir_id, H_AddressHistory.is_current_address==True).first()
            if curr:
                addr = db.query(Address).get(curr.address_id)
                addr.zip_code = kwargs.get("zip_code")
                addr.prefecture = kwargs.get("pref")
                addr.city_ward_town = kwargs.get("city")
                addr.street_address = kwargs.get("street")
                addr.building_name = kwargs.get("building")
            else:
                new_addr = Address(
                    zip_code=kwargs.get("zip_code"), prefecture=kwargs.get("pref"),
                    city_ward_town=kwargs.get("city"), street_address=kwargs.get("street"),
                    building_name=kwargs.get("building")
                )
                db.add(new_addr); db.flush()
                db.add(H_AddressHistory(heir_id=heir_id, address_id=new_addr.id, is_current_address=True))
        
        _update_contacts(db, "heir", heir_id, kwargs.get("phone_contacts"), "PHONE")
        _update_contacts(db, "heir", heir_id, kwargs.get("email_contacts"), "EMAIL")
        
        db.commit(); return True
    except Exception as e:
        db.rollback(); raise e
    finally:
        db.close()

def delete_heir(heir_id: int) -> bool:
    db = SessionLocal()
    try:
        heir = db.query(Heir).get(heir_id)
        if heir:
            db.delete(heir); db.commit(); return True
        return False
    finally:
        db.close()

def add_new_case_for_client_registration(case_number, name, **kwargs) -> int:
    db = SessionLocal()
    try:
        new_case = Case(
            case_number=case_number, client_name=name, client_name_kana=f"{kwargs.get('kana_last')} {kwargs.get('kana_first')}".strip(),
            manager_id=kwargs.get("manager_id"), operator_id=kwargs.get("operator_id"), current_status_id=1, contract_date=datetime.date.today()
        )
        db.add(new_case); db.flush()
        
        deceased = Deceased(case_id=new_case.case_id, name_last="", name_first="", relationship_type="本人")
        db.add(deceased); db.flush()
        
        parts = name.split(" ", 1)
        heir = Heir(
            deceased_id=deceased.id, name_last=parts[0], name_first=parts[1] if len(parts) > 1 else "",
            name_last_kana=kwargs.get("kana_last"), name_first_kana=kwargs.get("kana_first"),
            relationship_type=kwargs.get("rel"), hometown=kwargs.get("hometown"), is_contracting_party=True
        )
        db.add(heir); db.flush()
        
        if kwargs.get("pref") or kwargs.get("street"):
            addr = Address(
                zip_code=kwargs.get("zip_code"), prefecture=kwargs.get("pref"),
                city_ward_town=kwargs.get("city"), street_address=kwargs.get("street"),
                building_name=kwargs.get("building")
            )
            db.add(addr); db.flush()
            db.add(H_AddressHistory(heir_id=heir.id, address_id=addr.id, is_current_address=True))
        
        _add_contacts_to_heir(db, heir.id, kwargs.get("phone_contacts"), "PHONE")
        _add_contacts_to_heir(db, heir.id, kwargs.get("email_contacts"), "EMAIL")
        
        db.commit(); return deceased.id
    except Exception as e:
        db.rollback(); print(f"Reg Error: {e}"); return -1
    finally:
        db.close()

# --- 6. 住所・連絡先ヘルパー ---

def get_address_by_id(address_id: int) -> Optional[Address]:
    db = SessionLocal()
    try: return db.query(Address).get(address_id)
    finally: db.close()

def get_address_info(target_type: str, target_id: int) -> dict:
    db = SessionLocal()
    try:
        addr = None
        if target_type == "heir":
            link = db.query(H_AddressHistory).filter(H_AddressHistory.heir_id==target_id, H_AddressHistory.is_current_address==True).first()
            if link: addr = db.query(Address).get(link.address_id)
        elif target_type == "deceased":
            d = db.query(Deceased).get(target_id)
            if d and d.last_address_id: addr = db.query(Address).get(d.last_address_id)
        
        if addr:
            return {"zip_code": addr.zip_code, "prefecture": addr.prefecture, "city_ward_town": addr.city_ward_town, "street_address": addr.street_address, "building_name": addr.building_name}
        return {}
    finally: db.close()

def get_contact_info(target_type: str, target_id: int) -> List[dict]:
    db = SessionLocal()
    try:
        contacts = []
        if target_type == "heir":
            links = db.query(H_ContactLink).filter(H_ContactLink.heir_id==target_id).all()
            for link in links:
                c = db.query(Contact).get(link.contact_id)
                if c: contacts.append({"id": c.id, "type": c.type, "value": c.value, "sub_type": c.sub_type})
        elif target_type == "deceased":
            links = db.query(D_ContactLink).filter(D_ContactLink.deceased_id==target_id).all()
            for link in links:
                c = db.query(Contact).get(link.contact_id)
                if c: contacts.append({"id": c.id, "type": c.type, "value": c.value, "sub_type": c.sub_type})
        return contacts
    finally: db.close()

def get_deceased_address_history(deceased_id: int) -> List[dict]:
    db = SessionLocal()
    try:
        links = db.query(D_AddressHistory).filter(D_AddressHistory.deceased_id==deceased_id).all()
        history = []
        for link in links:
            if not link.is_last_address:
                addr = db.query(Address).get(link.address_id)
                if addr:
                    history.append({"address_id": addr.id, "zip_code": addr.zip_code, "prefecture": addr.prefecture, "city_ward_town": addr.city_ward_town, "street_address": addr.street_address, "building_name": addr.building_name})
        return history
    finally: db.close()

def _add_contacts_to_heir(db, heir_id, contact_list, type_str):
    if not contact_list: return
    for c in contact_list:
        val = c.get("value")
        if val:
            new_c = Contact(value=val, type=type_str, sub_type=c.get("sub_type", "Primary"))
            db.add(new_c); db.flush()
            db.add(H_ContactLink(heir_id=heir_id, contact_id=new_c.id))

def _update_contacts(db, target_type, target_id, contact_list, type_str):
    if target_type == "heir":
        links = db.query(H_ContactLink).join(Contact).filter(H_ContactLink.heir_id==target_id, Contact.type==type_str).all()
        for l in links: db.delete(l)
        _add_contacts_to_heir(db, target_id, contact_list, type_str)
    elif target_type == "deceased":
        links = db.query(D_ContactLink).join(Contact).filter(D_ContactLink.deceased_id==target_id, Contact.type==type_str).all()
        for l in links: db.delete(l)
        if contact_list:
            for c in contact_list:
                val = c.get("value")
                if val:
                    new_c = Contact(value=val, type=type_str, sub_type=c.get("sub_type", "Primary"))
                    db.add(new_c); db.flush()
                    db.add(D_ContactLink(deceased_id=target_id, contact_id=new_c.id))

def search_address_by_zip_api(zip_code: str) -> Optional[dict]:
    if not zip_code: return None
    try:
        res = requests.get(f"https://zipcloud.ibsnet.co.jp/api/search?zipcode={zip_code.replace('-', '')}")
        data = res.json()
        if data and data.get("results"):
            r = data["results"][0]
            return {"prefecture": r["address1"], "city_ward_town": r["address2"], "street_address": r["address3"]}
        return {}
    except: return None

def search_zip_by_address_api(address: str) -> Optional[str]:
    if not address: return None
    try:
        res = requests.get("http://geoapi.heartrails.com/api/json", params={"method": "suggest", "matching": "like", "keyword": address})
        data = res.json()
        if data and data.get("response") and data["response"].get("location"):
            p = data["response"]["location"][0].get("postal")
            return f"{p[:3]}-{p[3:]}" if p else None
        return None
    except: return None

def get_kintone_integration_data(case_id: int) -> dict:
    """Kintone連携用のデータを取得する（契約者詳細情報を含む）"""
    # 1. 案件情報の取得
    case = get_case_by_id(case_id)
    if not case:
        return {}

    # 2. 被相続人情報の取得
    deceased = get_deceased_by_case_id(case_id)
    
    d_name = ""
    d_kana = ""
    inheritance_date = ""

    # 被相続人データの抽出
    if deceased:
        d_name = f"{deceased.name_last}　{deceased.name_first}"
        d_kana = f"{deceased.name_last_kana or ''}　{deceased.name_first_kana or ''}".strip()
        if deceased.date_of_death:
            inheritance_date = deceased.date_of_death.strftime("%Y-%m-%d")

    # 3. 契約者（依頼者）情報の特定
    client_name = case.client_name
    client_kana = case.client_name_kana or ""
    client_zip = ""
    client_addr = ""
    client_tel = ""
    client_mail = ""

    # 相続人リストから契約者を探索
    contractor = None
    if deceased and deceased.heirs:
        # is_contracting_party が True の相続人を探す
        contractor = next((h for h in deceased.heirs if h.is_contracting_party), None)
    
    if contractor:
        # 名前・フリガナの更新（Heirテーブルの方が正確な場合があるため）
        client_name = f"{contractor.name_last}　{contractor.name_first}"
        client_kana = f"{contractor.name_last_kana or ''}　{contractor.name_first_kana or ''}".strip()

        # 住所情報の取得
        addr_info = get_address_info("heir", contractor.id)
        if addr_info:
            client_zip = addr_info.get("zip_code", "")
            # 住所連結: 都道府県 + 市区町村 + 番地 + (建物名)
            client_addr = f"{addr_info.get('prefecture', '')}{addr_info.get('city_ward_town', '')}{addr_info.get('street_address', '')}"
            if addr_info.get("building_name"):
                client_addr += f"　{addr_info.get('building_name')}"
        
        # 連絡先情報の取得
        contacts = get_contact_info("heir", contractor.id)
        # 電話番号 (Primary優先)
        phones = [c for c in contacts if c["type"] == "PHONE"]
        if phones:
            # Primaryがあればそれを、なければ最初のものを採用
            primary_phone = next((p for p in phones if p.get("sub_type") == "Primary"), phones[0])
            client_tel = primary_phone.get("value", "")

        # メールアドレス (Primary優先)
        emails = [c for c in contacts if c["type"] == "EMAIL"]
        if emails:
            primary_email = next((e for e in emails if e.get("sub_type") == "Primary"), emails[0])
            client_mail = primary_email.get("value", "")

    return {
        "case_number": case.case_number,
        "client_name": client_name,
        "deceased_name": d_name,
        "client_zip": client_zip,
        "client_addr": client_addr,
        "client_kana": client_kana,
        "deceased_kana": d_kana,
        "client_tel": client_tel,
        "client_mail": client_mail,
        "inheritance_date": inheritance_date
    }

# --- 7. 金融資産・書類作成関連 ---

def get_financial_asset_by_case(case_id: int):
    """案件に紐づく銀行資産リストの取得"""
    db = SessionLocal()
    try:
        assets = db.query(FinancialAsset).filter(FinancialAsset.case_id == case_id).all()
        return [
            {
                "id": a.id, "bank_id": a.bank_id, 
                "bank_name": a.bank_ref.bank_name if a.bank_ref else "不明",
                "bank_code": a.bank_ref.bank_code if a.bank_ref else "",
                "branch_name": a.branch_ref.branch_name if a.branch_ref else "",
                "account_number": a.account_number, "balance": a.balance, "status": a.status
            } for a in assets
        ]
    finally:
        db.close()

def get_bank_cert_document_data(case_id: int, bank_code: str) -> dict:
    db = SessionLocal()
    try:
        case = db.query(Case).get(case_id)
        if not case: return {}
        deceased = db.query(Deceased).filter(Deceased.case_id == case_id).first()
        client = db.query(Heir).filter(Heir.deceased_id==deceased.id, Heir.is_contracting_party==True).first() if deceased else None
        assets = db.query(FinancialAsset).join(BankMaster).filter(FinancialAsset.case_id==case_id, BankMaster.bank_code==bank_code).all()
        
        res = {
            "case_number": case.case_number,
            "deceased": {"last_name": deceased.name_last if deceased else "", "first_name": deceased.name_first if deceased else "", "date_of_death": deceased.date_of_death if deceased else None} if deceased else {},
            "contracting_party": {"last_name": client.name_last if client else "", "first_name": client.name_first if client else ""} if client else {},
            "bank_assets": []
        }
        for a in assets:
            res["bank_assets"].append({
                "id": a.id, "bank_name": a.bank_ref.bank_name,
                "branch_name": a.branch_ref.branch_name if a.branch_ref else "",
                "branch_code": a.branch_ref.branch_code if a.branch_ref else "",
                "account_type": a.account_type_ref.type_name if a.account_type_ref else "",
                "account_number": a.account_number, "balance": a.balance
            })
        return res
    finally: db.close()

def get_financial_assets_by_bank_code(case_id: int, bank_code: str) -> List[dict]:
    data = get_bank_cert_document_data(case_id, bank_code)
    return data.get("bank_assets", [])

def get_financial_asset_automation_data(case_id: int, bank_code: str) -> dict:
    db = SessionLocal()
    try:
        case = db.query(Case).get(case_id)
        deceased = db.query(Deceased).filter(Deceased.case_id==case_id).first()
        if not case or not deceased: return {}
        client = db.query(Heir).filter(Heir.deceased_id==deceased.id, Heir.is_contracting_party==True).first()
        asset = db.query(FinancialAsset).join(BankMaster).outerjoin(BranchMaster).filter(FinancialAsset.case_id==case_id, BankMaster.bank_code==bank_code).first()
        
        client_tel = ""
        client_mail = ""
        if client:
            contacts = get_contact_info("heir", client.id)
            client_tel = next((c["value"] for c in contacts if c["type"]=="PHONE"), "")
            client_mail = next((c["value"] for c in contacts if c["type"]=="EMAIL"), "")
            
        return {
            "case_number": case.case_number, "deceased_name": f"{deceased.name_last} {deceased.name_first}",
            "contractor_name": f"{client.name_last} {client.name_first}" if client else "",
            "client_phone": client_tel, "client_email": client_mail,
            "bank_branch_code": asset.branch_ref.branch_code if asset and asset.branch_ref else "",
            "bank_account_number": asset.account_number if asset else ""
        }
    finally: db.close()

def get_bank_masters(db=None) -> List[BankMaster]:
    local = False
    if db is None: db = SessionLocal(); local = True
    try: return db.query(BankMaster).order_by(BankMaster.bank_code).all()
    finally:
        if local: db.close()

def get_bank_master_by_id(bank_id: int) -> Optional[BankMaster]:
    db = SessionLocal()
    try: return db.query(BankMaster).get(bank_id)
    finally: db.close()

def get_branch_masters_by_bank_id(bank_id: int) -> List[BranchMaster]:
    db = SessionLocal()
    try: return db.query(BranchMaster).filter(BranchMaster.bank_id==bank_id).all()
    finally: db.close()

def get_account_type_masters(db=None) -> List[AccountTypeMaster]:
    local = False
    if db is None: db = SessionLocal(); local = True
    try: return db.query(AccountTypeMaster).all()
    finally:
        if local: db.close()

def add_or_update_bank_master(bank_id: Optional[int], name: str, code: str) -> Optional[BankMaster]:
    db = SessionLocal()
    try:
        if bank_id:
            bank = db.query(BankMaster).get(bank_id)
            if bank: bank.bank_name = name; bank.bank_code = code
        else:
            if db.query(BankMaster).filter(BankMaster.bank_code==code).first(): return None
            bank = BankMaster(bank_name=name, bank_code=code)
            db.add(bank)
        db.commit(); db.refresh(bank); return bank
    except: db.rollback(); return None
    finally: db.close()

def add_branch_master(bank_id: int, name: str, code: str) -> Optional[BranchMaster]:
    db = SessionLocal()
    try:
        if db.query(BranchMaster).filter(BranchMaster.bank_id==bank_id, BranchMaster.branch_code==code).first(): raise ValueError("Duplicate")
        branch = BranchMaster(bank_id=bank_id, branch_name=name, branch_code=code)
        db.add(branch); db.commit(); db.refresh(branch); return branch
    except Exception as e: db.rollback(); raise e
    finally: db.close()

def update_branch_code(branch_id: int, new_code: str) -> bool:
    db = SessionLocal()
    try:
        branch = db.query(BranchMaster).get(branch_id)
        if branch: branch.branch_code = new_code; db.commit(); return True
        return False
    except: db.rollback(); return False
    finally: db.close()

def update_branch_name(branch_id: int, new_name: str) -> bool:
    db = SessionLocal()
    try:
        branch = db.query(BranchMaster).get(branch_id)
        if branch: branch.branch_name = new_name; db.commit(); return True
        return False
    except: db.rollback(); return False
    finally: db.close()

def add_account_type_master(db=None, type_name: str = "") -> Optional[AccountTypeMaster]:
    local = False
    if db is None: db = SessionLocal(); local = True
    try:
        if db.query(AccountTypeMaster).filter(AccountTypeMaster.type_name==type_name).first(): return None
        new_type = AccountTypeMaster(type_name=type_name)
        db.add(new_type); db.commit(); db.refresh(new_type); return new_type
    except: db.rollback(); return None
    finally:
        if local: db.close()

def get_financial_asset_by_case_and_type(case_id: int, asset_type: str) -> List[dict]:
    db = SessionLocal()
    try:
        assets = db.query(FinancialAsset).filter(FinancialAsset.case_id==case_id, FinancialAsset.asset_type==asset_type).all()
        return [{"id": a.id, "bank_id": a.bank_id, "bank_name": a.bank_ref.bank_name if a.bank_ref else "不明",
                 "branch_name": a.branch_ref.branch_name if a.branch_ref else "", "account_number": a.account_number,
                 "bank_code": a.bank_ref.bank_code if a.bank_ref else "", "balance": a.balance, "status": a.status} for a in assets]
    finally: db.close()

def add_financial_asset_with_type(case_id: int, asset_type: str, bank_id: int, branch_id: Optional[int], account_type_id: Optional[int], account_number: str, balance: float, status: str) -> bool:
    db = SessionLocal()
    try:
        asset = FinancialAsset(case_id=case_id, asset_type=asset_type, bank_id=bank_id, branch_id=branch_id, account_type_id=account_type_id, account_number=account_number, balance=balance, status=status)
        db.add(asset); db.commit(); return True
    except: db.rollback(); return False
    finally: db.close()

def add_financial_asset(case_id: int, bank_id: int, branch_id: Optional[int], account_type_id: Optional[int], account_number: str, balance: float, status: str) -> bool:
    return add_financial_asset_with_type(case_id, "BANK", bank_id, branch_id, account_type_id, account_number, balance, status)

def update_financial_asset(asset_id: int, bank_id: int, branch_id: Optional[int], account_type_id: Optional[int], account_number: str, balance: float, status: str) -> bool:
    db = SessionLocal()
    try:
        asset = db.query(FinancialAsset).get(asset_id)
        if asset:
            asset.bank_id = bank_id; asset.branch_id = branch_id; asset.account_type_id = account_type_id
            asset.account_number = account_number; asset.balance = balance; asset.status = status
            db.commit(); return True
        return False
    except: db.rollback(); return False
    finally: db.close()

def delete_financial_asset(asset_id: int) -> bool:
    db = SessionLocal()
    try:
        asset = db.query(FinancialAsset).get(asset_id)
        if asset: db.delete(asset); db.commit(); return True
        return False
    finally: db.close()

# --- 8. タスク管理 ---

def get_all_tasks_for_case(case_id: int) -> List[dict]:
    db = SessionLocal()
    try:
        tasks = db.query(Task, User.name).outerjoin(User, Task.assigned_user_id==User.id).filter(Task.case_id==case_id).order_by(Task.due_date).all()
        return [{"task_id": t.task_id, "description": t.description, "due_date": t.due_date.strftime("%Y-%m-%d") if t.due_date else None, "assigned_user_name": u if u else "未割当", "is_completed": t.is_completed} for t, u in tasks]
    finally: db.close()

def save_task(case_id: int, task_id: Optional[int], description: str, due_date: str, assigned_user_id: Optional[int], is_completed: bool = False) -> bool:
    db = SessionLocal()
    try:
        dt_due = datetime.datetime.combine(parse_all_flexible_date(due_date), datetime.time.min) if due_date else None
        if task_id:
            task = db.query(Task).get(task_id)
            if task: task.description=description; task.due_date=dt_due; task.assigned_user_id=assigned_user_id; task.is_completed=is_completed
        else:
            db.add(Task(case_id=case_id, description=description, due_date=dt_due, assigned_user_id=assigned_user_id, is_completed=is_completed))
        db.commit(); return True
    except: db.rollback(); return False
    finally: db.close()

def delete_task(task_id: int) -> bool:
    db = SessionLocal()
    try:
        task = db.query(Task).get(task_id)
        if task: db.delete(task); db.commit(); return True
        return False
    finally: db.close()

def get_incomplete_tasks(user_id=None):
    db = SessionLocal()
    try:
        query = db.query(Task, Case.case_number, User.name, Case.client_name).join(Case, Task.case_id==Case.case_id).join(User, Task.assigned_user_id==User.id).filter(Task.is_completed==False)
        if user_id: query = query.filter(Task.assigned_user_id==user_id)
        tasks = query.order_by(Task.due_date).limit(10).all()
        return [{"task_id": t.task_id, "case_id": t.case_id, "case_number": cn, "description": t.description, "due_date": t.due_date.strftime("%Y/%m/%d") if t.due_date else "N/A", "assigned_user": u, "client_name": cl} for t, cn, u, cl in tasks]
    finally: db.close()

# --- 9. 案件リストビュー ---

def get_case_list(search_term="", status_id=None, user_id=None):
    db = SessionLocal()
    try:
        HeirContactLink = aliased(H_ContactLink)
        DeceasedContactLink = aliased(D_ContactLink)
        HeirContact = aliased(Contact)
        DeceasedContact = aliased(Contact)

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
            .join(Deceased.heirs, isouter=True)
            .join(Case.status_ref, isouter=True)
            .join(Task, Case.case_id == Task.case_id, isouter=True)
            .outerjoin(DeceasedContactLink, Deceased.id == DeceasedContactLink.deceased_id)
            .outerjoin(DeceasedContact, DeceasedContactLink.contact_id == DeceasedContact.id)
            .outerjoin(HeirContactLink, Heir.id == HeirContactLink.heir_id)
            .outerjoin(HeirContact, HeirContactLink.contact_id == HeirContact.id)
            .order_by(Case.contract_date.desc())
        )

        if search_term:
            # 💡 修正: フルネーム検索、スペース無視検索の対応
            t = f"%{search_term}%"
            # スペースを除去した検索語（「山田太郎」で「山田 太郎」をヒットさせるため）
            t_nospace = f"%{search_term.replace(' ', '').replace('　', '')}%"

            query = query.filter(
                or_(
                    Case.case_number.ilike(t),
                    Case.client_name.ilike(t),
                    Case.client_name_kana.ilike(t),
                    
                    # 個別カラム検索
                    Deceased.name_last.ilike(t),
                    Deceased.name_first.ilike(t),
                    Deceased.name_last_kana.ilike(t),
                    Heir.name_last.ilike(t),
                    Heir.name_first.ilike(t),
                    Heir.name_last_kana.ilike(t),

                    # フルネーム検索 (スペースあり)
                    (Deceased.name_last + " " + Deceased.name_first).ilike(t),
                    (Deceased.name_last_kana + " " + Deceased.name_first_kana).ilike(t),
                    (Heir.name_last + " " + Heir.name_first).ilike(t),
                    (Heir.name_last_kana + " " + Heir.name_first_kana).ilike(t),

                    # フルネーム検索 (スペースなし)
                    (Deceased.name_last + Deceased.name_first).ilike(t_nospace),
                    (Deceased.name_last_kana + Deceased.name_first_kana).ilike(t_nospace),
                    (Heir.name_last + Heir.name_first).ilike(t_nospace),
                    (Heir.name_last_kana + Heir.name_first_kana).ilike(t_nospace),

                    # 連絡先
                    DeceasedContact.value.ilike(t),
                    HeirContact.value.ilike(t),
                )
            )
        
        if status_id: query = query.filter(Case.current_status_id==status_id)
        if user_id: query = query.filter(or_(Case.manager_id==user_id, Case.operator_id==user_id))
        
        cases_data = query.limit(100).all()
        case_list = []
        processed = set()
        for c, dl, df, stat, desc, lup in cases_data:
            if c.case_id in processed: continue
            processed.add(c.case_id)
            role = ""
            if user_id:
                if c.manager_id == user_id: role = "担当1"
                elif c.operator_id == user_id: role = "担当2"
            
            case_list.append({
                "case_id": c.case_id, "case_number": c.case_number, "sol_case_number": getattr(c, "sol_case_number", "---"),
                "client_name": c.client_name, "deceased_name": f"{dl} {df}" if dl else "N/A",
                "contract_date": c.contract_date.strftime("%Y/%m/%d") if c.contract_date else "N/A",
                "status": stat if stat else "未設定", "role_label": role, "description": desc if desc else "",
                "last_updated_at": lup.strftime("%Y/%m/%d") if lup else "N/A"
            })
        return case_list
    finally: db.close()

def get_my_cases(user_id: int, limit: int = 10):
    db = SessionLocal()
    try:
        cases = db.query(Case).options(joinedload(Case.deceased_ref), joinedload(Case.status_ref)).filter(or_(Case.manager_id==user_id, Case.operator_id==user_id)).order_by(Case.current_status_id, Case.contract_date.desc()).limit(limit).all()
        return [{"case_id": c.case_id, "case_number": c.case_number, "sol_case_number": getattr(c, "sol_case_number", "---"), "client_name": c.client_name, "deceased_name": f"{c.deceased_ref.name_last} {c.deceased_ref.name_first}" if c.deceased_ref else "N/A", "status": c.status_ref.name if c.status_ref else "N/A"} for c in cases]
    finally: db.close()

def get_user_capacity_data():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        data = []
        for u in users:
            tc = db.query(func.count(Task.task_id)).filter(Task.assigned_user_id==u.id, Task.is_completed==False).scalar()
            cc = db.query(func.count(Case.case_id)).filter(or_(Case.manager_id==u.id, Case.operator_id==u.id)).scalar()
            data.append({"user_id": u.id, "name": u.name, "role": u.role, "total_incomplete_tasks": tc, "total_cases_handled": cc})
        return sorted(data, key=lambda x: x["total_incomplete_tasks"], reverse=True)
    finally: db.close()