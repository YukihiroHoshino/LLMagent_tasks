import pandas as pd
import numpy as np

# データセットを読み込みます
try:
    df = pd.read_csv('250728/data/merged_results_high_univ_0.7_wpref.csv')
except FileNotFoundError:
    print("エラー: 'merged_results_high_univ_0.7_wpref.csv' が見つかりません。")
    exit()

def calculate_w2_distance(series1, series2):
    """
    1次元分布を表す2つのpandas Series間の2次ワッサースタイン距離を計算します。
    これは、同じサイズの経験分布を対象とした実装です。
    """
    # 公平な比較と分布のサイズを等しくするため、どちらかのSeriesにNaN値を持つ行を削除します
    combined = pd.concat([series1, series2], axis=1).dropna()
    if combined.empty or len(combined) == 0:
        return np.nan # 有効なデータが残っていない場合はNaNを返します

    # クリーニングされたデータを抽出し、ソートします
    data1_sorted = np.sort(combined.iloc[:, 0].values)
    data2_sorted = np.sort(combined.iloc[:, 1].values)
    
    # ソートされた値の差の2乗を計算します
    squared_diffs = (data1_sorted - data2_sorted)**2
    
    # 2次ワッサースタイン距離は、差の2乗の平均の平方根です
    w2_distance = np.sqrt(np.mean(squared_diffs))
    
    return w2_distance

# --- 各グループの列名を定義します ---
cols_survey = {
    15: 'question_15_survey',
    16: 'question_16_survey',
    18: 'question_18_survey'
}

cols_wo_pref = {
    15: 'question_15_gpt_wo_pref',
    16: 'question_16_gpt_wo_pref',
    17: 'question_17_gpt_wo_pref',
    18: 'question_18_gpt_wo_pref'
}

cols_w_pref = {
    15: 'question_15_gpt_w_pref',
    16: 'question_16_gpt_w_pref',
    17: 'question_17_gpt_w_pref',
    18: 'question_18_gpt_w_pref'
}

# --- 比較を実行し、結果を出力します ---
print("--- 2次ワッサースタイン距離の計算結果 ---")

# Question 15
q = 15
print(f"\n## Question {q}")
dist_sv_wo = calculate_w2_distance(df[cols_survey[q]], df[cols_wo_pref[q]])
dist_sv_w = calculate_w2_distance(df[cols_survey[q]], df[cols_w_pref[q]])
dist_wo_w = calculate_w2_distance(df[cols_wo_pref[q]], df[cols_w_pref[q]])
print(f"Survey vs. wo_pref: {dist_sv_wo:.4f}")
print(f"Survey vs. w_pref:  {dist_sv_w:.4f}")
print(f"wo_pref vs. w_pref: {dist_wo_w:.4f}")

# Question 16
q = 16
print(f"\n## Question {q}")
dist_sv_wo = calculate_w2_distance(df[cols_survey[q]], df[cols_wo_pref[q]])
dist_sv_w = calculate_w2_distance(df[cols_survey[q]], df[cols_w_pref[q]])
dist_wo_w = calculate_w2_distance(df[cols_wo_pref[q]], df[cols_w_pref[q]])
print(f"Survey vs. wo_pref: {dist_sv_wo:.4f}")
print(f"Survey vs. w_pref:  {dist_sv_w:.4f}")
print(f"wo_pref vs. w_pref: {dist_wo_w:.4f}")

# Question 17 (Surveyデータは利用できません)
q = 17
print(f"\n## Question {q}")
dist_wo_w = calculate_w2_distance(df[cols_wo_pref[q]], df[cols_w_pref[q]])
print(f"wo_pref vs. w_pref: {dist_wo_w:.4f}")

# Question 18
q = 18
print(f"\n## Question {q}")
dist_sv_wo = calculate_w2_distance(df[cols_survey[q]], df[cols_wo_pref[q]])
dist_sv_w = calculate_w2_distance(df[cols_survey[q]], df[cols_w_pref[q]])
dist_wo_w = calculate_w2_distance(df[cols_wo_pref[q]], df[cols_w_pref[q]])
print(f"Survey vs. wo_pref: {dist_sv_wo:.4f}")
print(f"Survey vs. w_pref:  {dist_sv_w:.4f}")
print(f"wo_pref vs. w_pref: {dist_wo_w:.4f}")