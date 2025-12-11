# src/models/coordinate.py
from dataclasses import dataclass


@dataclass
class Coordinate:
    """
    画面上の座標情報とPDF上の実座標を管理するデータクラス
    """

    id: int
    page_number: int
    type: str  # "text", "rect", "circle", "check"
    ui_x: float
    ui_y: float
    real_x: int
    real_y: int
    text: str = ""
    font_size: int = 11
    real_w: int = 0
    real_h: int = 0

    def __str__(self) -> str:
        if self.type == "text":
            return f"[P{self.page_number}] Text: ({self.real_x}, {self.real_y}) '{self.text}'"
        elif self.type == "rect":
            return f"[P{self.page_number}] Rect: ({self.real_x}, {self.real_y}) {self.real_w}x{self.real_h}"
        return f"[P{self.page_number}] {self.type}: ({self.real_x}, {self.real_y})"
