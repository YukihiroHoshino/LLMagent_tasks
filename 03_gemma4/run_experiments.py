import os
import subprocess
from pathlib import Path

def run_experiments(start_id, end_id):
    # 02_LLAMA フォルダのパスを取得
    base_dir = Path(__file__).parent.absolute()
    
    # 02_LLAMA 内のフォルダを取得してソート
    # expで始まるフォルダのみ抽出
    exp_folders = sorted([f for f in os.listdir(base_dir) if f.startswith("exp") and os.path.isdir(os.path.join(base_dir, f))])
    
    for folder_name in exp_folders:
        # フォルダ名から数値部分を抽出 (例: exp4111 -> 4111)
        try:
            exp_num = int(folder_name.replace("exp", "").split("_")[0])
        except ValueError:
            continue

        # 指定範囲外ならスキップ
        if not (start_id <= exp_num <= end_id):
            continue

        exp_path = base_dir / folder_name
        main_py = exp_path / "src" / "main.py"

        if main_py.exists():
            print(f"\n{'='*50}")
            print(f"🚀 Starting: {folder_name}")
            print(f"{'='*50}")

            try:
                # cwd(current working directory)を指定することで、
                # そのフォルダの中で実行しているのと同じ状態を作り出す
                result = subprocess.run(
                    ["python", "src/main.py"],
                    cwd=exp_path,  # ここがポイント：フォルダを移動して実行
                    check=True     # エラーが出たら停止（必要に応じてFalseに）
                )
                print(f"✅ Finished: {folder_name}")
            except subprocess.CalledProcessError as e:
                print(f"❌ Error in {folder_name}: {e}")
        else:
            print(f"⚠️ Skipped: {folder_name} (src/main.py not found)")

if __name__ == "__main__":
    # 実験の範囲を指定して実行
    START = 4332
    END = 4332
    run_experiments(START, END)