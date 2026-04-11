import json
import re
from pathlib import Path

def fix_quota_files(base_directory="."):
    base_path = Path(base_directory)
    
    # 差し替えるためのデータ
    data_school = {
        "School_A": 1,
        "School_B": 1,
        "School_C": 1,
        "School_D": 1,
        "School_E": 1
    }
    
    data_nursery = {
        "Nursery_A": 1,
        "Nursery_B": 1,
        "Nursery_C": 1,
        "Nursery_D": 1,
        "Nursery_E": 1
    }

    # base_directory内のすべてのフォルダをチェック
    for folder in base_path.iterdir():
        if not folder.is_dir():
            continue
            
        # フォルダ名から「exp + 4桁の数字」を抽出
        # 例: "exp4211_school_DA_5v5_pref1" -> "4211"
        match = re.search(r'exp(\d{4})', folder.name)
        if not match:
            continue # exp+4桁の数字が含まれないフォルダはスキップ

        exp_num_str = match.group(1) # "4211"などの文字列
        exp_num = int(exp_num_str)

        # 抽出した数字が対象範囲(4111〜6325)か確認
        if not (4111 <= exp_num <= 6325):
            continue

        # 4桁の数字の上から2桁目（インデックス1）を取得
        second_digit = exp_num_str[1]

        # 2文字目に応じて書き換えるデータを決定
        if second_digit == '2':
            new_data = data_school
        elif second_digit == '3':
            new_data = data_nursery
        else:
            # 2でも3でもない場合は変更せずスキップ
            continue

        # 対象となる quota.json のパスを構築
        json_file = folder / "data" / "quota.json"

        # 該当のファイルが存在しない場合はスキップ
        if not json_file.is_file():
            print(f"⚠️ スキップ (ファイルなし): {json_file}")
            continue

        # ファイルの上書き実行
        try:
            with json_file.open('w', encoding='utf-8') as f:
                json.dump(new_data, f, indent=2, ensure_ascii=False)
            print(f"✅ 更新しました: {json_file}")
        except Exception as e:
            print(f"❌ エラーが発生しました ({json_file}): {e}")

if __name__ == "__main__":
    # このスクリプトを「exp...」フォルダがずらりと並んでいる親ディレクトリに置いて実行してください
    fix_quota_files(".")