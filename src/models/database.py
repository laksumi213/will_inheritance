# src/models/database.py
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import settings

# データベースエンジンの作成
engine = create_engine(
    f"sqlite:///{settings.DB_PATH}", echo=False, connect_args={"check_same_thread": False}
)

# セッション作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# モデルの基底クラス
Base = declarative_base()


def get_db():
    """DBセッションを取得するジェネレータ (Dependency Injection用)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """テーブルを作成し、初期データを投入する"""
    # モデル定義をインポートしてmetadataに登録

    try:
        Base.metadata.create_all(bind=engine)
        print("Database initialized successfully.")

        # 初期データの投入
        add_initial_data()

    except Exception as e:
        print(f"Database initialization failed: {e}")


def add_initial_data():
    """初期データとサンプル案件の投入"""
    from src.models.tables import (
        AccountTypeMaster,
        Address,
        BankMaster,
        BranchMaster,
        Case,
        CaseStatus,
        Contact,
        Deceased,
        FinancialAsset,
        H_AddressHistory,
        H_ContactLink,
        Heir,
        Liability,
        User,
    )

    session = SessionLocal()
    try:
        # 1. 担当者とステータスの初期登録 (存在チェック付き)
        if not session.query(User).filter_by(windows_id="admin01").first():
            user1 = User(windows_id="admin01", name="管理者 太郎", role="Manager")
            session.add(user1)

        if not session.query(CaseStatus).filter_by(name="受託").first():
            status1 = CaseStatus(name="受託", order_num=3)
            session.add(status1)

        session.flush()

        # 2. 銀行マスタの初期登録
        if not session.query(BankMaster).filter_by(bank_code="0001").first():
            bank_master = BankMaster(bank_name="みずほ銀行", bank_code="0001")
            session.add(bank_master)
            session.flush()

            # 2-2. 支店マスタ
            branch_master = BranchMaster(
                bank_id=bank_master.id, branch_name="銀座中央", branch_code="050"
            )
            session.add(branch_master)

        # 2-3. 口座種類マスタ
        initial_account_types = [
            "普通預金",
            "定期預金",
            "当座預金",
            "普通貯金",
            "定期貯金",
            "投資信託",
            "外貨預金",
        ]

        for type_name in initial_account_types:
            if not session.query(AccountTypeMaster).filter_by(type_name=type_name).first():
                session.add(AccountTypeMaster(type_name=type_name))

        session.commit()

        # 3. サンプル案件データの登録 (初回のみ)
        if session.query(Case).count() == 0:
            # ID再取得
            user1 = session.query(User).filter_by(windows_id="admin01").first()
            status1 = session.query(CaseStatus).filter_by(name="受託").first()

            # 案件 (Case: G2103) の登録
            case1 = Case(
                case_number="G2103",
                client_name="水谷 昌代",
                client_name_kana="みずたに　まさよ",
                manager_id=user1.id,
                current_status_id=status1.id,
                contract_date=date(2025, 10, 1),
                fee_contract_amount=500000.0,
                folder_path=r"\\192.168.11.20\行政書士法人チェスター\01.個別ＪＯＢ\G2103水谷昌代様（スタンダードプラン）",
            )
            session.add(case1)
            session.flush()

            # 4. 被相続人 (Deceased: 水谷 弘) の登録
            addr_deceased = Address(
                zip_code="104-0053",
                prefecture="東京都",
                city_ward_town="中央区晴海",
                street_address="二丁目5番16号",
                building_name="1101号",
            )
            session.add(addr_deceased)
            session.flush()

            d1 = Deceased(
                case_id=case1.case_id,
                name_last="水谷",
                name_first="弘",
                name_last_kana="みずたに",
                name_first_kana="ひろし",
                date_of_birth=date(1935, 1, 12),
                date_of_death=date(2025, 5, 16),
                hometown="東京都台東区東上野一丁目1番地",
                relationship_type="本人",
                last_address_id=addr_deceased.id,
            )
            session.add(d1)
            session.flush()

            # 5. 契約者 (Heir: 水谷 昌代, 妻) の登録
            h1 = Heir(
                deceased_id=d1.id,
                name_last="水谷",
                name_first="昌代",
                name_last_kana="みずたに",
                name_first_kana="まさよ",
                relationship_type="妻",
                date_of_birth=date(1946, 11, 29),
                hometown="東京都台東区東上野1-1",
                is_contracting_party=True,  # 契約者フラグ
            )
            session.add(h1)
            session.flush()

            h1_addr_link = H_AddressHistory(
                heir_id=h1.id, address_id=addr_deceased.id, is_current_address=True
            )
            session.add(h1_addr_link)

            contact_phone = Contact(value="03-3533-1675", type="PHONE", sub_type="Primary")
            session.add(contact_phone)
            session.flush()

            h1_contact_link = H_ContactLink(heir_id=h1.id, contact_id=contact_phone.id)
            session.add(h1_contact_link)

            # 6. 金融資産 (FinancialAsset) の登録
            bank_master = session.query(BankMaster).filter_by(bank_code="0001").first()
            branch_master = (
                session.query(BranchMaster)
                .filter_by(bank_id=bank_master.id, branch_code="050")
                .first()
            )
            account_type_master = (
                session.query(AccountTypeMaster).filter_by(type_name="普通預金").first()
            )

            if bank_master and branch_master and account_type_master:
                bank1 = FinancialAsset(
                    case_id=case1.case_id,
                    bank_id=bank_master.id,
                    branch_id=branch_master.id,
                    account_type_id=account_type_master.id,
                    account_number="1234567",
                    balance=5000000.0,
                    status="調査中",
                )
                session.add(bank1)

            # 7. 負債/葬儀費用の登録
            liability1 = Liability(
                case_id=case1.case_id,
                is_debt=False,
                description="葬儀費用",
                amount=2500000.0,
                is_funeral_cost=True,
            )
            session.add(liability1)

            session.commit()
            print("Initial data seeded successfully.")

    except Exception as e:
        session.rollback()
        print(f"Failed to add initial data: {e}")
    finally:
        session.close()
