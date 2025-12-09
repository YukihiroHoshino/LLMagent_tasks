import os
import sys
from dotenv import load_dotenv

# --- パス設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, '.env')

# .env ロード
loaded = load_dotenv(dotenv_path)

# srcパス追加
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.utils import load_json, save_match_results
from src.environment import Environment

def main():
    # --- デバッグ: APIキーの確認 ---
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not loaded:
        print(f"Warning: .env file was not found at {dotenv_path}")
    
    if not api_key:
        print("CRITICAL ERROR: 'OPENAI_API_KEY' not found. Please check your .env file.")
        print(f"Current looking in: {dotenv_path}")
        return

    # キーが読み込めているか確認（セキュリティのため一部だけ表示）
    print(f"API Key loaded successfully: {api_key[:8]}...")

    # ディレクトリ設定
    input_dir = os.path.join(BASE_DIR, 'data', 'input')
    output_dir = os.path.join(BASE_DIR, 'data', 'output')
    
    personas_path = os.path.join(input_dir, 'personas.json')
    prefs_path = os.path.join(input_dir, 'preferences.json')
    
    if not os.path.exists(personas_path) or not os.path.exists(prefs_path):
        print(f"Error: Input files not found in {input_dir}")
        return

    print(f"Loading data from {input_dir}...")
    personas = load_json(personas_path)
    prefs = load_json(prefs_path)

    # Environment に api_key を渡す
    env = Environment(personas, prefs, output_dir=output_dir, api_key=api_key)
    
    results = env.run_simulation()
    
    print(f"Saving results to {output_dir}...")
    match_results_path = os.path.join(output_dir, 'match_results.csv')
    save_match_results(results, match_results_path)
    print("Done!")

if __name__ == "__main__":
    main()