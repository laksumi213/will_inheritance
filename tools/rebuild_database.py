# tools/rebuild_database.py
import sys
import os

# プロジェクトルートをパスに追加してモジュールを読み込めるようにする
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.database import engine, Base, add_initial_data
# 全てのテーブルモデルをインポートしてmetadataに登録させる
from src.models.tables import (
    User, CaseStatus, AccountTypeMaster, BankMaster, BranchMaster,
    Case, Deceased, Heir, Address, Contact,
    FinancialAsset, RealEstateAsset, Liability, 
    Task, H_AddressHistory, H_ContactLink, D_AddressHistory, D_ContactLink,
    InsuranceAsset, OtherAsset, Expense, Coordinate,
    CaseContactPoint, TaskTemplate, TaskDocumentLog,
    DocumentType, ShippingMethod, SubmissionDocType, CaseSubmissionDoc
)

def rebuild_database():
    """
    データベースを完全に削除し、最新のモデル定義に基づいて再構築します。
    """
    print("==========================================")
    print("🔄 データベース再構築ツール")
    print("==========================================")
    
    # 1. DB接続確認
    print("Checking database connection...")
    try:
        with engine.connect() as connection:
            print(" -> Connection OK.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    # 2. 既存テーブルの削除
    print("\n🗑️  既存のテーブルを削除しています...")
    try:
        # 外部キー制約等の関係で削除順序が重要な場合があるため、
        # SQLAlchemyのdrop_allに任せつつ、エラー時は強制続行などを検討
        Base.metadata.drop_all(bind=engine)
        print(" -> 全テーブルの削除に成功しました。")
    except Exception as e:
        print(f"⚠️ テーブル削除中にエラーが発生しましたが、続行します: {e}")

    # 3. テーブルの新規作成
    print("\n🏗️  テーブルを新規作成しています...")
    try:
        # src/models/tables.py の定義に基づいてテーブルを作成
        Base.metadata.create_all(bind=engine)
        print(" -> テーブル作成完了。")
    except Exception as e:
        print(f"❌ テーブル作成エラー: {e}")
        return

    # 4. 初期データの投入
    print("\n🌱 初期データ（マスタ・サンプル案件）を投入しています...")
    try:
        add_initial_data()
        print(" -> 初期データ投入完了。")
    except Exception as e:
        print(f"❌ 初期データ投入エラー: {e}")
        return

    print("\n✅ データベースの再構築が完了しました！")
    print("アプリを再起動して動作を確認してください。")

if __name__ == "__main__":
    rebuild_database()