import os
import re
from pathlib import Path

def update_experiment_files(start_id, end_id):
    base_dir = Path(__file__).parent.absolute()
    
    # expで始まるフォルダを抽出
    exp_folders = sorted([f for f in os.listdir(base_dir) if f.startswith("exp") and os.path.isdir(base_dir / f)])

    for folder_name in exp_folders:
        try:
            # フォルダ名の数値部分を判定 (例: exp6111_... -> 6111)
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
            
            # ① OpenAIクライアント初期化部分の変更
            content = content.replace(
                'client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))',
                'client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")'
            )
            
            # ② デフォルトモデルの引数変更
            content = content.replace(
                'def get_llm_response(system_prompt: str, user_prompt: str, model: str = "meta-llama-3.1-8b-instruct", temperature: float = 0.7) -> dict:',
                'def get_llm_response(system_prompt: str, user_prompt: str, model: str = "MODEL_NAME", temperature: float = 0.7) -> dict:'
            )
            
            # ③ response_format の行を削除（改行やインデントも含めて綺麗に除去）
            content = re.sub(r'\n\s*response_format\s*=\s*\{\s*"type"\s*:\s*"json_object"\s*\},?', '', content)
            
            # ファイルに書き戻す
            client_py.write_text(content, encoding='utf-8')
            print(f"  - Updated llm_client.py")
        else:
            print(f"  - Skipped: llm_client.py not found")

if __name__ == "__main__":
    # 指定された範囲
    START = 6111
    END = 6325
    
    update_experiment_files(START, END)
    print("\n✅ All files updated successfully.")