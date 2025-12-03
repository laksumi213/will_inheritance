# migrate_project.py
import os
import shutil
import re
from pathlib import Path

# --- 設定: プロジェクトのルートディレクトリ ---
# このスクリプトがプロジェクトルートにあると仮定
BASE_DIR = Path(__file__).parent

# --- 設定: 移動ルールの定義 ---
# (元のパスパターン, 新しい保存先ディレクトリ)
MOVE_RULES = [
    # 1. 画面 (Views)
    ("components/pages/*.py", "src/views"),
    ("views/*.py", "src/views"),
    
    # 2. ビジネスロジック (Services)
    ("services/*.py", "src/services"),
    
    # 3. ユーティリティ (Utils) - pdf_createなど
    ("components/utils/pdf_create.py", "src/utils"),
    ("components/utils/pdf_writer.py", "src/utils"),
    ("components/utils/date_utils.py", "src/utils"),
    ("components/utils/file_system.py", "src/utils"),
    ("components/utils/ui_utils.py", "src/utils"),
    ("components/utils/web_operation.py", "src/utils"),
    
    # 4. コンポーネント (Components) - ビジネスロジック寄り
    ("components/utils/contact_controls.py", "src/components/business"),
    
    # 5. コンポーネント (Components) - 汎用UIなど
    # もし他にも汎用的なボタンなどがあればここに定義
    # ("components/common/*.py", "src/components/common"),
]

# --- 設定: インポート修正ルール (正規表現) ---
# 上から順に適用されます
IMPORT_REPLACEMENTS = [
    # components.pages -> src.views
    (r"from components\.pages", "from src.views"),
    
    # components.utils.contact_controls -> src.components.business.contact_controls
    (r"from components\.utils\.contact_controls", "from src.components.business.contact_controls"),
    
    # components.utils -> src.utils (上記以外)
    (r"from components\.utils", "from src.utils"),
    
    # services -> src.services
    (r"from services", "from src.services"),
    
    # views -> src.views
    (r"from views", "from src.views"),
    
    # components (汎用) -> src.components
    (r"from components", "from src.components"),
]

def ensure_dir(path: Path):
    """ディレクトリが存在しない場合は作成する"""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)

def fix_imports(content: str) -> str:
    """インポートパスを修正する"""
    new_content = content
    for pattern, replacement in IMPORT_REPLACEMENTS:
        new_content = re.sub(pattern, replacement, new_content)
    return new_content

def process_file(source_path: Path, dest_dir: Path):
    """ファイルを読み込み、修正を加えて新しい場所に保存する"""
    try:
        if not source_path.exists():
            print(f"⚠️  スキップ: ファイルが見つかりません: {source_path}")
            return

        # 宛先パスの構築
        dest_path = dest_dir / source_path.name
        ensure_dir(dest_dir)

        # Pythonファイルのみテキスト処理を行う
        if source_path.suffix == ".py":
            with open(source_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 1. 1行目に元のファイル名をコメントとして追加
            # Windowsのパス区切り文字をスラッシュに統一して見やすくする
            relative_path = source_path.relative_to(BASE_DIR).as_posix()
            header = f"# {relative_path}\n"
            
            # 既に同じヘッダーがある場合は二重に追加しない
            if not content.startswith(header):
                content = header + content

            # 2. インポートパスの修正
            content = fix_imports(content)

            # 3. 新しい場所に書き込み
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            print(f"✅ 移動・修正完了: {source_path.name} -> {dest_path}")

        else:
            # Python以外のファイル（フォントなど）は単純コピー
            shutil.copy2(source_path, dest_path)
            print(f"📦 コピー完了: {source_path.name} -> {dest_path}")

    except Exception as e:
        print(f"❌ エラー ({source_path.name}): {e}")

def main():
    print("🚀 プロジェクト構成の移行を開始します...")
    
    for pattern, dest_str in MOVE_RULES:
        dest_path = BASE_DIR / dest_str
        
        # ワイルドカードを含む場合とそうでない場合で処理を分ける
        if "*" in pattern:
            # globで検索
            files = list(BASE_DIR.glob(pattern))
            if not files:
                print(f"ℹ️  対象なし: {pattern}")
                continue
                
            for source_file in files:
                # 自分自身（移行スクリプト）やvenvなどは除外
                if "migrate_project.py" in source_file.name:
                    continue
                process_file(source_file, dest_path)
        else:
            # 単一ファイル指定
            source_file = BASE_DIR / pattern
            process_file(source_file, dest_path)

    print("\n✨ 移行処理が完了しました。")
    print("⚠️  注意: 元のフォルダ（components, services, views）は安全のため残してあります。")
    print("   'src' フォルダ内の動作を確認した後、手動で削除してください。")

if __name__ == "__main__":
    main()