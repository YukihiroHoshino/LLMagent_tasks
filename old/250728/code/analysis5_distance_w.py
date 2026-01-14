import pandas as pd
import numpy as np

# --- Step 1: データの読み込みと距離計算の関数の定義 ---

try:
    df = pd.read_csv('250728/data/merged_results_high_univ_1.0_wpref.csv')
except FileNotFoundError:
    print("エラー: 'merged_results_high_univ_1.0_wpref.csv' が見つかりません。")
    exit()

def calculate_w2_distance(series1, series2):
    """
    Numpyを使い、2つのpandas Series間の2次ワッサースタイン距離を計算します。
    """
    combined = pd.concat([series1, series2], axis=1).dropna()
    if combined.empty:
        return np.nan
    data1_sorted = np.sort(combined.iloc[:, 0].values)
    data2_sorted = np.sort(combined.iloc[:, 1].values)
    squared_diffs = (data1_sorted - data2_sorted)**2
    return np.sqrt(np.mean(squared_diffs))

# --- Step 2: ブートストラップ検定を実行する関数を定義 ---

def perform_bootstrap_test(df, survey_col, wo_pref_col, w_pref_col, n_bootstraps=10000):
    """
    指定された列名に基づき、ワッサースタイン距離の差についてブートストラップ検定を実行します。
    """
    # 比較ごとに欠損値を除いたペアのデータフレームを作成
    df_survey_wo = df[[survey_col, wo_pref_col]].dropna()
    df_survey_w = df[[survey_col, w_pref_col]].dropna()

    # 観測されたワッサースタイン距離の差を計算
    d1_obs = calculate_w2_distance(df_survey_wo[survey_col], df_survey_wo[wo_pref_col])
    d2_obs = calculate_w2_distance(df_survey_w[survey_col], df_survey_w[w_pref_col])
    
    # 観測データがない場合はNoneを返す
    if pd.isna(d1_obs) or pd.isna(d2_obs):
        return None, None, None, None, None
        
    observed_difference = d1_obs - d2_obs

    # ブートストラップ法によるリサンプリングと差の計算
    bootstrap_diffs = []
    for _ in range(n_bootstraps):
        bs_df1 = df_survey_wo.sample(n=len(df_survey_wo), replace=True)
        d1_boot = calculate_w2_distance(bs_df1[survey_col], bs_df1[wo_pref_col])
        
        bs_df2 = df_survey_w.sample(n=len(df_survey_w), replace=True)
        d2_boot = calculate_w2_distance(bs_df2[survey_col], bs_df2[w_pref_col])
        
        bootstrap_diffs.append(d1_boot - d2_boot)

    bootstrap_diffs = np.array(bootstrap_diffs)

    # p値と信頼区間の算出
    conf_interval = np.percentile(bootstrap_diffs, [2.5, 97.5])
    shifted_bootstrap_diffs = bootstrap_diffs - np.mean(bootstrap_diffs)
    p_value = np.mean(np.abs(shifted_bootstrap_diffs) >= np.abs(observed_difference))

    return d1_obs, d2_obs, observed_difference, conf_interval, p_value

# --- Step 3: 各質問について検定を実行し、結果を出力 ---

# 列名を管理する辞書
cols_survey = {
    15: 'question_15_survey',
    16: 'question_16_survey',
    18: 'question_18_survey'
}
cols_wo_pref = {
    15: 'question_15_gpt_wo_pref',
    16: 'question_16_gpt_wo_pref',
    18: 'question_18_gpt_wo_pref'
}
cols_w_pref = {
    15: 'question_15_gpt_w_pref',
    16: 'question_16_gpt_w_pref',
    18: 'question_18_gpt_w_pref'
}

# 検定対象の質問リスト
questions_to_test = [15, 16, 18]
np.random.seed(0) # 結果の再現性のための乱数シード固定

for q_num in questions_to_test:
    print(f"\n--- ブートストラップ検定の結果 (Question {q_num}) ---")
    
    # 検定を実行
    d1, d2, obs_diff, ci, p_val = perform_bootstrap_test(
        df,
        cols_survey[q_num],
        cols_wo_pref[q_num],
        cols_w_pref[q_num]
    )

    if p_val is None:
        print("データが不足しているため、検定を実行できませんでした。")
        continue

    # 結果を出力
    print(f"観測されたワッサースタイン距離 (Survey vs. wo_pref): {d1:.4f}")
    print(f"観測されたワッサースタイン距離 (Survey vs. w_pref):  {d2:.4f}")
    print(f"観測された距離の差 (d(wo_pref) - d(w_pref)): {obs_diff:.4f}")
    print("-" * 20)
    print(f"距離の差の95%信頼区間: [{ci[0]:.4f}, {ci[1]:.4f}]")
    print(f"p値: {p_val:.4f}")
    print("-" * 20)
    print("結論:")
    if p_val < 0.05:
        print("p値が0.05未満であるため、2つのワッサースタイン距離の差は統計的に有意です。")
    else:
        print("p値が0.05以上であるため、2つのワッサースタイン距離の差は統計的に有意ではありません。")