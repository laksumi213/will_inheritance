import os

# まとめる対象の拡張子 (ソースコードのみ)
# TARGET_EXTENSIONS = {".py", ".sql", ".json", ".md", ".txt", ".html", ".css", ".js"}
TARGET_EXTENSIONS = {".py"}

# 無視するフォルダ (完全一致)
IGNORE_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "idea",
    ".vscode",
    ".idea",
    "build",
    "dist",
    "node_modules",
    "assets",  # 画像などのリソースフォルダも除外推奨
    "generated_pdfs",  # 生成物も除外
    "backup",
    "assets",
    "data",
    "output",
}

# 無視するファイル名（完全一致）
IGNORE_FILES = {
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    ".DS_Store",
    "tempCodeRunnerFile.py",
    "point_get.py",
    "all_code_context.txt",  # 自分自身を含めない
    "migrate_project.py",
}

# ★追加: 無視するファイル名に含まれるキーワード（部分一致）
# ファイル名にこれらの文字が含まれていたら無視します
IGNORE_KEYWORDS = {
    "test",  # test_xxx.py や xxx_test.py などを無視
    "custom_",
}

# 出力ファイル名
OUTPUT_FILE = "all_code_context.txt"

# 最大ファイルサイズ (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024


def combine_files():
    current_size = 0
    file_count = 0

    # 既存の出力ファイルがあれば削除
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
        # ディレクトリを走査
        for root, dirs, files in os.walk("."):
            # 無視リストにあるフォルダを除外 (in-place modification)
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                # 1. 完全一致で無視
                if file in IGNORE_FILES:
                    continue

                # 2. ★追加: キーワードが含まれていたら無視 (部分一致)
                if any(keyword in file for keyword in IGNORE_KEYWORDS):
                    continue

                ext = os.path.splitext(file)[1]

                # 自身のファイルとターゲット拡張子以外はスキップ
                if file == os.path.basename(__file__) or ext not in TARGET_EXTENSIONS:
                    continue

                file_path = os.path.join(root, file)

                # ファイルサイズチェック
                try:
                    file_size = os.path.getsize(file_path)
                    if current_size + file_size > MAX_FILE_SIZE:
                        outfile.write(
                            "\n\n# --- WARNING: Max file size (100MB) reached. Stopping here. ---\n"
                        )
                        print("⚠️ サイズ制限(100MB)に達したため、処理を中断しました。")
                        return
                except OSError:
                    continue

                # ファイルの区切りとパスを書き込み
                header = f"\n{'=' * 50}\nFILE_PATH: {file_path}\n{'=' * 50}\n\n"
                outfile.write(header)
                current_size += len(header.encode("utf-8"))

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as infile:
                        content = infile.read()
                        outfile.write(content)
                        outfile.write("\n")
                        current_size += len(content.encode("utf-8")) + 1
                        file_count += 1
                except Exception as e:
                    error_msg = f"Error reading file: {e}\n"
                    outfile.write(error_msg)
                    current_size += len(error_msg.encode("utf-8"))

    print("✅ 完了しました！")
    print(f"出力ファイル: {OUTPUT_FILE}")
    print(f"合計ファイル数: {file_count}")
    print(f"合計サイズ: {current_size / (1024 * 1024):.2f} MB")
    print("このファイルをGeminiにアップロードしてください。")


if __name__ == "__main__":
    combine_files()
