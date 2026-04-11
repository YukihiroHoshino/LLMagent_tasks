import os
import re
from pathlib import Path

def apply_template_changes():
    base_dir = Path(__file__).parent.absolute()
    
    # expで始まるフォルダを抽出
    exp_folders = sorted([f for f in os.listdir(base_dir) if f.startswith("exp") and os.path.isdir(base_dir / f)])

    for folder_name in exp_folders:
        try:
            # フォルダ名の数値部分を抽出
            exp_num = int(re.search(r'exp(\d+)', folder_name).group(1))
        except (ValueError, AttributeError):
            continue

        # 実験番号がどの範囲に属するかを判定
        is_range_1 = 4111 <= exp_num <= 4355
        is_range_2 = 6111 <= exp_num <= 6325

        # どちらの範囲にも該当しない場合はスキップ
        if not (is_range_1 or is_range_2):
            continue

        print(f"🛠 Updating: {folder_name}")

        # ---------------------------------------------------------
        # 1. llm_client.py の修正 (両方の範囲で実行)
        # ---------------------------------------------------------
        client_py = base_dir / folder_name / "src" / "llm_client.py"
        if client_py.exists():
            content = client_py.read_text(encoding='utf-8')
            
            # MODEL_NAME を置換
            if 'MODEL_NAME' in content:
                content = content.replace('BEFORE_MODEL_NAME', 'AFTER_MODEL_NAME')
                client_py.write_text(content, encoding='utf-8')
                print(f"  - Updated llm_client.py")

        # ---------------------------------------------------------
        # 2. main.py の修正 (4111〜4355の範囲のみ実行)
        # ---------------------------------------------------------
        if is_range_1:
            main_py = base_dir / folder_name / "src" / "main.py"
            if main_py.exists():
                content = main_py.read_text(encoding='utf-8')
                
                # MODEL_NAME を置換
                if 'MODEL_NAME' in content:
                    content = content.replace('BEFORE_MODEL_NAME', 'AFTER_MODEL_NAME')
                    main_py.write_text(content, encoding='utf-8')
                    print(f"  - Updated main.py")

if __name__ == "__main__":
    apply_template_changes()
    print("\n✅ Template edits applied successfully.")