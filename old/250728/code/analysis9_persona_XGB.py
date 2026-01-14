import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score
import xgboost as xgb
import matplotlib.pyplot as plt
import seaborn as sns
import os

# --- Step 1: データの読み込み ---
try:
    df = pd.read_csv('250728/data/merged_results_high_univ_0.7_wpref.csv')
except FileNotFoundError:
    print("エラー: 'merged_results_high_univ_0.7_wpref.csv' が見つかりません。")
    exit()

# --- Step 2: 分析の準備 ---
predictor_cols = [
    'school', 'male', 'age', 'financialKnowledge', 
    'overconfidence', 'pref_Disc', 'pref_RiskAver', 'pref_LossAver'
]
target_info = {
    'survey': ['question_15_survey', 'question_16_survey', 'question_18_survey'],
    'gpt_wo_pref': ['question_15_gpt_wo_pref', 'question_16_gpt_wo_pref', 'question_18_gpt_wo_pref'],
    'gpt_w_pref': ['question_15_gpt_w_pref', 'question_16_gpt_w_pref', 'question_18_gpt_w_pref']
}

# --- Step 3: XGBoostモデル学習、精度検証、特徴量重要度の算出 ---
all_results_xgb = {}

for group_name, target_cols in target_info.items():
    
    group_results = {}
    for target_col in target_cols:
        question_num = target_col.split('_')[1]
        
        # --- ここからが修正箇所 ---
        # 目的変数を変換
        y_raw = df[target_col].copy()
        if question_num == '15':
            mapping = {0: 0, 1: 0, 2: 1, 3: 1}
            y_raw = y_raw.apply(lambda x: mapping.get(x, x))
            print(f"Info: {target_col}を2値分類 ((0,1)->0, (2,3)->1) に変換しました。")
        elif question_num == '18':
            y_raw = y_raw.apply(lambda x: 0 if x == 0 else 1)
            print(f"Info: {target_col}を2値分類 ((0)->0, (1-8)->1) に変換しました。")
        
        # データ準備 (NaNの除去)
        data = pd.concat([df[predictor_cols], y_raw], axis=1).dropna()
        # 変換後の列名が重複しないように一時的に'target'とする
        data = data.rename(columns={target_col: 'target'})
        # --- 修正箇所ここまで ---
        
        le = LabelEncoder()
        y_encoded = le.fit_transform(data['target'])
        X = data[predictor_cols]

        if len(data) < 50 or len(le.classes_) < 2:
            print(f"Skipping {target_col}: データ不足またはクラスが1種類のみ。")
            continue
        
        min_class_count = np.bincount(y_encoded).min()
        if min_class_count < 2:
            X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)
        else:
            X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)
        
        if np.unique(y_train).size < 2:
            print(f"Skipping {target_col}: 学習データにクラスが1種類しか含まれず、モデルを学習できません。")
            continue

        model = xgb.XGBClassifier(n_estimators=5000, random_state=42, eval_metric='mlogloss')
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='macro', zero_division=0)
        importances = pd.Series(model.feature_importances_, index=predictor_cols)
        
        group_results[target_col] = {
            'importances': importances,
            'accuracy': accuracy,
            'f1_score': f1
        }
        
    all_results_xgb[group_name] = group_results

# --- Step 4: 結果の表示 ---
for group_name, results_dict in all_results_xgb.items():
    print(f"\n===== 貢献度・精度分析 (XGBoost): {group_name} の回答 =====")
    if not results_dict:
        print("このグループの分析結果はありません。")
        continue
    for target_col, results in results_dict.items():
        question_num = target_col.split('_')[1]
        print(f"\n--- Question {question_num} ---")
        print(f"モデル精度 (Accuracy): {results['accuracy']:.4f}")
        print(f"モデル精度 (Macro F1-Score): {results['f1_score']:.4f}")
        print("影響を与える要因 (Feature Importance):")
        print(results['importances'].reindex(predictor_cols))

print("\nXGBoostによる分析が完了しました。")


# --- Step 5: 貢献度グラフの個別出力 ---

# 全ての貢献度の最大値を取得して、グラフのx軸の範囲を統一
global_max_importance = 0
for group_name, importances_dict in all_results_xgb.items():
    for target_col, results in importances_dict.items():
        current_max = results['importances'].max()
        if current_max > global_max_importance:
            global_max_importance = current_max

# 出力先ディレクトリを作成
output_dir = '250728/fig/feature_importance_plots_xgb'
os.makedirs(output_dir, exist_ok=True)

# 各分析結果について個別のグラフを作成
for group_name, importances_dict in all_results_xgb.items():
    for target_col, results in importances_dict.items():
        question_num = target_col.split('_')[1]

        # グラフを新規作成
        plt.figure(figsize=(10, 7))
        
        # 縦軸の順序を統一
        importances_ordered = results['importances'].reindex(predictor_cols)
        
        # 棒グラフを作成し、色を指定
        sns.barplot(x=importances_ordered.values, y=importances_ordered.index, color='#ac2949')
        
        # タイトルとラベルを設定
        title_text = (f"Feature Importance: {group_name} - Q{question_num}\n"
                      f"Accuracy: {results['accuracy']:.3f}, F1-Score: {results['f1_score']:.3f}")
        plt.title(title_text, fontsize=14)
        plt.xlabel('Importance', fontsize=12)
        plt.ylabel('Persona Feature', fontsize=12)
        
        # x軸の範囲を統一
        plt.xlim(0, global_max_importance * 1.05)
        
        # レイアウトを調整して保存
        plt.tight_layout()
        filename = f"{output_dir}/importance_{group_name}_Q{question_num}.png"
        plt.savefig(filename)
        plt.close() # メモリを解放するために図を閉じる

print(f"\n特徴量の重要度グラフを '{output_dir}' フォルダに個別に保存しました。")