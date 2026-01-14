import pandas as pd
import matplotlib.pyplot as plt
import os

# ファイル読み込み
df = pd.read_csv('data_analysis_persona/data_formatted/merged_results_high_univ_0.7_wpref.csv')

# 各質問と選択肢の定義
question_options = {
    'question_15': [0, 1, 2, 3],
    'question_16': [0, 1],
    'question_17': [0, 1],  # surveyなし
    'question_18': list(range(9)),
}

# 出力ディレクトリの作成
output_dir = 'data_analysis_persona/fig/macro'
os.makedirs(output_dir, exist_ok=True)

# 結果を格納する辞書
results = {}

# データ集計（この部分は変更なし）
for q, options in question_options.items():
    results[q] = {}
    for model in ['gpt_w_pref', 'gpt_wo_pref']:
        col = f'{q}_{model}'
        if col in df.columns:
            counts = df[col].value_counts(normalize=True).reindex(options, fill_value=0).sort_index()
            results[q][model] = counts
    # surveyがあれば追加（Q17除く）
    survey_col = f'{q}_survey'
    if survey_col in df.columns:
        counts = df[survey_col].value_counts(normalize=True).reindex(options, fill_value=0).sort_index()
        results[q]['survey'] = counts


# 出力
for question, models_data in results.items():
    print(f"\n▼ {question} 選択肢ごとの割合(人数)")
    
    # 整形して表示するための空のデータフレームを作成
    output_df = pd.DataFrame()
    
    for model_name, proportions in models_data.items():
        # 元データから対象カラム名を作成
        if 'survey' in model_name:
            original_col_name = f'{question}_survey'
        else:
            original_col_name = f'{question}_{model_name}'
            
        # 該当カラムの総回答数を取得
        total_responses = df[original_col_name].count()
        
        # 割合から人数を算出
        counts = (proportions * total_responses).round().astype(int)
        
        # '割合 (人数)' の形式で文字列を作成
        formatted_list = []
        for prop, count in zip(proportions, counts):
            formatted_list.append(f"{prop:.2f} ({count})")
            
        # データフレームに結果を追加
        output_df[model_name] = pd.Series(formatted_list, index=proportions.index)
        
    print(output_df)

# --- 出力部分の修正はここまで ---

# グラフ出力関数（変更なし）
def plot_question_distribution(question, options):
    plt.figure(figsize=(8, 5))
    for label, series in results[question].items():
        plt.plot(options, series, marker='o', label=label)
    plt.title(f'{question.upper()} - Distribution Comparison')
    plt.xlabel('Choice')
    plt.ylabel('Density')
    plt.xticks(options)
    plt.legend()
    plt.grid(True)
    save_path = os.path.join(output_dir, f'{question}.png')
    plt.savefig(save_path)
    plt.close()

# Q15, Q16, Q18 の比較グラフのみ描画（変更なし）
for q in ['question_15', 'question_16', 'question_18']:
    plot_question_distribution(q, question_options[q])
