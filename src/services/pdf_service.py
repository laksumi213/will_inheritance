# src/services/pdf_service.py
from pathlib import Path
from typing import List

from src.models.database import SessionLocal
from src.models.tables import Coordinate
from src.utils.pdf_writer import PdfWriter


class PdfService:
    """
    PDF生成および座標データ管理に関するビジネスロジック
    """

    def __init__(self):
        # プロジェクトルートからの相対パスでフォントを指定
        base_dir = Path(__file__).parent.parent.parent  # src/services/ -> root
        self.font_path = str(base_dir / "assets" / "fonts" / "ipaexg.ttf")
        self.writer = PdfWriter(self.font_path)

        # 出力ディレクトリの作成
        self.output_dir = base_dir / "output"
        self.output_dir.mkdir(exist_ok=True)

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

    def generate_preview_pdf(self, filename: str = "preview.pdf") -> str:
        """
        現在のDBデータを使ってPDFを生成する

        Returns:
            str: 生成されたファイルのフルパス
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

        output_path = str(self.output_dir / filename)

        try:
            self.writer.create_overlay_pdf(output_path, draw_data)
            return output_path
        except Exception as e:
            raise e


# シングルトン
pdf_service = PdfService()
