import os

# まとめる対象の拡張子
TARGET_EXTENSIONS = {'.py', '.sql', '.json'}
# 無視するフォルダ
IGNORE_DIRS = {'__pycache__', '.git', '.venv', 'venv', 'idea', '.vscode'}
# 出力ファイル名
OUTPUT_FILE = 'all_code_context.txt'

def combine_files():
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        # ディレクトリを走査
        for root, dirs, files in os.walk("."):
            # 無視リストにあるフォルダを除外
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in TARGET_EXTENSIONS and file != os.path.basename(__file__):
                    file_path = os.path.join(root, file)
                    
                    # ファイルの区切りとパスを書き込み
                    outfile.write(f"\n{'='*50}\n")
                    outfile.write(f"FILE_PATH: {file_path}\n")
                    outfile.write(f"{'='*50}\n\n")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            outfile.write(infile.read())
                            outfile.write("\n")
                    except Exception as e:
                        outfile.write(f"Error reading file: {e}\n")

    print(f"完了しました！ '{OUTPUT_FILE}' をGeminiにアップロードしてください。")

if __name__ == "__main__":
    combine_files()