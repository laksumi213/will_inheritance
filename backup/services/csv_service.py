# /services/csv_service.py

import csv
import datetime
from sqlalchemy.orm import Session, joinedload
from services.db_setup import (
    Engine, Case, Deceased, User, CaseStatus, Heir, Address, Contact, H_ContactLink,
    H_AddressHistory, D_AddressHistory,
    get_all_users, get_all_case_statuses
)

# --- CSVヘッダー定義（DBの全主要項目を網羅） ---
CSV_HEADERS = [
    # --- 案件基本情報 ---
    "case_number",          # 案件番号 (Key)
    "status_name",          # ステータス
    "manager_name",         # 担当1
    "operator_name",        # 担当2
    "contract_date",        # 受託日
    "tax_deadline",         # 申告期限
    "fee_amount",           # 報酬額
    "deposit_req",          # 着手金請求額
    "deposit_paid",         # 着手金入金額
    "is_paid_full",         # 全額入金済みフラグ (0/1)
    "folder_path",          # フォルダパス

    # --- 被相続人情報 (Deceased) ---
    "deceased_last",        # 姓
    "deceased_first",       # 名
    "deceased_kana_last",   # セイ
    "deceased_kana_first",  # メイ
    "deceased_dob",         # 生年月日
    "deceased_dod",         # 死亡日
    "deceased_hometown",    # 本籍地

    # --- 被相続人 最終住所 ---
    "d_zip", "d_pref", "d_city", "d_street", "d_bldg",

    # --- 契約者情報 (Client/Heir) ---
    "client_last",          # 姓
    "client_first",         # 名
    "client_kana_last",     # セイ
    "client_kana_first",    # メイ
    "client_rel",           # 続柄
    "client_dob",           # 生年月日
    "client_hometown",      # 本籍地

    # --- 契約者 住所 ---
    "c_zip", "c_pref", "c_city", "c_street", "c_bldg",

    # --- 契約者 連絡先 ---
    "c_phone",              # 電話番号 (代表)
    "c_email"               # メールアドレス (代表)
]

def _format_date(d):
    """日付オブジェクトをYYYY-MM-DD文字列に変換"""
    return d.strftime("%Y-%m-%d") if d else ""

def _parse_date(s):
    """文字列を日付オブジェクトに変換"""
    if not s: return None
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None

def _get_address_str(address_obj):
    """Addressオブジェクトから辞書を生成"""
    if not address_obj:
        return {"zip": "", "pref": "", "city": "", "street": "", "bldg": ""}
    return {
        "zip": address_obj.zip_code or "",
        "pref": address_obj.prefecture or "",
        "city": address_obj.city_ward_town or "",
        "street": address_obj.street_address or "",
        "bldg": address_obj.building_name or ""
    }

def export_cases_to_csv(file_path: str) -> bool:
    """全案件の詳細情報をCSVに出力する"""
    session = Session(bind=Engine)
    try:
        # 関連情報をすべて結合して取得
        cases = session.query(Case).options(
            joinedload(Case.deceased_ref).joinedload(Deceased.last_address),
            joinedload(Case.status_ref),
            joinedload(Case.manager),
            joinedload(Case.operator)
        ).all()

        with open(file_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()

            for case in cases:
                row = {}
                
                # 1. 案件基本情報
                row["case_number"] = case.case_number
                row["status_name"] = case.status_ref.name if case.status_ref else ""
                row["manager_name"] = case.manager.name if case.manager else ""
                row["operator_name"] = case.operator.name if case.operator else ""
                row["contract_date"] = _format_date(case.contract_date)
                row["tax_deadline"] = case.tax_deadline.strftime("%Y-%m-%d") if case.tax_deadline else ""
                row["fee_amount"] = case.fee_contract_amount or 0
                row["deposit_req"] = case.deposit_required_amount or 0
                row["deposit_paid"] = case.deposit_paid_amount or 0
                row["is_paid_full"] = 1 if case.is_paid_in_full else 0
                row["folder_path"] = case.folder_path or ""

                # 2. 被相続人情報
                d = case.deceased_ref
                if d:
                    row["deceased_last"] = d.name_last
                    row["deceased_first"] = d.name_first
                    row["deceased_kana_last"] = d.name_last_kana
                    row["deceased_kana_first"] = d.name_first_kana
                    row["deceased_dob"] = _format_date(d.date_of_birth)
                    row["deceased_dod"] = _format_date(d.date_of_death)
                    row["deceased_hometown"] = d.hometown
                    
                    # 住所
                    addr = _get_address_str(d.last_address)
                    row["d_zip"] = addr["zip"]
                    row["d_pref"] = addr["pref"]
                    row["d_city"] = addr["city"]
                    row["d_street"] = addr["street"]
                    row["d_bldg"] = addr["bldg"]
                else:
                    # 空埋め
                    for k in ["deceased_last", "deceased_first", "deceased_kana_last", "deceased_kana_first", "deceased_dob", "deceased_dod", "deceased_hometown", "d_zip", "d_pref", "d_city", "d_street", "d_bldg"]:
                        row[k] = ""

                # 3. 契約者情報 (Heir where is_contracting_party=True)
                # Deceased経由で取得
                client = None
                if d:
                    client = session.query(Heir).filter(Heir.deceased_id == d.id, Heir.is_contracting_party == True).first()
                
                if client:
                    row["client_last"] = client.name_last
                    row["client_first"] = client.name_first
                    row["client_kana_last"] = client.name_last_kana
                    row["client_kana_first"] = client.name_first_kana
                    row["client_rel"] = client.relationship_type
                    row["client_dob"] = _format_date(client.date_of_birth)
                    row["client_hometown"] = client.hometown

                    # 契約者住所 (現在の住所)
                    c_addr_link = session.query(H_AddressHistory).filter(H_AddressHistory.heir_id == client.id, H_AddressHistory.is_current_address == True).first()
                    c_addr_obj = session.query(Address).get(c_addr_link.address_id) if c_addr_link else None
                    addr = _get_address_str(c_addr_obj)
                    row["c_zip"] = addr["zip"]
                    row["c_pref"] = addr["pref"]
                    row["c_city"] = addr["city"]
                    row["c_street"] = addr["street"]
                    row["c_bldg"] = addr["bldg"]

                    # 契約者連絡先
                    # 簡易的に最初に見つかった電話とメールを取得
                    contacts = session.query(Contact).join(H_ContactLink).filter(H_ContactLink.heir_id == client.id).all()
                    phone = next((c.value for c in contacts if c.type == "PHONE"), "")
                    email = next((c.value for c in contacts if c.type == "EMAIL"), "")
                    row["c_phone"] = phone
                    row["c_email"] = email

                else:
                    for k in ["client_last", "client_first", "client_kana_last", "client_kana_first", "client_rel", "client_dob", "client_hometown", "c_zip", "c_pref", "c_city", "c_street", "c_bldg", "c_phone", "c_email"]:
                        row[k] = ""

                writer.writerow(row)
        return True
    except Exception as e:
        print(f"CSV Export Error: {e}")
        return False
    finally:
        session.close()

def _update_address_from_csv(session, zip_c, pref, city, street, bldg):
    """CSVデータからAddressレコードを作成または取得してIDを返す"""
    if not pref and not street:
        return None
    # 常に新規作成して履歴管理するのが安全だが、今回は簡易的に新規作成して返す
    new_addr = Address(
        zip_code=zip_c, prefecture=pref, city_ward_town=city, 
        street_address=street, building_name=bldg
    )
    session.add(new_addr)
    session.flush()
    return new_addr.id

def _update_contact_from_csv(session, heir_id, value, type_str):
    """連絡先を更新（既存削除→新規登録）"""
    if not value: return

    # 既存の同タイプ連絡先があれば削除 (簡易実装)
    # 本当は厳密なマッチングが必要だが、上書き仕様なのでクリアして再登録する
    existing_links = session.query(H_ContactLink).join(Contact).filter(
        H_ContactLink.heir_id == heir_id, Contact.type == type_str
    ).all()
    
    for link in existing_links:
        session.delete(link) # Link削除
        # Contact本体の削除は、他で使われてない前提でスキップまたはGCが必要
    
    # 新規登録
    new_contact = Contact(value=value, type=type_str, sub_type="Primary")
    session.add(new_contact)
    session.flush()
    
    new_link = H_ContactLink(heir_id=heir_id, contact_id=new_contact.id)
    session.add(new_link)

def import_cases_from_csv(file_path: str) -> tuple[bool, str]:
    """CSVを取り込み、案件番号が一致すれば上書き更新、なければ新規登録"""
    session = Session(bind=Engine)
    
    # マッピング用辞書
    user_map = {u.name: u.id for u in session.query(User).all()}
    status_map = {s.name: s.id for s in session.query(CaseStatus).all()}

    try:
        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            
            # ヘッダー簡易チェック
            if "case_number" not in reader.fieldnames:
                 return False, "CSVフォーマットエラー: case_number列が見つかりません"

            count_updated = 0
            count_created = 0

            for row in reader:
                case_num = row.get("case_number")
                if not case_num: continue

                # 既存チェック
                case = session.query(Case).filter(Case.case_number == case_num).first()
                
                # 値の準備
                mgr_id = user_map.get(row.get("manager_name"))
                ope_id = user_map.get(row.get("operator_name"))
                st_id = status_map.get(row.get("status_name"))
                
                contract_d = _parse_date(row.get("contract_date"))
                tax_d = _parse_date(row.get("tax_deadline"))
                
                # クライアント名の構築
                c_full = f"{row.get('client_last', '')} {row.get('client_first', '')}".strip()
                c_kana_full = f"{row.get('client_kana_last', '')} {row.get('client_kana_first', '')}".strip()

                if case:
                    # === UPDATE ===
                    case.client_name = c_full
                    case.client_name_kana = c_kana_full
                    case.manager_id = mgr_id
                    case.operator_id = ope_id
                    if st_id: case.current_status_id = st_id
                    case.contract_date = contract_d
                    case.tax_deadline = tax_d
                    case.fee_contract_amount = float(row.get("fee_amount") or 0)
                    case.deposit_required_amount = float(row.get("deposit_req") or 0)
                    case.deposit_paid_amount = float(row.get("deposit_paid") or 0)
                    case.is_paid_in_full = True if row.get("is_paid_full") == "1" else False
                    case.folder_path = row.get("folder_path")
                    
                    count_updated += 1
                else:
                    # === INSERT ===
                    case = Case(
                        case_number=case_num,
                        client_name=c_full,
                        client_name_kana=c_kana_full,
                        manager_id=mgr_id,
                        operator_id=ope_id,
                        current_status_id=st_id,
                        contract_date=contract_d,
                        tax_deadline=tax_d,
                        fee_contract_amount=float(row.get("fee_amount") or 0),
                        deposit_required_amount=float(row.get("deposit_req") or 0),
                        deposit_paid_amount=float(row.get("deposit_paid") or 0),
                        is_paid_in_full=(True if row.get("is_paid_full") == "1" else False),
                        folder_path=row.get("folder_path")
                    )
                    session.add(case)
                    session.flush() # case_id取得
                    count_created += 1

                # --- Deceased 更新/作成 ---
                d = session.query(Deceased).filter(Deceased.case_id == case.case_id).first()
                if not d:
                    d = Deceased(case_id=case.case_id)
                    session.add(d)
                
                d.name_last = row.get("deceased_last")
                d.name_first = row.get("deceased_first")
                d.name_last_kana = row.get("deceased_kana_last")
                d.name_first_kana = row.get("deceased_kana_first")
                d.date_of_birth = _parse_date(row.get("deceased_dob"))
                d.date_of_death = _parse_date(row.get("deceased_dod"))
                d.hometown = row.get("deceased_hometown")
                
                # Deceased 住所
                d_addr_id = _update_address_from_csv(
                    session, row.get("d_zip"), row.get("d_pref"), row.get("d_city"), row.get("d_street"), row.get("d_bldg")
                )
                if d_addr_id:
                    d.last_address_id = d_addr_id # リンク更新
                    # D_AddressHistory もメンテすべきだが省略

                # --- Client (Heir) 更新/作成 ---
                # 契約者Heirを探す
                client = session.query(Heir).filter(Heir.deceased_id == d.id, Heir.is_contracting_party == True).first()
                if not client:
                    client = Heir(deceased_id=d.id, is_contracting_party=True)
                    session.add(client)
                
                client.name_last = row.get("client_last")
                client.name_first = row.get("client_first")
                client.name_last_kana = row.get("client_kana_last")
                client.name_first_kana = row.get("client_kana_first")
                client.relationship_type = row.get("client_rel")
                client.date_of_birth = _parse_date(row.get("client_dob"))
                client.hometown = row.get("client_hometown")
                session.flush()

                # Client 住所
                c_addr_id = _update_address_from_csv(
                    session, row.get("c_zip"), row.get("c_pref"), row.get("c_city"), row.get("c_street"), row.get("c_bldg")
                )
                if c_addr_id:
                    # 既存のCurrent AddressリンクをOFF
                    session.query(H_AddressHistory).filter(H_AddressHistory.heir_id == client.id).update({"is_current_address": False})
                    # 新規リンク
                    new_link = H_AddressHistory(heir_id=client.id, address_id=c_addr_id, is_current_address=True)
                    session.add(new_link)
                
                # Client 連絡先
                _update_contact_from_csv(session, client.id, row.get("c_phone"), "PHONE")
                _update_contact_from_csv(session, client.id, row.get("c_email"), "EMAIL")

            session.commit()
            return True, f"処理完了: 新規{count_created}件 / 更新{count_updated}件"

    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        return False, f"エラー: {str(e)}"
    finally:
        session.close()