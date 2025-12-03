from flet import Colors, Theme, ThemeMode, VisualDensity

# テーマ設定を関数にしておく
app_theme = Theme(
    color_scheme_seed=Colors.TEAL,  # ここを変えるだけで全画面変わる
    visual_density=VisualDensity.COMFORTABLE,  # 余白の広さ設定
)


# default_mode = ThemeMode.SYSTEM
default_mode = ThemeMode.DARK
