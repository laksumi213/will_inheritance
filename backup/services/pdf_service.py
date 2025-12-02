# services/pdf_service.py
import os
from typing import List

from models.coordinate import Coordinate, SessionLocal
from utils.pdf_writer import PdfWriter


class PdfService:
    """
    PDF生成および座標データ管理に関するビジネスロジック
    """

    def __init__(self):
        # フォントパスは環境に合わせて調整（assetsフォルダを想定）
        self.font_path = os.path.join("assets", "fonts", "ipaexg.ttf")
        self.writer = PdfWriter(self.font_path)

    def get_all_coordinates(self) -> List[Coordinate]:
        """保存されている全ての座標データを取得"""
        session = SessionLocal()
        try:
            return session.query(Coordinate).all()
        finally:
            session.close()

    def add_coordinate(self, label: str, x: float, y: float, value: str = "") -> None:
        """座標データをDBに追加"""
        session = SessionLocal()
        try:
            new_coord = Coordinate(label=label, x_point=x, y_point=y, value=value)
            session.add(new_coord)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def delete_coordinate(self, coord_id: int) -> None:
        """指定IDの座標データを削除"""
        session = SessionLocal()
        try:
            target = session.query(Coordinate).filter(Coordinate.id == coord_id).first()
            if target:
                session.delete(target)
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def generate_preview_pdf(self, output_path: str) -> str:
        """
        現在のDBデータを使ってPDFを生成する

        Returns:
            str: 生成されたファイルのパス
        """
        coords = self.get_all_coordinates()

        # utils用のデータ形式に変換
        draw_data = []
        for c in coords:
            draw_data.append(
                {
                    "x": c.x_point,
                    "y": c.y_point,
                    "value": c.value if c.value else c.label,  # 値がない場合はラベルを表示
                }
            )

        try:
            self.writer.create_overlay_pdf(output_path, draw_data)
            return output_path
        except Exception as e:
            raise e
