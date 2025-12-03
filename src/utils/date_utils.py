# src/utils/date_utils.py
from datetime import date, datetime
from typing import Optional

from flet import Colors, ControlEvent, Text, TextField


def parse_all_flexible_date(date_str: Optional[str]) -> Optional[date]:
    """
    様々な形式の文字列（YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD等）を日付オブジェクトに変換する。
    変換できない場合は ValueError を送出する。
    """
    if not date_str:
        return None
    
    date_str = date_str.strip().replace("／", "/").replace("－", "-").replace("．", ".")
    
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%Y%m%d",
        "%Y-%m-%dT%H:%M:%S",  # ISO format
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
            
    # 全て失敗した場合
    raise ValueError(f"Invalid date format: {date_str}")


def convert_seireki_to_wareki(date_obj: Optional[date]) -> str:
    """西暦の日付オブジェクトを和暦文字列に変換する"""
    if not date_obj:
        return ""

    y, m, d = date_obj.year, date_obj.month, date_obj.day

    # 令和 (Reiwa): 2019-05-01 から
    if y > 2019 or (y == 2019 and m >= 5 and d >= 1):
        gengo = "令和"
        wareki_year = y - 2018
    # 平成 (Heisei): 1989-01-08 から
    elif y > 1989 or (y == 1989 and m >= 1 and d >= 8):
        gengo = "平成"
        wareki_year = y - 1988
    # 昭和 (Showa): 1926-12-25 から
    elif y > 1926 or (y == 1926 and m >= 12 and d >= 25):
        gengo = "昭和"
        wareki_year = y - 1925
    # 大正 (Taisho): 1912-07-30 から
    elif y > 1912 or (y == 1912 and m >= 7 and d >= 30):
        gengo = "大正"
        wareki_year = y - 1911
    # 明治 (Meiji): 1868-01-25 から
    elif y > 1868 or (y == 1868 and m >= 1 and d >= 25):
        gengo = "明治"
        wareki_year = y - 1867
    else:
        # 範囲外の場合は西暦をそのまま返す
        return date_obj.isoformat()

    wareki_year_str = "元年" if wareki_year == 1 else f"{wareki_year}年"
    return f"{gengo}{wareki_year_str}{m}月{d}日"


def on_date_blur_handler(e: ControlEvent, wareki_text: Text) -> None:
    """
    TextFieldがフォーカスを失ったときに実行されるハンドラー。
    入力された値を正規化し、和暦表示を更新する。
    """
    textfield: TextField = e.control
    input_value = textfield.value.strip() if textfield.value else ""
    wareki_text.value = ""

    if not input_value:
        textfield.error_text = None
        wareki_text.update()
        textfield.update()
        return

    try:
        # 柔軟な解析関数で日付オブジェクトを取得
        validated_date = parse_all_flexible_date(input_value)

        if validated_date:
            # YYYY-MM-DD 形式にフォーマットし直し、TextFieldの値を更新
            textfield.value = validated_date.isoformat()
            textfield.error_text = None  # エラーメッセージをクリア

            # 和暦に変換してTEXTコントロールを更新
            wareki_text.value = convert_seireki_to_wareki(validated_date)
            wareki_text.color = Colors.BLUE_GREY_600

    except ValueError:
        # 解析に失敗した場合
        textfield.error_text = "無効な日付形式です"
        wareki_text.value = "変換不可"
        wareki_text.color = Colors.RED_400

    wareki_text.update()  # Textコントロールを更新
    textfield.update()    # TextFieldの見た目を更新