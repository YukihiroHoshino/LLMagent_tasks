import pandas as pd
import matplotlib.pyplot as plt
import os

# ファイル読み込み
try:
    df = pd.read_csv('data_analysis_persona/data_formatted/merged_results_high_univ_0.7_wpref.csv')
except FileNotFoundError:
    print("エラー: 'merged_results_high_univ_0.7_wpref.csv' が見つかりません。")
    print("ファイルパスを確認してください。")
    # スクリプトを終了するか、ダミーデータフレームを作成して続行するかを選択できます。
    # ここではエラーを出して終了します。
    exit()


# 各質問と選択肢の定義
question_options = {
    'question_15': [0, 1, 2, 3],
    'question_16': [0, 1],
    'question_17': [0, 1],  # surveyなし
    'question_18': list(range(9)),
}

# 出力ディレクトリの作成
output_dir = 'data_analysis_persona/fig/gender'
os.makedirs(output_dir, exist_ok=True)

# --- ここからが修正箇所 ---

# 性別の定義
genders = {1: 'male', 0: 'female'}

# グラフ出力関数（変更なしだが、呼び出し時に渡す引数を調整）
def plot_question_distribution(question, options, results_data, gender_name, save_dir):
    plt.figure(figsize=(8, 5))
    for label, series in results_data[question].items():
        plt.plot(options, series, marker='o', label=label)
    plt.title(f'{question.upper()} - {gender_name.capitalize()} - Distribution Comparison')
    plt.xlabel('Choice')
    plt.ylabel('Density')
    plt.xticks(options)
    plt.legend()
    plt.grid(True)
    # ファイル名に性別を追加して保存
    save_path = os.path.join(save_dir, f'{question}_{gender_name}.png')
    plt.savefig(save_path)
    plt.close()


# 性別ごとにループして集計と出力を行う
for gender_value, gender_name in genders.items():
    print(f"\n{'='*20} 集計結果: {gender_name.capitalize()} (male={gender_value}) {'='*20}")
    
    # 性別でデータをフィルタリング
    df_gender = df[df['male'] == gender_value].copy()
    
    if df_gender.empty:
        print(f"{gender_name.capitalize()} のデータはありませんでした。")
        continue

    # 結果を格納する辞書
    results = {}

    # データ集計
    for q, options in question_options.items():
        results[q] = {}
        # モデルごとの処理
        for model in ['gpt_w_pref', 'gpt_wo_pref']:
            col = f'{q}_{model}'
            if col in df_gender.columns:
                counts = df_gender[col].value_counts(normalize=True).reindex(options, fill_value=0).sort_index()
                results[q][model] = counts
        # surveyがあれば追加（Q17除く）
        survey_col = f'{q}_survey'
        if survey_col in df_gender.columns:
            counts = df_gender[survey_col].value_counts(normalize=True).reindex(options, fill_value=0).sort_index()
            results[q]['survey'] = counts

    # 集計結果の出力
    for question, models_data in results.items():
        # データが存在しない質問はスキップ
        if not models_data:
            continue
            
        print(f"\n▼ {question} 選択肢ごとの割合(人数)")
        
        output_df = pd.DataFrame()
        
        for model_name, proportions in models_data.items():
            original_col_name = f'{question}_survey' if 'survey' in model_name else f'{question}_{model_name}'
            
            # 該当カラムの総回答数を取得
            total_responses = df_gender[original_col_name].count()
            
            # 割合から人数を算出
            counts = (proportions * total_responses).round().astype(int)
            
            # '割合 (人数)' の形式で文字列を作成
            formatted_list = [f"{prop:.2f} ({count})" for prop, count in zip(proportions, counts)]
            
            # データフレームに結果を追加
            output_df[model_name] = pd.Series(formatted_list, index=proportions.index)
            
        print(output_df)

    # グラフの描画
    print(f"\n--- {gender_name.capitalize()} のグラフを生成中 ---")
    for q in ['question_15', 'question_16', 'question_18']:
        if q in results and results[q]: # その性別のデータに、その質問の結果が存在する場合のみプロット
            plot_question_distribution(q, question_options[q], results, gender_name, output_dir)
    print(f"{gender_name.capitalize()} のグラフを '{output_dir}' に保存しました。")

# --- 修正はここまで ---