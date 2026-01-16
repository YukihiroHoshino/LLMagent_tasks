import os
import pandas as pd
import glob

def aggregate_experiment_results(root_folder_name="01_GPT", output_csv_name="experiment_results_summary.csv"):
    aggregated_data = []

    if not os.path.exists(root_folder_name):
        print(f"エラー: '{root_folder_name}' フォルダが見つかりません。")
        return

    exp_folders = [f for f in os.listdir(root_folder_name) if os.path.isdir(os.path.join(root_folder_name, f))]
    print(f"処理対象フォルダ数: {len(exp_folders)}")

    for folder in exp_folders:
        folder_path = os.path.join(root_folder_name, folder)
        
        # --- 1. フォルダ名からメタデータを抽出 ---
        parts = folder.split('_')
        if len(parts) < 4:
            continue

        # ID抽出 (exp4111 -> 4111)
        exp_id_str = parts[0]
        exp_id = exp_id_str[3:] if exp_id_str.startswith("exp") else exp_id_str
        
        scenario = parts[1]

        # Environment と Number の抽出
        if exp_id.startswith('6'):
            # IDが6系は Environment が2単語 (例: free_active)
            environment = f"{parts[2]}_{parts[3]}"
            number = parts[4]
        else:
            # それ以外は Environment が1単語 (例: DA)
            environment = parts[2]
            number = parts[3]

        # --- 2. 最新のsummary csvファイルを特定 ---
        output_dir = os.path.join(folder_path, 'output')
        if not os.path.exists(output_dir):
            continue

        # "summary" が含まれるcsvファイルを探す
        # (experiment_...summary.csv も 2026...summary.csv もヒットします)
        csv_files = glob.glob(os.path.join(output_dir, "*summary*.csv"))
        
        if not csv_files:
            print(f"スキップ: summaryを含むcsvが見つかりません ({folder})")
            continue

        # 名前順でソートして最新（最後）のファイルを取得
        latest_csv_path = sorted(csv_files)[-1]
        
        # --- 3. CSVの中身を読み込んで値を抽出 ---
        try:
            df = pd.read_csv(latest_csv_path)
            
            stability_val = None
            efficiency_val = None
            honesty_val = None

            # === IDが6から始まる場合の処理 (横持ち形式) ===
            if exp_id.startswith('6'):
                # 想定形式: Stability_Rate,Efficiency_Rate,Num_Trials
                # 値は1行目にあると想定
                if not df.empty:
                    # カラム名に空白がある場合に備えてstripする処理を入れることも可能ですが、
                    # 提示された形式(Stability_Rate)に合わせてそのまま取得します
                    if 'Stability_Rate' in df.columns:
                        stability_val = df.iloc[0]['Stability_Rate']
                    
                    if 'Efficiency_Rate' in df.columns:
                        efficiency_val = df.iloc[0]['Efficiency_Rate']
                    
                    # Truth-telling Rateは0固定
                    honesty_val = 0
            
            # === IDがそれ以外の場合の処理 (縦持ち形式) ===
            else:
                # 想定形式: Metric, Value, Description
                df['Metric'] = df['Metric'].astype(str).str.strip()
                
                def get_metric_value(metric_name):
                    row = df[df['Metric'] == metric_name]
                    if not row.empty:
                        return row['Value'].values[0]
                    return None

                stability_val = get_metric_value('Stability Rate')
                efficiency_val = get_metric_value('Efficiency Rate')
                honesty_val = get_metric_value('Avg Honesty Rate')

            # --- 4. データをリストに追加 ---
            aggregated_data.append({
                'ID': exp_id,
                'Scenario': scenario,
                'Environment': environment,
                'Number': number,
                'Stability': stability_val,
                'Efficiency': efficiency_val,
                'Truth-telling Rate': honesty_val
            })

        except Exception as e:
            print(f"エラー: ファイル読み込み中に問題が発生しました ({latest_csv_path}): {e}")

    # --- 5. CSV出力 ---
    if aggregated_data:
        result_df = pd.DataFrame(aggregated_data)
        
        cols_order = [
            'ID', 'Scenario', 'Environment', 'Number', 
            'Stability', 'Efficiency', 'Truth-telling Rate'
        ]
        # カラムが存在することを確認して並べ替え
        cols_order = [c for c in cols_order if c in result_df.columns]
        result_df = result_df[cols_order]
        
        # IDでソート
        result_df = result_df.sort_values(by='ID')

        result_df.to_csv(output_csv_name, index=False)
        print(f"完了: 結果を '{output_csv_name}' に保存しました。")
        print(result_df.head())
    else:
        print("警告: 有効なデータが見つかりませんでした。")

if __name__ == "__main__":
    aggregate_experiment_results()