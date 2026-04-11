import os
import re
from pathlib import Path

def update_experiment_files(start_id, end_id):
    base_dir = Path(__file__).parent.absolute()
    
    # expで始まるフォルダを抽出
    exp_folders = sorted([f for f in os.listdir(base_dir) if f.startswith("exp") and os.path.isdir(base_dir / f)])

    for folder_name in exp_folders:
        try:
            # フォルダ名の数値部分を判定 (例: exp4111_... -> 4111)
            exp_num = int(re.search(r'exp(\d+)', folder_name).group(1))
        except (ValueError, AttributeError):
            continue

        if not (start_id <= exp_num <= end_id):
            continue

        print(f"🛠 Updating: {folder_name}")

        # 1. llm_client.py の修正
        client_py = base_dir / folder_name / "src" / "llm_client.py"
        if client_py.exists():
            content = client_py.read_text(encoding='utf-8')
            
            # --- __init__ のモデル名変更 ---
            content = content.replace(
                'def __init__(self, model="google/gemma-4-e4b", temperature=0.7):',
                'def __init__(self, model="MODEL_NAME", temperature=0.7):'
            )

            # --- system_prompt の変更 ---
            content = content.replace(
                'system_prompt = "JSON only"',
                'system_prompt = "Output JSON only"'
            )

            # --- response_format の削除 ---
            # [ \t]* で行頭・行末のスペース(インデント)のみをキャッチし、改行(\n)を1つだけ消すことで
            # 次の行(temperature=...)が消えたりインデントが崩れたりするのを防ぎます
            content = re.sub(r'[ \t]*response_format\s*=\s*\{\s*"type"\s*:\s*"json_object"\s*\},[ \t]*\n?', '', content)

            client_py.write_text(content, encoding='utf-8')
            print(f"  - Updated llm_client.py")

        # 2. main.py の修正
        main_py = base_dir / folder_name / "src" / "main.py"
        if main_py.exists():
            content = main_py.read_text(encoding='utf-8')
            
            # --- AgentSimulator のモデル名変更 ---
            content = content.replace(
                'simulator = AgentSimulator(model="google/gemma-4-e4b", temperature=0.7)',
                'simulator = AgentSimulator(model="MODEL_NAME", temperature=0.7)'
            )
            
            main_py.write_text(content, encoding='utf-8')
            print(f"  - Updated main.py")

if __name__ == "__main__":
    # 指定された範囲
    START = 4111
    END = 4355
    
    update_experiment_files(START, END)
    print("\n✅ All files updated successfully.")