# src/services/bank_automation_service.py
import os
import shutil
import unicodedata
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

# テーブル定義のインポート
from src.models.tables import BankMaster, BankAlias

class BankAutomationService:
    """
    銀行関連の自動化処理（検索、学習、ファイルリネーム等）を担当するサービスクラス
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def _normalize_name(self, text: str) -> str:
        """検索用に文字列を正規化する（全角統一、スペース削除）"""
        if not text:
            return ""
        # NFKCで正規化し、スペースを除去
        return unicodedata.normalize("NFKC", text).replace(" ", "").replace("　", "")

    def search_financial_institution(self, raw_bank_name: str) -> Optional[BankMaster]:
        """
        読み取った銀行名からマスタデータを検索する。
        Alias(学習済みデータ) -> 正規名称 -> ルールベース の順で検索。
        """
        if not raw_bank_name:
            return None

        clean_name = self._normalize_name(raw_bank_name)
        print(f"検索開始: {clean_name}")

        # --- STEP 1: 学習済みAliasテーブルからの検索 (最優先・最速) ---
        alias_stmt = select(BankAlias).where(
            BankAlias.alias_name == clean_name
        )
        alias_result = self.db.execute(alias_stmt).scalars().first()
        
        if alias_result:
            print(f"Aliasヒット: {clean_name} -> {alias_result.bank_ref.bank_name}")
            return alias_result.bank_ref

        # --- STEP 2: 正規名称での検索 ---
        institution = self._query_db_by_name(clean_name)
        if institution:
            return institution

        # --- STEP 3: ルールベースのリトライ (信組変換など) ---
        
        # 3-1. 信用組合 -> 信組 (七島信用組合 -> 七島信組 など)
        if "信用組合" in clean_name:
            alt_name_shinkumi = clean_name.replace("信用組合", "信組")
            print(f"リトライ検索 (信組変換): {alt_name_shinkumi}")
            institution = self._query_db_by_name(alt_name_shinkumi)
            if institution:
                # ★ここで自動学習: 次回から一発で引けるように登録
                self.learn_alias(clean_name, institution)
                return institution

        # 3-2. 銀行削除 (例: "三菱UFJ銀行" -> "三菱UFJ")
        if "銀行" in clean_name:
            alt_name_no_bank = clean_name.replace("銀行", "")
            print(f"リトライ検索 (銀行削除): {alt_name_no_bank}")
            if alt_name_no_bank:
                institution = self._query_db_by_name(alt_name_no_bank)
                if institution:
                    # ★ここで自動学習
                    self.learn_alias(clean_name, institution)
                    return institution

        print("該当する金融機関が見つかりませんでした。")
        return None

    def learn_alias(self, alias_name: str, bank: BankMaster) -> None:
        """
        検索でヒットしたパターンを「別名」としてDBに記憶させる（学習機能）
        """
        try:
            # 既に登録済みかチェック
            existing = self.db.query(BankAlias).filter_by(alias_name=alias_name).first()
            if existing:
                return

            new_alias = BankAlias(
                alias_name=alias_name,
                bank_id=bank.id
            )
            self.db.add(new_alias)
            self.db.commit()
            print(f"学習完了: '{alias_name}' を '{bank.bank_name}' の別名として登録しました。")
            
        except Exception as e:
            self.db.rollback()
            print(f"学習保存エラー: {e}")

    def _query_db_by_name(self, name_query: str) -> Optional[BankMaster]:
        """DBへの実際のクエリ実行部 (名称検索 - 部分一致含む)"""
        try:
            # 1. 完全一致トライ
            stmt = select(BankMaster).where(BankMaster.bank_name == name_query)
            result = self.db.execute(stmt).scalars().first()
            if result: return result

            # 2. 含む検索
            stmt = select(BankMaster).where(
                BankMaster.bank_name.contains(name_query)
            )
            result = self.db.execute(stmt).scalars().first()
            return result
        except Exception as e:
            print(f"DB検索エラー: {e}")
            return None

    def rename_and_move_file(self, original_path: str, extracted_text: str) -> Tuple[bool, str]:
        """
        ファイルの内容に基づいてファイル名を変更し、保存する。
        【修正】常に「残高証明書」として保存します。
        """
        try:
            if not os.path.exists(original_path):
                return False, "元のファイルが見つかりません。"

            directory = os.path.dirname(original_path)
            filename = os.path.basename(original_path)
            name_without_ext, ext = os.path.splitext(filename)

            # 【修正箇所】文言判定を廃止し、一律で「残高証明書」を使用
            suffix = "残高証明書"

            # 新しいファイル名の生成
            # 例: original.pdf -> original_残高証明書.pdf
            new_filename = f"{name_without_ext}_{suffix}{ext}"
            new_path = os.path.join(directory, new_filename)

            # 名前の衝突回避
            counter = 1
            while os.path.exists(new_path):
                new_filename = f"{name_without_ext}_{suffix}_{counter}{ext}"
                new_path = os.path.join(directory, new_filename)
                counter += 1

            shutil.move(original_path, new_path)
            
            return True, new_path

        except Exception as e:
            return False, f"ファイルリネーム中にエラーが発生しました: {str(e)}"