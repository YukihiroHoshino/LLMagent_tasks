import pandas as pd
import numpy as np

# --- Step 1: データの読み込みと距離計算の関数の定義 ---

def calculate_rmse_distance(series1, series2):
    """
    2つのpandas Series間の二乗平均平方根誤差（RMSE）を計算します。
    NaN値は計算から除外されます。
    """
    # 差の2乗を計算 (NaNは自動的に無視される)
    squared_diff = (series1 - series2)**2
    
    # 差の2乗の平均値を計算
    mean_squared_diff = np.mean(squared_diff)
    
    # 平均値の平方根（RMSE）を返す
    return np.sqrt(mean_squared_diff)

try:
    df = pd.read_csv('250728/data/merged_results_high_univ_1.0_wpref.csv')
except FileNotFoundError:
    print("エラー: 'merged_results_high_univ_0.7_wpref.csv' が見つかりません。")
    exit()

# --- Step 2: ブートストラップ検定を実行する関数を定義 ---

def perform_bootstrap_test_rmse(df, survey_col, wo_pref_col, w_pref_col, n_bootstraps=10000):
    """
    RMSE距離の差についてブートストラップ検定を実行します。
    """
    # 元のデータで観測されたRMSEの差を計算
    d1_obs = calculate_rmse_distance(df[survey_col], df[wo_pref_col])
    d2_obs = calculate_rmse_distance(df[survey_col], df[w_pref_col])
    
    if pd.isna(d1_obs) or pd.isna(d2_obs):
        return None, None, None, None, None
        
    observed_difference = d1_obs - d2_obs

    # ブートストラップ法によるリサンプリングと差の計算
    bootstrap_diffs = []
    for _ in range(n_bootstraps):
        # データ全体から復元抽出でリサンプリング
        bs_df = df.sample(n=len(df), replace=True)
        
        d1_boot = calculate_rmse_distance(bs_df[survey_col], bs_df[wo_pref_col])
        d2_boot = calculate_rmse_distance(bs_df[survey_col], bs_df[w_pref_col])
        
        bootstrap_diffs.append(d1_boot - d2_boot)

    bootstrap_diffs = np.array(bootstrap_diffs)
    bootstrap_diffs = bootstrap_diffs[~np.isnan(bootstrap_diffs)] # NaNを除外

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
    print(f"\n--- RMSE距離のブートストラップ検定 (Question {q_num}) ---")
    
    # 検定を実行
    d1, d2, obs_diff, ci, p_val = perform_bootstrap_test_rmse(
        df,
        cols_survey[q_num],
        cols_wo_pref[q_num],
        cols_w_pref[q_num]
    )

    if p_val is None:
        print("データが不足しているため、検定を実行できませんでした。")
        continue

    # 結果を出力
    print(f"観測されたRMSE (Survey vs. wo_pref): {d1:.4f}")
    print(f"観測されたRMSE (Survey vs. w_pref):  {d2:.4f}")
    print(f"観測された距離の差 (d(wo_pref) - d(w_pref)): {obs_diff:.4f}")
    print("-" * 20)
    print(f"距離の差の95%信頼区間: [{ci[0]:.4f}, {ci[1]:.4f}]")
    print(f"p値: {p_val:.4f}")
    print("-" * 20)
    print("結論:")
    if p_val < 0.05:
        print("p値が0.05未満であるため、2つのRMSEの差は統計的に有意です。")
    else:
        print("p値が0.05以上であるため、2つのRMSEの差は統計的に有意ではありません。")