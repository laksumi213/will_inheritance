# src/services/user_management_service.py
from typing import Dict, List, Optional

from src.models.database import SessionLocal
from src.models.tables import User


class UserManagementService:
    """
    ユーザー認証・管理に関するサービスロジック
    """

    def authenticate(self, windows_id: str) -> Optional[User]:
        """
        簡易認証: Windows IDに基づいてユーザーを取得する
        実際にはActive Directory連携やパスワード照合を行う
        """
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.windows_id == windows_id).first()
            if user:
                print(f"User authenticated: {user.name} ({user.role})")
                return user
            else:
                print(f"Authentication failed for: {windows_id}")
                return None
        finally:
            db.close()

    def get_all_managers(self) -> List[Dict[str, str]]:
        """Managerロールを持つユーザーのリストを取得"""
        db = SessionLocal()
        try:
            managers = db.query(User).filter(User.role == "Manager").all()
            return [{"id": u.id, "name": u.name} for u in managers]
        finally:
            db.close()

    def get_all_operators(self) -> List[Dict[str, str]]:
        """Operatorロールを持つユーザーのリストを取得"""
        db = SessionLocal()
        try:
            operators = db.query(User).filter(User.role == "Operator").all()
            return [{"id": u.id, "name": u.name} for u in operators]
        finally:
            db.close()

    def create_user(self, windows_id: str, name: str, role: str = "Operator") -> bool:
        """新規ユーザーを作成する"""
        db = SessionLocal()
        try:
            if db.query(User).filter(User.windows_id == windows_id).first():
                print("User already exists.")
                return False

            new_user = User(windows_id=windows_id, name=name, role=role)
            db.add(new_user)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Failed to create user: {e}")
            return False
        finally:
            db.close()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """IDからユーザー情報を取得（セッションはデタッチされるため注意）"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                # 必要な属性をアクセスしてロードしておくか、辞書で返すのが安全
                return user
            return None
        finally:
            db.close()


# シングルトンインスタンス
user_service = UserManagementService()
