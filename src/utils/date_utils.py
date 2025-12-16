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
    # 全角英数・記号を半角に、カタカナは全角に(NFKC)
    return unicodedata.normalize("NFKC", text).strip()

def parse_all_flexible_date(date_str: str) -> datetime.date:
    """
    多様な日付フォーマットを解析して date オブジェクトを返す
    
    対応フォーマット:
    - 和暦略称: S50.1.1, H10-5-5, R3/10/10 (M, T, S, H, R 対応)
    - 漢字和暦: 昭和50年1月1日, 令和元年5月1日
    - 西暦: YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
    - 日本語: YYYY年MM月DD日
    - 8桁数値: YYYYMMDD
    - 年省略: MM/DD, MM-DD (現在の年を補完)
    - 年省略日本語: MM月DD日 (現在の年を補完)
    """
    if not date_str:
        raise ValueError("Empty string")
    
    text = normalize_text(date_str)
    
    # 0. 和暦略称 (S50.1.1, H10-10-10, R5/5/5 など)
    # アルファベット + 数字 + 区切り + 数字 + 区切り + 数字
    match_era = re.match(r'^([MTSHRmtshr])(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})$', text)
    if match_era:
        era_char = match_era.group(1).upper()
        era_year = int(match_era.group(2))
        month = int(match_era.group(3))
        day = int(match_era.group(4))

        # 元号の開始年
        base_year = 1900
        if era_char == 'M':   # 明治 (1868-1912)
            base_year = 1868
        elif era_char == 'T': # 大正 (1912-1926)
            base_year = 1912
        elif era_char == 'S': # 昭和 (1926-1989)
            base_year = 1926
        elif era_char == 'H': # 平成 (1989-2019)
            base_year = 1989
        elif era_char == 'R': # 令和 (2019-)
            base_year = 2019
        
        # 西暦変換: 元号開始年 + 年数 - 1
        year = base_year + era_year - 1
        return datetime.date(year, month, day)

    # 💡 追加: 漢字和暦 (昭和50年1月1日, 令和元年5月1日)
    match_kanji_era = re.match(r'^(明治|大正|昭和|平成|令和)(\d{1,2}|元)年(\d{1,2})月(\d{1,2})日$', text)
    if match_kanji_era:
        era_name = match_kanji_era.group(1)
        era_year_str = match_kanji_era.group(2)
        month = int(match_kanji_era.group(3))
        day = int(match_kanji_era.group(4))

        if era_year_str == "元":
            era_year = 1
        else:
            era_year = int(era_year_str)

        base_year = 1900
        if era_name == '明治': base_year = 1868
        elif era_name == '大正': base_year = 1912
        elif era_name == '昭和': base_year = 1926
        elif era_name == '平成': base_year = 1989
        elif era_name == '令和': base_year = 2019
        
        year = base_year + era_year - 1
        return datetime.date(year, month, day)

    # 1. YYYY年MM月DD日
    match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
    if match:
        return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    # 2. YYYY/MM/DD, YYYY-MM-DD, YYYY.MM.DD (区切り文字混在対応)
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
        # 解析実行
        d = parse_all_flexible_date(val)
        
        # 成功したらYYYY-MM-DD形式で上書き
        control.value = d.isoformat()
        control.error_text = None
        
        # 和暦表示の更新
        if wareki_text_control:
            wareki_text_control.value = convert_seireki_to_wareki(d)
            wareki_text_control.update()
            
    except ValueError:
        # 解析不能な場合はエラーメッセージなどは出さず、入力値をそのままにする
        # または、必要に応じてユーザーに通知する形でも良い
        pass
    
    control.update()