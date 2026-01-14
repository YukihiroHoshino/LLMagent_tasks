import pandas as pd
import statsmodels.api as sm
import numpy as np

def run_logit_analysis(df, group_name):
    """
    指定されたデータフレームに対してLogit回帰分析を実行し、結果を表示する関数
    """
    # --- ★★★ 修正箇所 ★★★ ---
    # 1. 基本的な説明変数のリストを定義
    independent_vars = [
        'age',
        'pref_RiskAver',
        'pref_LossAver',
        'financialKnowledge',
        'overconfidence',
        'pref_Disc'
    ]
    
    # 2. 'school_school_'で始まるダミー変数のみをリストに追加する
    #    (元の'school_cat'列を含めないように修正)
    school_dummy_cols = [col for col in df.columns if col.startswith('school_school_')]
    independent_vars.extend(school_dummy_cols)
    
    # 3. 分析に必要な列のみを抽出してコピー
    analysis_df = df[['PEXGacha'] + independent_vars].copy()

    # 4. 説明変数を強制的に数値型に変換
    for col in independent_vars:
        if col in analysis_df.columns:
            analysis_df[col] = pd.to_numeric(analysis_df[col], errors='coerce')
        
    # 5. 欠損値を含む行を削除
    analysis_df.dropna(inplace=True)

    # 6. 目的変数(y)と説明変数(X)を定義
    y = analysis_df['PEXGacha']
    X = analysis_df[independent_vars]
    
    # --- 分析の実行と結果表示 (以下は変更なし) ---
    if X.empty or y.empty or len(y.unique()) < 2:
        print(f"--- {group_name} の分析結果 ---")
        print("エラー: 有効なデータが不足しているため、分析を実行できませんでした。")
        print("="*60, "\n")
        return

    X = sm.add_constant(X, has_constant='add')
    logit_model = sm.Logit(y, X)
    result = logit_model.fit(disp=0)

    def get_significance_stars(p_value):
        if p_value < 0.01: return '***'
        if p_value < 0.05: return '**'
        if p_value < 0.1: return '*'
        return ''

    print("="*60)
    print(f"Logit Regression Results (Model: {group_name}対象)")
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
        #print(f"{param:>10.2f}\n{se:>10.2f}")
        print(f"{var:<20} {param:>10.4f} {se:>10.4f} {p_val:>10.4f} {stars:>10}")

    print("-"*60)
    print("有意性: *** p<0.01, ** p<0.05, * p<0.1")
    print("="*60, "\n")

# --- データの読み込みと前処理 (以下は変更なし) ---
try:
    df = pd.read_csv('data_analysis_persona/data_formatted/merged_results_high_univ_0.7_wpref.csv')
except FileNotFoundError:
    print("エラー: 'merged_results_high_univ_0.7_wpref.csv' が見つかりません。")

df['question_18_numeric'] = pd.to_numeric(df['question_18_survey'], errors='coerce') ###ここを変更
df['PEXGacha'] = np.where(df['question_18_numeric'] > 0, 1, 0)

school_map = {
    '20181203': 'school_A', '20190002': 'school_B', '20190001': 'school_C',
    '20190904': 'school_D', '20191201': 'school_E'
}
df['school_cat'] = df['school'].astype(str).map(school_map)
school_dummies = pd.get_dummies(df['school_cat'], prefix='school_school', drop_first=True, dtype=int)
df = pd.concat([df, school_dummies], axis=1)

df_male = df[df['male'] == 1].copy()
df_female = df[df['male'] == 0].copy()

run_logit_analysis(df_male, "男性 (male=1)")
run_logit_analysis(df_female, "女性 (male=0)")