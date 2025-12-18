# src/services/json_backup_service.py

import datetime
import json
import os
import platform
import re
import traceback
from typing import Tuple

from sqlalchemy.orm import joinedload

from src.models.database import SessionLocal
from src.models.tables import (
    AccountTypeMaster,
    Address,
    BankMaster,
    BranchMaster,
    Case,
    CaseStatus,
    Contact,
    Coordinate,
    Deceased,
    Expense,
    FinancialAsset,
    H_AddressHistory,
    H_ContactLink,
    Heir,
    InsuranceAsset,
    Liability,
    OtherAsset,
    RealEstateAsset,
    Task,
    User,
    BankAlias,
)


# --- デバッグ用ロガー ---
def log_error_to_desktop(message: str):
    """エラーをデスクトップのログファイルに書き出す（macOS/Windows対応）"""
    try:
        desktop = os.path.expanduser("~/Desktop")
        log_path = os.path.join(desktop, "backup_error_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # ログ書き込み自体のエラーは無視


# --- 日付型などをJSONシリアライズ可能にするヘルパー ---
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)


# 柔軟な日付解析関数
def _parse_flexible_date(date_str: str | None) -> datetime.date | None:
    if not date_str:
        return None
    if "T" in date_str:
        try:
            return datetime.datetime.fromisoformat(date_str).date()
        except ValueError:
            pass
    try:
        return datetime.date.fromisoformat(date_str)
    except ValueError:
        pass
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        pass
    try:
        return datetime.datetime.strptime(date_str, "%Y/%m/%d").date()
    except ValueError:
        return None


def _parse_flexible_datetime(date_str: str | None) -> datetime.datetime | None:
    if not date_str:
        return None
    try:
        return datetime.datetime.fromisoformat(date_str)
    except ValueError:
        d = _parse_flexible_date(date_str)
        if d:
            return datetime.datetime(d.year, d.month, d.day)
        return None


def _get_address_dict(session, address_id):
    if not address_id:
        return None
    addr = session.query(Address).get(address_id)
    if not addr:
        return None
    return {
        "zip_code": addr.zip_code,
        "prefecture": addr.prefecture,
        "city_ward_town": addr.city_ward_town,
        "street_address": addr.street_address,
        "building_name": addr.building_name,
    }


def _create_address_record(session, addr_data):
    if not addr_data:
        return None
    new_addr = Address(
        zip_code=addr_data.get("zip_code"),
        prefecture=addr_data.get("prefecture"),
        city_ward_town=addr_data.get("city_ward_town"),
        street_address=addr_data.get("street_address"),
        building_name=addr_data.get("building_name"),
    )
    session.add(new_addr)
    session.flush()
    return new_addr.id


# ==========================================
# エクスポート (出力)
# ==========================================
def export_database_to_json(file_path: str) -> bool:
    session = SessionLocal()
    try:
        # ディレクトリの存在確認と作成
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        # --- 1. マスタデータの取得 ---
        masters = {
            "users": [],
            "case_statuses": [],
            "account_types": [],
            "banks": [],
            "bank_aliases": [],
            "branches": [],
            "coordinates": [],
        }

        for u in session.query(User).all():
            masters["users"].append(
                {"id": u.id, "windows_id": u.windows_id, "name": u.name, "role": u.role}
            )
        for s in session.query(CaseStatus).all():
            masters["case_statuses"].append({"id": s.id, "name": s.name, "order_num": s.order_num})
        for a in session.query(AccountTypeMaster).all():
            masters["account_types"].append({"id": a.id, "type_name": a.type_name})
        for b in session.query(BankMaster).all():
            masters["banks"].append(
                {"id": b.id, "bank_name": b.bank_name, "bank_code": b.bank_code}
            )
        
        # BankAliasのエクスポート
        try:
            for alias in session.query(BankAlias).all():
                masters["bank_aliases"].append(
                    {"id": alias.id, "alias_name": alias.alias_name, "bank_id": alias.bank_id}
                )
        except Exception:
            print("Warning: BankAlias table not found or empty, skipping alias export.")

        for br in session.query(BranchMaster).all():
            masters["branches"].append(
                {
                    "id": br.id,
                    "bank_id": br.bank_id,
                    "branch_name": br.branch_name,
                    "branch_code": br.branch_code,
                }
            )
        for co in session.query(Coordinate).all():
            masters["coordinates"].append(
                {
                    "id": co.id,
                    "label": co.label,
                    "x_point": co.x_point,
                    "y_point": co.y_point,
                    "value": co.value, # value, description はカラムとして存在するか要確認(tables.pyにはあった)
                    "description": co.description,
                }
            )

        # --- 2. 案件データの取得 ---
        cases = (
            session.query(Case)
            .options(
                joinedload(Case.deceased_ref).joinedload(Deceased.heirs),
                joinedload(Case.financial_assets),
                joinedload(Case.tasks),
                joinedload(Case.real_estates),
                joinedload(Case.liabilities),
                joinedload(Case.insurance_assets),
                joinedload(Case.other_assets),
                joinedload(Case.expenses),
            )
            .all()
        )

        cases_list = []

        for case in cases:
            case_dict = {
                "case_id": case.case_id,
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
                "sol_case_number": getattr(case, "sol_case_number", None), # 安全に取得
                "deceased": None,
                "heirs": [],
                "financial_assets": [],
                "tasks": [],
                "real_estates": [],
                "liabilities": [],
                "insurance_assets": [],
                "other_assets": [],
                "expenses": [],
            }

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
                    "last_address": _get_address_dict(session, d.last_address_id),
                }
                case_dict["deceased"] = d_dict

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
                        "contacts": [],
                    }

                    h_addr_link = (
                        session.query(H_AddressHistory)
                        .filter(
                            H_AddressHistory.heir_id == h.id,
                            H_AddressHistory.is_current_address == True,
                        )
                        .first()
                    )
                    if h_addr_link:
                        h_dict["current_address"] = _get_address_dict(
                            session, h_addr_link.address_id
                        )

                    links = session.query(H_ContactLink).filter(H_ContactLink.heir_id == h.id).all()
                    for link in links:
                        contact = session.query(Contact).get(link.contact_id)
                        if contact:
                            h_dict["contacts"].append(
                                {
                                    "type": contact.type,
                                    "value": contact.value,
                                    "sub_type": contact.sub_type,
                                }
                            )

                    case_dict["heirs"].append(h_dict)

            for asset in case.financial_assets:
                case_dict["financial_assets"].append(
                    {
                        "asset_type": asset.asset_type,
                        "bank_id": asset.bank_id,
                        "branch_id": asset.branch_id,
                        "account_type_id": asset.account_type_id,
                        "account_number": asset.account_number,
                        "balance": asset.balance,
                        "status": asset.status,
                    }
                )

            for t in case.tasks:
                case_dict["tasks"].append(
                    {
                        "template_id": t.template_id,
                        "description": t.description,
                        "assigned_user_id": t.assigned_user_id,
                        "due_date": t.due_date,
                        "is_completed": t.is_completed,
                        "last_updated_at": t.last_updated_at,
                    }
                )

            # 【修正箇所】 RealEstateAsset のエクスポート処理
            # municipality_name を廃止し、locationなどの実在カラムを使用
            for re_data in case.real_estates:
                case_dict["real_estates"].append({
                    "property_type": re_data.property_type,
                    "location": re_data.location,
                    "lot_number": re_data.lot_number,
                    "land_category": re_data.land_category,
                    "land_area": re_data.land_area,
                    "house_number": re_data.house_number,
                    "structure": re_data.structure,
                    "floor_area": re_data.floor_area,
                    "ownership_share": re_data.ownership_share,
                    "registry_pdf_path": re_data.registry_pdf_path,
                    "registry_image_path": re_data.registry_image_path
                })

            for lb in case.liabilities:
                case_dict["liabilities"].append(
                    {
                        "is_debt": lb.is_debt,
                        "description": lb.description,
                        "amount": lb.amount,
                        "is_funeral_cost": lb.is_funeral_cost,
                    }
                )

            for ins in case.insurance_assets:
                case_dict["insurance_assets"].append(
                    {
                        "insurance_company": ins.insurance_company,
                        "policy_number": ins.policy_number,
                        "estimated_value": ins.estimated_value,
                    }
                )

            for other in case.other_assets:
                case_dict["other_assets"].append(
                    {"description": other.description, "estimated_value": other.estimated_value}
                )

            for exp in case.expenses:
                case_dict["expenses"].append(
                    {
                        "description": exp.description,
                        "amount": exp.amount,
                        "expense_date": exp.expense_date,
                    }
                )

            cases_list.append(case_dict)

        final_data = {
            "version": "2.2",
            "exported_at": datetime.datetime.now(),
            "masters": masters,
            "cases": cases_list,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, cls=DateTimeEncoder, ensure_ascii=False, indent=2)

        print(f"✅ Export successful: {file_path}")
        return True

    except Exception as e:
        error_msg = f"Export Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        log_error_to_desktop(error_msg)  # デスクトップにログを出力
        return False
    finally:
        session.close()


# ==========================================
# インポート (取込・復元)
# ==========================================
def import_database_from_json(file_path: str) -> Tuple[bool, str]:
    session = SessionLocal()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        # Windows特有のバックスラッシュ置換を行わない (Windows環境でもJSONは/が安全)
        if platform.system() == "Windows":
            file_content = re.sub(r'(?<!\\)\\(?![u"\\/bfnrt])', r"\\\\", file_content)

        try:
            raw_data = json.loads(file_content)
        except json.JSONDecodeError:
            # パースエラー時のフォールバック
            file_content = file_content.replace("\\", "\\\\")
            raw_data = json.loads(file_content)

        if isinstance(raw_data, list):
            cases_data = raw_data
            masters_data = {}
        else:
            cases_data = raw_data.get("cases", [])
            masters_data = raw_data.get("masters", {})

        # --- 1. マスタデータの復元 ---
        if "users" in masters_data:
            for u in masters_data["users"]:
                existing = session.query(User).get(u["id"])
                if existing:
                    existing.windows_id = u["windows_id"]
                    existing.name = u["name"]
                    existing.role = u["role"]
                else:
                    session.add(
                        User(id=u["id"], windows_id=u["windows_id"], name=u["name"], role=u["role"])
                    )
            session.flush()

        if "case_statuses" in masters_data:
            for s in masters_data["case_statuses"]:
                existing = session.query(CaseStatus).get(s["id"])
                if existing:
                    existing.name = s["name"]
                    existing.order_num = s["order_num"]
                else:
                    session.add(CaseStatus(id=s["id"], name=s["name"], order_num=s["order_num"]))
            session.flush()

        if "account_types" in masters_data:
            for a in masters_data["account_types"]:
                existing = session.query(AccountTypeMaster).get(a["id"])
                if existing:
                    existing.type_name = a["type_name"]
                else:
                    session.add(AccountTypeMaster(id=a["id"], type_name=a["type_name"]))
            session.flush()

        if "banks" in masters_data:
            for b in masters_data["banks"]:
                existing = session.query(BankMaster).get(b["id"])
                if existing:
                    existing.bank_name = b["bank_name"]
                    existing.bank_code = b["bank_code"]
                else:
                    session.add(
                        BankMaster(id=b["id"], bank_name=b["bank_name"], bank_code=b["bank_code"])
                    )
            session.flush()
        
        # BankAliasのインポート
        if "bank_aliases" in masters_data:
            try:
                for ba in masters_data["bank_aliases"]:
                    parent_bank = session.query(BankMaster).get(ba["bank_id"])
                    if parent_bank:
                        existing = session.query(BankAlias).get(ba["id"])
                        if existing:
                            existing.alias_name = ba["alias_name"]
                            existing.bank_id = ba["bank_id"]
                        else:
                            session.add(
                                BankAlias(id=ba["id"], alias_name=ba["alias_name"], bank_id=ba["bank_id"])
                            )
                session.flush()
            except Exception:
                print("Warning: Skipping BankAlias import due to error/missing table.")

        if "branches" in masters_data:
            for br in masters_data["branches"]:
                existing = session.query(BranchMaster).get(br["id"])
                if existing:
                    existing.bank_id = br["bank_id"]
                    existing.branch_name = br["branch_name"]
                    existing.branch_code = br["branch_code"]
                else:
                    session.add(
                        BranchMaster(
                            id=br["id"],
                            bank_id=br["bank_id"],
                            branch_name=br["branch_name"],
                            branch_code=br["branch_code"],
                        )
                    )
            session.flush()

        if "coordinates" in masters_data:
            for co in masters_data["coordinates"]:
                existing = session.query(Coordinate).get(co["id"])
                if existing:
                    existing.label = co["label"]
                    existing.x_point = co["x_point"]
                    existing.y_point = co["y_point"]
                    existing.value = co.get("value")
                    existing.description = co.get("description")
                else:
                    session.add(
                        Coordinate(
                            id=co["id"],
                            label=co["label"],
                            x_point=co["x_point"],
                            y_point=co["y_point"],
                            value=co.get("value"),
                            description=co.get("description"),
                        )
                    )
            session.flush()

        # --- 2. 案件データの復元 ---
        count_created = 0
        count_updated = 0

        for case_data in cases_data:
            case_num = case_data.get("case_number")
            if not case_num:
                continue

            existing_case = session.query(Case).filter(Case.case_number == case_num).first()

            if existing_case:
                session.delete(existing_case)
                session.flush()
                count_updated += 1
            else:
                count_created += 1

            contract_d = _parse_flexible_date(case_data.get("contract_date"))
            tax_d_str = case_data.get("tax_deadline")
            tax_d = _parse_flexible_datetime(tax_d_str)

            # フォルダパスの補正
            raw_folder_path = case_data.get("folder_path")
            fixed_folder_path = None

            if raw_folder_path:
                fixed_folder_path = raw_folder_path.replace("\\", "/")

            new_case = Case(
                case_id=case_data.get("case_id"),
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
                sol_case_number=case_data.get("sol_case_number"), # 安全にインポート
            )
            session.add(new_case)
            session.flush()

            # 被相続人
            d_data = case_data.get("deceased")
            if d_data:
                new_deceased = Deceased(
                    case_id=new_case.case_id,
                    name_last=d_data.get("name_last"),
                    name_first=d_data.get("name_first"),
                    name_last_kana=d_data.get("name_last_kana"),
                    name_first_kana=d_data.get("name_first_kana"),
                    hometown=d_data.get("hometown"),
                    date_of_birth=_parse_flexible_date(d_data.get("date_of_birth")),
                    date_of_death=_parse_flexible_date(d_data.get("date_of_death")),
                )
                addr_id = _create_address_record(session, d_data.get("last_address"))
                if addr_id:
                    new_deceased.last_address_id = addr_id

                session.add(new_deceased)
                session.flush()

                # 相続人
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
                        date_of_birth=_parse_flexible_date(h_data.get("date_of_birth")),
                    )
                    session.add(new_heir)
                    session.flush()

                    h_addr_id = _create_address_record(session, h_data.get("current_address"))
                    if h_addr_id:
                        session.add(
                            H_AddressHistory(
                                heir_id=new_heir.id, address_id=h_addr_id, is_current_address=True
                            )
                        )

                    for c_data in h_data.get("contacts", []):
                        new_contact = Contact(
                            type=c_data.get("type"),
                            value=c_data.get("value"),
                            sub_type=c_data.get("sub_type"),
                        )
                        session.add(new_contact)
                        session.flush()
                        session.add(H_ContactLink(heir_id=new_heir.id, contact_id=new_contact.id))

            # 金融資産
            for a_data in case_data.get("financial_assets", []):
                new_asset = FinancialAsset(
                    case_id=new_case.case_id,
                    asset_type=a_data.get("asset_type", "BANK"),
                    bank_id=a_data.get("bank_id"),
                    branch_id=a_data.get("branch_id"),
                    account_type_id=a_data.get("account_type_id"),
                    account_number=a_data.get("account_number"),
                    balance=a_data.get("balance"),
                    status=a_data.get("status"),
                )
                session.add(new_asset)

            # タスク
            for t_data in case_data.get("tasks", []):
                new_task = Task(
                    case_id=new_case.case_id,
                    template_id=t_data.get("template_id"),
                    description=t_data.get("description"),
                    assigned_user_id=t_data.get("assigned_user_id"),
                    due_date=_parse_flexible_datetime(t_data.get("due_date")),
                    is_completed=t_data.get("is_completed"),
                    last_updated_at=_parse_flexible_datetime(t_data.get("last_updated_at")),
                )
                session.add(new_task)

            # 【修正箇所】 RealEstateAsset のインポート処理
            # location, property_type などの新しいフィールドにマッピング
            for re_data in case_data.get("real_estates", []):
                # 古いバックアップデータ（municipality_nameがある場合）との互換性
                loc = re_data.get("location")
                if not loc:
                    # 後方互換性: municipality_name があればそれを location に
                    loc = re_data.get("municipality_name", "不明")

                session.add(
                    RealEstateAsset(
                        case_id=new_case.case_id,
                        property_type=re_data.get("property_type", "Land"),
                        location=loc,
                        lot_number=re_data.get("lot_number"),
                        land_category=re_data.get("land_category"),
                        land_area=re_data.get("land_area"),
                        house_number=re_data.get("house_number"),
                        structure=re_data.get("structure"),
                        floor_area=re_data.get("floor_area"),
                        ownership_share=re_data.get("ownership_share"),
                        registry_pdf_path=re_data.get("registry_pdf_path"),
                        registry_image_path=re_data.get("registry_image_path")
                    )
                )

            for lb in case_data.get("liabilities", []):
                session.add(
                    Liability(
                        case_id=new_case.case_id,
                        is_debt=lb.get("is_debt"),
                        description=lb.get("description"),
                        amount=lb.get("amount"),
                        is_funeral_cost=lb.get("is_funeral_cost"),
                    )
                )

            for ins in case_data.get("insurance_assets", []):
                session.add(
                    InsuranceAsset(
                        case_id=new_case.case_id,
                        insurance_company=ins.get("insurance_company"),
                        policy_number=ins.get("policy_number"),
                        estimated_value=ins.get("estimated_value"),
                    )
                )

            for other in case_data.get("other_assets", []):
                session.add(
                    OtherAsset(
                        case_id=new_case.case_id,
                        description=other.get("description"),
                        estimated_value=other.get("estimated_value"),
                    )
                )

            for exp in case_data.get("expenses", []):
                session.add(
                    Expense(
                        case_id=new_case.case_id,
                        description=exp.get("description"),
                        amount=exp.get("amount"),
                        expense_date=_parse_flexible_date(exp.get("expense_date")),
                    )
                )

        session.commit()
        return True, f"JSON取込完了: 新規{count_created}件 / 上書き{count_updated}件"

    except Exception as e:
        session.rollback()
        error_msg = f"Import Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        log_error_to_desktop(error_msg)
        return False, f"エラーが発生しました: {str(e)}"
    finally:
        session.close()