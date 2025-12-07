# models/coordinate.py
from dataclasses import dataclass
from typing import Literal


@dataclass
class Coordinate:
    """
    画面上の操作ログおよび描画情報を保持するデータクラス
    """

    id: int  # 識別用ID
    page_number: int  # ページ番号 (1始まり)
    type: Literal["text", "rect", "circle", "check"]  # 描画タイプ

    # 座標情報 (実寸: PDF上のピクセル / UI: 画面上のピクセル)
    ui_x: float
    ui_y: float
    real_x: int
    real_y: int

    # 矩形用 (Width/Height)
    real_w: int = 0
    real_h: int = 0

    # テキスト/設定用
    text: str = ""
    font_size: int = 11

    def __str__(self) -> str:
        base = f"P{self.page_number} [{self.type.upper()}]"
        if self.type == "rect":
            return f"{base} Pos({self.real_x},{self.real_y}) Size({self.real_w}x{self.real_h})"
        elif self.type == "text":
            content = self.text if self.text else "..."
            return f"{base} ({self.real_x},{self.real_y}) Size:{self.font_size}pt '{content}'"
        else:
            return f"{base} ({self.real_x},{self.real_y})"
