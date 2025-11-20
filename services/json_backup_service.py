# /services/json_backup_service.py

import json
import re
import datetime
from sqlalchemy.orm import Session, joinedload
from services.db_setup import (
    Engine, Case, Deceased, Heir, FinancialAsset, 
    Address, Contact, H_ContactLink, H_AddressHistory, D_AddressHistory,
    User, CaseStatus, AccountTypeMaster, BankMaster, BranchMaster
)

# --- 日付型などをJSONシリアライズ可能にするヘルパー ---
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat() # YYYY-MM-DD文字列表記
        return super().default(obj)

# 💡【追加】柔軟な日付解析関数
def _parse_flexible_date(date_str: str | None) -> datetime.date | None:
    """
    日付文字列をパースする。
    - 2025-01-01 (標準ISO)
    - 1941-3-1 (ゼロ埋めなし)
    - 2025/01/01 (スラッシュ区切り)
    これらに対応して datetime.date オブジェクトを返す。
    """
    if not date_str:
        return None
    
    # 1. まず標準の fromisoformat を試す (高速)
    try:
        return datetime.date.fromisoformat(date_str)
    except ValueError:
        pass

    # 2. ゼロ埋めなしハイフン区切り (1941-3-1) を試す
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        pass
    
    # 3. スラッシュ区切り (2025/1/1) を試す
    try:
        return datetime.datetime.strptime(date_str, "%Y/%m/%d").date()
    except ValueError:
        # どうしても読めない場合はログを出してNoneを返す（エラー停止させない）
        print(f"Warning: Invalid date format skipped: {date_str}")
        return None


def _get_address_dict(session, address_id):
    """Address IDから辞書を作成"""
    if not address_id: return None
    addr = session.query(Address).get(address_id)
    if not addr: return None
    return {
        "zip_code": addr.zip_code,
        "prefecture": addr.prefecture,
        "city_ward_town": addr.city_ward_town,
        "street_address": addr.street_address,
        "building_name": addr.building_name
    }

def _create_address_record(session, addr_data):
    """辞書からAddressレコードを作成してIDを返す"""
    if not addr_data: return None
    new_addr = Address(
        zip_code=addr_data.get("zip_code"),
        prefecture=addr_data.get("prefecture"),
        city_ward_town=addr_data.get("city_ward_town"),
        street_address=addr_data.get("street_address"),
        building_name=addr_data.get("building_name")
    )
    session.add(new_addr)
    session.flush()
    return new_addr.id

# ==========================================
# エクスポート (出力)
# ==========================================
def export_database_to_json(file_path: str) -> bool:
    session = Session(bind=Engine)
    try:
        # 全案件を、関連データ込みで取得
        cases = session.query(Case).options(
            joinedload(Case.deceased_ref).joinedload(Deceased.heirs),
            joinedload(Case.financial_assets),
        ).all()

        export_data = []

        for case in cases:
            # 1. 案件基本情報
            case_dict = {
                "case_number": case.case_number,
                "client_name": case.client_name,
                "client_name_kana": case.client_name_kana,
                "contract_date": case.contract_date,
                "status_id": case.current_status_id,
                "manager_id": case.manager_id,
                "operator_id": case.operator_id,
                "folder_path": case.folder_path,
                "tax_deadline": case.tax_deadline,
                "fee_contract_amount": case.fee_contract_amount,
                "deposit_required_amount": case.deposit_required_amount,
                "deposit_paid_amount": case.deposit_paid_amount,
                "is_paid_in_full": case.is_paid_in_full,
                "deceased": None,
                "heirs": [],
                "financial_assets": []
            }

            # 2. 被相続人 (Deceased)
            d = case.deceased_ref
            if d:
                d_dict = {
                    "name_last": d.name_last,
                    "name_first": d.name_first,
                    "name_last_kana": d.name_last_kana,
                    "name_first_kana": d.name_first_kana,
                    "date_of_birth": d.date_of_birth,
                    "date_of_death": d.date_of_death,
                    "hometown": d.hometown,
                    "last_address": _get_address_dict(session, d.last_address_id)
                }
                case_dict["deceased"] = d_dict

                # 3. 相続人リスト (Heirs)
                for h in d.heirs:
                    h_dict = {
                        "name_last": h.name_last,
                        "name_first": h.name_first,
                        "name_last_kana": h.name_last_kana,
                        "name_first_kana": h.name_first_kana,
                        "relationship_type": h.relationship_type,
                        "date_of_birth": h.date_of_birth,
                        "hometown": h.hometown,
                        "is_contracting_party": h.is_contracting_party,
                        "current_address": None,
                        "contacts": []
                    }
                    
                    h_addr_link = session.query(H_AddressHistory).filter(
                        H_AddressHistory.heir_id == h.id, 
                        H_AddressHistory.is_current_address == True
                    ).first()
                    if h_addr_link:
                        h_dict["current_address"] = _get_address_dict(session, h_addr_link.address_id)

                    links = session.query(H_ContactLink).filter(H_ContactLink.heir_id == h.id).all()
                    for link in links:
                        contact = session.query(Contact).get(link.contact_id)
                        if contact:
                            h_dict["contacts"].append({
                                "type": contact.type,
                                "value": contact.value,
                                "sub_type": contact.sub_type
                            })
                    
                    case_dict["heirs"].append(h_dict)

            # 4. 金融資産リスト (Financial Assets)
            for asset in case.financial_assets:
                asset_dict = {
                    "bank_id": asset.bank_id,
                    "branch_id": asset.branch_id,
                    "account_type_id": asset.account_type_id,
                    "account_number": asset.account_number,
                    "balance": asset.balance,
                    "status": asset.status
                }
                case_dict["financial_assets"].append(asset_dict)

            export_data.append(case_dict)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, cls=DateTimeEncoder, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"JSON Export Error: {e}")
        return False
    finally:
        session.close()


# ==========================================
# インポート (取込・復元)
# ==========================================
def import_database_from_json(file_path: str) -> tuple[bool, str]:
    session = Session(bind=Engine)
    try:
        # 💡 変更: ファイルをテキストとして読み込み、バックスラッシュを救済してからJSONパースする
        with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()
        
        # 【自動修正1】JSONエラー回避のためのバックスラッシュ補正
        # "C:\Users" のように \ が1つだけ書かれている箇所を \\ に置換します。
        # 正規表現: 「直前に \ がなく、直後にエスケープ文字(u, ", \, /, b, f, n, r, t)が来ない \」 をターゲット
        # ※ \t (temp) や \n (new) などで始まるフォルダ名は救えませんが、それ以外はこれで直ります。
        file_content = re.sub(r'(?<!\\)\\(?![u"\\/bfnrt])', r'\\\\', file_content)

        data_list = json.loads(file_content) # load ではなく loads (文字列から読込)

        count_created = 0
        count_updated = 0

        for case_data in data_list:
            case_num = case_data.get("case_number")
            if not case_num: continue

            existing_case = session.query(Case).filter(Case.case_number == case_num).first()
            
            if existing_case:
                session.delete(existing_case)
                session.flush()
                count_updated += 1
            else:
                count_created += 1

            # 日付変換
            contract_d = _parse_flexible_date(case_data.get("contract_date"))
            
            tax_d_str = case_data.get("tax_deadline")
            tax_d = None
            if tax_d_str:
                if "T" in tax_d_str or " " in tax_d_str:
                    try:
                        tax_d = datetime.datetime.fromisoformat(tax_d_str)
                    except:
                         tax_d = _parse_flexible_date(tax_d_str)
                else:
                    tax_d = _parse_flexible_date(tax_d_str)

            # 💡 【自動修正2】パス区切り文字の正規化 ( / -> \ )
            raw_folder_path = case_data.get("folder_path")
            fixed_folder_path = None
            
            if raw_folder_path:
                # 1. スラッシュをバックスラッシュに統一
                temp_path = raw_folder_path.replace("/", "\\")
                
                # 2. 先頭が "\\" (2つ) で始まっている場合、"\\\\" (4つ) に増やす
                # ※ すでに4つある場合は何もしない
                if temp_path.startswith("\\\\") and not temp_path.startswith("\\\\\\\\"):
                    fixed_folder_path = "\\\\" + temp_path
                else:
                    fixed_folder_path = temp_path

            new_case = Case(
                case_number=case_num,
                client_name=case_data.get("client_name"),
                client_name_kana=case_data.get("client_name_kana"),
                contract_date=contract_d,
                tax_deadline=tax_d,
                current_status_id=case_data.get("status_id"),
                manager_id=case_data.get("manager_id"),
                operator_id=case_data.get("operator_id"),
                folder_path=fixed_folder_path, 
                fee_contract_amount=case_data.get("fee_contract_amount"),
                deposit_required_amount=case_data.get("deposit_required_amount"),
                deposit_paid_amount=case_data.get("deposit_paid_amount"),
                is_paid_in_full=case_data.get("is_paid_in_full"),
            )
            session.add(new_case)
            session.flush()

            # 3. 被相続人 (Deceased)
            d_data = case_data.get("deceased")
            if d_data:
                new_deceased = Deceased(
                    case_id=new_case.case_id,
                    name_last=d_data.get("name_last"),
                    name_first=d_data.get("name_first"),
                    name_last_kana=d_data.get("name_last_kana"),
                    name_first_kana=d_data.get("name_first_kana"),
                    hometown=d_data.get("hometown"),
                    
                    # 💡【変更】日付変換を適用
                    date_of_birth=_parse_flexible_date(d_data.get("date_of_birth")),
                    date_of_death=_parse_flexible_date(d_data.get("date_of_death")),
                )
                addr_id = _create_address_record(session, d_data.get("last_address"))
                if addr_id:
                    new_deceased.last_address_id = addr_id
                
                session.add(new_deceased)
                session.flush()

                # 4. 相続人 (Heirs)
                heirs_list = case_data.get("heirs", [])
                for h_data in heirs_list:
                    new_heir = Heir(
                        deceased_id=new_deceased.id,
                        name_last=h_data.get("name_last"),
                        name_first=h_data.get("name_first"),
                        name_last_kana=h_data.get("name_last_kana"),
                        name_first_kana=h_data.get("name_first_kana"),
                        relationship_type=h_data.get("relationship_type"),
                        hometown=h_data.get("hometown"),
                        is_contracting_party=h_data.get("is_contracting_party"),
                        
                        # 💡【変更】日付変換を適用
                        date_of_birth=_parse_flexible_date(h_data.get("date_of_birth")),
                    )
                    session.add(new_heir)
                    session.flush()

                    h_addr_id = _create_address_record(session, h_data.get("current_address"))
                    if h_addr_id:
                        session.add(H_AddressHistory(heir_id=new_heir.id, address_id=h_addr_id, is_current_address=True))
                    
                    for c_data in h_data.get("contacts", []):
                        new_contact = Contact(
                            type=c_data.get("type"), 
                            value=c_data.get("value"), 
                            sub_type=c_data.get("sub_type")
                        )
                        session.add(new_contact)
                        session.flush()
                        session.add(H_ContactLink(heir_id=new_heir.id, contact_id=new_contact.id))

            # 5. 金融資産
            assets_list = case_data.get("financial_assets", [])
            for a_data in assets_list:
                new_asset = FinancialAsset(
                    case_id=new_case.case_id,
                    bank_id=a_data.get("bank_id"),
                    branch_id=a_data.get("branch_id"),
                    account_type_id=a_data.get("account_type_id"),
                    account_number=a_data.get("account_number"),
                    balance=a_data.get("balance"),
                    status=a_data.get("status")
                )
                session.add(new_asset)

        session.commit()
        return True, f"JSON取込完了: 新規{count_created}件 / 上書き{count_updated}件"

    except Exception as e:
        session.rollback()
        print(f"JSON Import Error: {e}")
        import traceback
        traceback.print_exc()
        return False, f"エラーが発生しました: {str(e)}"
    finally:
        session.close()