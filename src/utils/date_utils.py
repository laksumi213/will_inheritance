# src/utils/date_utils.py
import datetime
import re
import unicodedata
from typing import Optional
from flet import Control, Text, TextField

def normalize_text(text: str) -> str:
    """全角英数字を半角に変換し、前後の空白を除去する"""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip()

def parse_all_flexible_date(date_str: str) -> datetime.date:
    """
    多様な日付フォーマットを解析して date オブジェクトを返す
    
    対応フォーマット:
    - YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
    - YYYY年MM月DD日
    - YYYYMMDD
    - MM/DD, MM-DD (現在の年を補完)
    - MM月DD日 (現在の年を補完)
    """
    if not date_str:
        raise ValueError("Empty string")
    
    text = normalize_text(date_str)
    
    # 1. YYYY年MM月DD日
    match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
    if match:
        return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    # 2. YYYY/MM/DD, YYYY-MM-DD, YYYY.MM.DD
    match = re.match(r'(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})', text)
    if match:
        return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    # 3. YYYYMMDD (8桁)
    match = re.match(r'^(\d{4})(\d{2})(\d{2})$', text)
    if match:
        return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    # 4. MM/DD, MM-DD, MM.DD (年省略 -> 現在の年)
    match = re.match(r'^(\d{1,2})[\/\-\.](\d{1,2})$', text)
    if match:
        today = datetime.date.today()
        year = today.year
        month = int(match.group(1))
        day = int(match.group(2))
        return datetime.date(year, month, day)
    
    # 5. MM月DD日 (年省略 -> 現在の年)
    match = re.match(r'^(\d{1,2})月(\d{1,2})日$', text)
    if match:
        today = datetime.date.today()
        year = today.year
        month = int(match.group(1))
        day = int(match.group(2))
        return datetime.date(year, month, day)

    raise ValueError("Invalid date format")

def convert_seireki_to_wareki(date_obj: datetime.date) -> str:
    """西暦(date)を和暦文字列に変換する"""
    if date_obj < datetime.date(1868, 10, 23):
        return "明治以前"
    
    if date_obj < datetime.date(1912, 7, 30):
        y = date_obj.year - 1868 + 1
        era = "明治"
    elif date_obj < datetime.date(1926, 12, 25):
        y = date_obj.year - 1912 + 1
        era = "大正"
    elif date_obj < datetime.date(1989, 1, 8):
        y = date_obj.year - 1926 + 1
        era = "昭和"
    elif date_obj < datetime.date(2019, 5, 1):
        y = date_obj.year - 1989 + 1
        era = "平成"
    else:
        y = date_obj.year - 2019 + 1
        era = "令和"
    
    gannen = "元年" if y == 1 else f"{y}年"
    return f"{era}{gannen}{date_obj.month}月{date_obj.day}日"

def on_date_blur_handler(e, wareki_text_control: Optional[Text] = None) -> None:
    """
    TextFieldのon_blurイベントハンドラ
    入力された日付を解析し、YYYY-MM-DD形式に変換してセットする。
    wareki_text_control が渡されていれば、そこに和暦を表示する。
    """
    control: TextField = e.control
    val = control.value
    
    if not val:
        if wareki_text_control:
            wareki_text_control.value = ""
            wareki_text_control.update()
        control.error_text = None
        control.update()
        return

    try:
        d = parse_all_flexible_date(val)
        control.value = d.isoformat() # YYYY-MM-DD に変換
        control.error_text = None
        
        if wareki_text_control:
            wareki_text_control.value = convert_seireki_to_wareki(d)
            wareki_text_control.update()
            
    except ValueError:
        # 解析不能な場合はエラーメッセージなどは出さず、入力値をそのままにするか
        # 必要に応じて error_text をセットする。今回はUXを考慮しエラー表示せずそのまま。
        pass
    
    control.update()