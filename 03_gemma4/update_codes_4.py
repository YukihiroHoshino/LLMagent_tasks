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
            
            # 置換対象のパターン（OpenAIクライアント初期化部分）
            # インデントを保持しつつ書き換えます
            old_init = r'def __init__\(self,\s*model="google/gemma-4-e4b",\s*temperature=0\.7\):\s*self\.client = OpenAI\(\s*base_url="http://127.0.0.1:1234/v1",\s*api_key="lm-studio"\s*\)'
            
            new_init = (
                'def __init__(self, model="meta-llama-3.1-8b-instruct", temperature=0.7):\n'
                '        self.client = OpenAI(\n'
                '            base_url="http://127.0.0.1:1234/v1",\n'
                '            api_key="lm-studio"\n'
                '        )'
            )
            
            new_content = re.sub(old_init, new_init, content)
            client_py.write_text(new_content, encoding='utf-8')
            print(f"  - Updated llm_client.py")
        
        # 1.5 llm_client.py の response_format 削除
        client_py = base_dir / folder_name / "src" / "llm_client.py"
        if client_py.exists():
            content = client_py.read_text(encoding='utf-8')
            
            # 置換対象のパターン（OpenAIクライアント初期化部分）
            # インデントを保持しつつ書き換えます
            old_init = r'response_format={"type": "json_object"},'
            
            new_init = '\n'
            
            new_content = re.sub(old_init, new_init, content)
            client_py.write_text(new_content, encoding='utf-8')
            print(f"  - Updated llm_client.py")

        # 2. main.py の修正
        main_py = base_dir / folder_name / "src" / "main.py"
        if main_py.exists():
            content = main_py.read_text(encoding='utf-8')
            
            # モデル指定部分の置換
            old_sim = r'simulator = AgentSimulator\(model="google/gemma-4-e4b", temperature=0.7\)'
            new_sim = 'simulator = AgentSimulator(model="meta-llama-3.1-8b-instruct", temperature=0.7)'
            
            new_content = re.sub(old_sim, new_sim, content)
            main_py.write_text(new_content, encoding='utf-8')
            print(f"  - Updated main.py")

if __name__ == "__main__":
    # 指定された範囲
    START = 4111
    END = 4355
    
    update_experiment_files(START, END)
    print("\n✅ All files updated successfully.")