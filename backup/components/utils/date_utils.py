# /components/utils/date_utils.py

from datetime import date

from flet import Text  # on_date_blur_handler で使用

from services.deceased_service import parse_all_flexible_date  # 💡 依存関係を明示


def convert_seireki_to_wareki(date_obj: date) -> str:
    """西暦の日付オブジェクトを和暦文字列に変換する"""
    if not date_obj:
        return ""

    y, m, d = date_obj.year, date_obj.month, date_obj.day
    # 令和 (Reiwa)
    if y > 2019 or (y == 2019 and m >= 5 and d >= 1):
        gengo = "令和"
        wareki_year = y - 2018
    # 平成 (Heisei)
    elif y > 1989 or (y == 1989 and m >= 1 and d >= 8):
        gengo = "平成"
        wareki_year = y - 1988
    # 昭和 (Showa)
    elif y > 1926 or (y == 1926 and m >= 12 and d >= 25):
        gengo = "昭和"
        wareki_year = y - 1925
    # 大正 (Taisho)
    elif y > 1912 or (y == 1912 and m >= 7 and d >= 30):
        gengo = "大正"
        wareki_year = y - 1911
    else:
        return date_obj.isoformat()

    wareki_year_str = "元年" if wareki_year == 1 else str(wareki_year) + "年"
    return f"{gengo}{wareki_year_str}{m}月{d}日"


def on_date_blur_handler(e, wareki_text: Text):
    """TextFieldがフォーカスを失ったときに実行されるハンドラー。和暦表示を更新する"""
    input_value = e.control.value
    wareki_text.value = ""

    if not input_value:
        e.control.error_text = None
        wareki_text.update()
        e.control.update()
        return

    try:
        validated_date = parse_all_flexible_date(input_value)
        e.control.value = validated_date.isoformat()
        e.control.error_text = None
        wareki_text.value = convert_seireki_to_wareki(validated_date)

    except ValueError:
        e.control.error_text = "無効な日付形式です"
        wareki_text.value = ""

    wareki_text.update()
    e.control.update()


# 💡 これで、日付に関するロジックが全て一箇所に集約されます。
