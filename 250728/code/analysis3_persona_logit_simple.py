import pandas as pd
import statsmodels.api as sm
import numpy as np

# データの読み込み
try:
    df = pd.read_csv('data_analysis_persona/data_formatted/merged_results_high_univ_0.7_wpref.csv')
except FileNotFoundError:
    print("エラー: 'merged_results_high_univ_0.7_wpref.csv' が見つかりません。")


# --- データ前処理 ---

# 1. 目的変数の作成 (PEXGacha)
# question_18が数値でない場合を考慮し、エラーを無視して数値に変換
df['question_18_numeric'] = pd.to_numeric(df['question_18_gpt_wo_pref'], errors='coerce') ###ここを変更
# question_18が0（または数値でない）なら0、それ以外なら1
df['PEXGacha'] = np.where(df['question_18_numeric'] > 0, 1, 0)


# 2. 説明変数の準備
# schoolダミー変数の作成 (School E '20191201' が基準)
school_map = {
    '20181203': 'school_A',
    '20190002': 'school_B',
    '20190001': 'school_C',
    '20190904': 'school_D',
    '20191201': 'school_E'
}
df['school_cat'] = df['school'].astype(str).map(school_map)
school_dummies = pd.get_dummies(df['school_cat'], prefix='school', drop_first=True, dtype=int)
df = pd.concat([df, school_dummies], axis=1)

# 使用する説明変数のリスト
independent_vars = [
    'male',
    'age',
    'pref_RiskAver',
    'pref_LossAver',
    'financialKnowledge',
    'overconfidence',
    'pref_Disc'
]
independent_vars.extend(school_dummies.columns)

# すべての説明変数を強制的に数値型に変換する
for col in independent_vars:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')


# 欠損値を含む行を削除 (目的変数と説明変数の両方でチェック)
df_clean = df.dropna(subset=['PEXGacha'] + independent_vars)


# 説明変数(X)と目的変数(y)を定義
X = df_clean[independent_vars]
y = df_clean['PEXGacha']


# --- Logit回帰分析の実行 ---

# 定数項（切片）をモデルに追加
X = sm.add_constant(X, has_constant='add')

# Model (1): 全員対象の基本モデル
# データが空でないことを確認
if X.empty or y.empty:
    print("エラー: 有効なデータがありません。分析を実行できませんでした。")
else:
    logit_model = sm.Logit(y, X)
    result = logit_model.fit()

    # --- 結果の表示 ---
    def get_significance_stars(p_value):
        """p値に応じてアスタリスクを返す"""
        if p_value < 0.01: return '***'
        elif p_value < 0.05: return '**'
        elif p_value < 0.1: return '*'
        else: return ''

    print("="*60)
    print("Logit Regression Results (Model 1: 全員対象の基本モデル)")
    print("="*60)
    print(f"目的変数: PEXGacha (ガチャ購入経験の有無)")
    print(f"観測数: {int(result.nobs)}")
    print(f"Pseudo R-squ.: {result.prsquared:.4f}")
    print("-"*60)
    print(f"{'変数':<20} {'係数':>10} {'標準誤差':>10} {'p値':>10} {'有意性':>10}")
    print("-"*60)

    params = result.params
    p_values = result.pvalues
    std_errs = result.bse

    for var, param in params.items():
        p_val = p_values[var]
        se = std_errs[var]
        stars = get_significance_stars(p_val)
        print(f"{var:<20} {param:>10.4f} {se:>10.4f} {p_val:>10.4f} {stars:>10}")

    print("-"*60)
    print("有意性: *** p<0.01, ** p<0.05, * p<0.1")
    print("="*60)