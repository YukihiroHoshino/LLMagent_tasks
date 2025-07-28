import pandas as pd
import numpy as np
from scipy.stats import entropy

# --- Step 1: データ読み込みとヘルパー関数の定義 ---

def create_pmf(series, all_possible_values):
    """pandas Seriesから確率質量関数（PMF）を作成します。"""
    counts = series.value_counts().reindex(all_possible_values, fill_value=0)
    # ゼロカウントを避けるための微小値を加える（スムージング）
    counts = counts + 1e-9
    pmf = counts.values / counts.sum()
    return pmf

def calculate_kl_divergence(p, q):
    """scipy.stats.entropyを利用してKLダイバージェンスを計算します。"""
    return entropy(p, q)

try:
    df = pd.read_csv('250728/data/merged_results_high_univ_0.7_wpref.csv')
except FileNotFoundError:
    print("エラー: 'merged_results_high_univ_0.7_wpref.csv' が見つかりません。")
    exit()

# --- Step 2: ブートストラップ検定を実行する関数を定義 ---

def perform_bootstrap_test_kl(df, survey_col, wo_pref_col, w_pref_col, n_bootstraps=10000):
    """KLダイバージェンスの差についてブートストラップ検定を実行します。"""
    
    # 質問内で出現する全てのユニークな値を取得し、確率分布の軸を統一
    all_values = pd.concat([df[c].dropna() for c in [survey_col, wo_pref_col, w_pref_col]]).unique()
    all_values.sort()

    # 元のデータで観測されたKLダイバージェンスの差を計算
    pmf_s_obs = create_pmf(df[survey_col].dropna(), all_values)
    pmf_wo_obs = create_pmf(df[wo_pref_col].dropna(), all_values)
    pmf_w_obs = create_pmf(df[w_pref_col].dropna(), all_values)
    
    d1_obs = calculate_kl_divergence(pmf_s_obs, pmf_wo_obs)
    d2_obs = calculate_kl_divergence(pmf_s_obs, pmf_w_obs)
    observed_difference = d1_obs - d2_obs

    # ブートストラップ
    bootstrap_diffs = []
    for _ in range(n_bootstraps):
        bs_df = df.sample(n=len(df), replace=True)
        
        pmf_s_boot = create_pmf(bs_df[survey_col].dropna(), all_values)
        pmf_wo_boot = create_pmf(bs_df[wo_pref_col].dropna(), all_values)
        pmf_w_boot = create_pmf(bs_df[w_pref_col].dropna(), all_values)

        d1_boot = calculate_kl_divergence(pmf_s_boot, pmf_wo_boot)
        d2_boot = calculate_kl_divergence(pmf_s_boot, pmf_w_boot)
        
        bootstrap_diffs.append(d1_boot - d2_boot)

    bootstrap_diffs = np.array(bootstrap_diffs)

    # p値と信頼区間の算出
    conf_interval = np.percentile(bootstrap_diffs, [2.5, 97.5])
    shifted_bootstrap_diffs = bootstrap_diffs - np.mean(bootstrap_diffs)
    p_value = np.mean(np.abs(shifted_bootstrap_diffs) >= np.abs(observed_difference))

    return d1_obs, d2_obs, observed_difference, conf_interval, p_value

# --- Step 3: 各質問について検定を実行 ---

# 列名を管理する辞書
cols_survey = {15: 'question_15_survey', 16: 'question_16_survey', 18: 'question_18_survey'}
cols_wo_pref = {15: 'question_15_gpt_wo_pref', 16: 'question_16_gpt_wo_pref', 18: 'question_18_gpt_wo_pref'}
cols_w_pref = {15: 'question_15_gpt_w_pref', 16: 'question_16_gpt_w_pref', 18: 'question_18_gpt_w_pref'}

questions_to_test = [15, 16, 18]
np.random.seed(0)

for q_num in questions_to_test:
    print(f"\n--- KLダイバージェンスのブートストラップ検定 (Question {q_num}) ---")
    
    d1, d2, obs_diff, ci, p_val = perform_bootstrap_test_kl(
        df, cols_survey[q_num], cols_wo_pref[q_num], cols_w_pref[q_num]
    )

    print(f"観測されたD_KL(Survey || wo_pref): {d1:.4f}")
    print(f"観測されたD_KL(Survey || w_pref):  {d2:.4f}")
    print(f"観測された距離の差: {obs_diff:.4f}")
    print("-" * 20)
    print(f"距離の差の95%信頼区間: [{ci[0]:.4f}, {ci[1]:.4f}]")
    print(f"p値: {p_val:.4f}")
    print("-" * 20)
    print("結論:")
    if p_val < 0.05:
        print("p値が0.05未満であるため、2つのKLダイバージェンスの差は統計的に有意です。")
    else:
        print("p値が0.05以上であるため、2つのKLダイバージェンスの差は統計的に有意ではありません。")
        