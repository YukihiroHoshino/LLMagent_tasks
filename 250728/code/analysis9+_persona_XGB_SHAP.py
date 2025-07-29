import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score
import xgboost as xgb
import matplotlib.pyplot as plt
import shap
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

# --- Step 3: XGBoostモデル学習とSHAP値の計算 ---
all_results_xgb_shap = {}
print("SHAP analysis started. This may take a few minutes...")

for group_name, target_cols in target_info.items():
    group_results = {}
    for target_col in target_cols:
        question_num = target_col.split('_')[1]
        
        # 目的変数を変換
        y_raw = df[target_col].copy()
        if question_num == '15':
            # (0, 1) -> 0, (2, 3) -> 1
            mapping = {0: 0, 1: 0, 2: 1, 3: 1}
            # .get(x, x)はマッピングにない値をそのまま返す
            y_raw = y_raw.apply(lambda x: mapping.get(x, x))
            print(f"Info: {target_col}を2値分類 ((0,1)->0, (2,3)->1) に変換しました。")
        elif question_num == '18':
            # (0) -> 0, (1, 2, ...) -> 1
            y_raw = y_raw.apply(lambda x: 0 if x == 0 else 1)
            print(f"Info: {target_col}を2値分類 ((0)->0, (1-8)->1) に変換しました。")
        
        # データ準備 (NaNの除去)
        data = pd.concat([df[predictor_cols], y_raw], axis=1).dropna()
        data = data.rename(columns={target_col: 'target'}) # 列名を統一

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

        explainer = shap.TreeExplainer(model)
        shap_explanation = explainer(X_test)
        
        group_results[target_col] = {
            'shap_explanation': shap_explanation,
            'accuracy': accuracy,
            'f1_score': f1,
            'is_binary': len(le.classes_) == 2 # 2値分類だったかのフラグ
        }
    all_results_xgb_shap[group_name] = group_results

print("\nXGBoostによる分析が完了しました。")

# --- Step 4: SHAP サマリープロットの個別出力 ---
output_dir_shap = '250728/fig/feature_importance_plots_xgb_shap'
os.makedirs(output_dir_shap, exist_ok=True)

for group_name, results_dict in all_results_xgb_shap.items():
    if not results_dict:
        
        continue
    for target_col, results in results_dict.items():
        question_num = target_col.split('_')[1]
        plt.figure()
        title_text = (f"SHAP Values: {group_name} - Q{question_num}\n"
                      f"Accuracy: {results['accuracy']:.3f}, F1-Score: {results['f1_score']:.3f}")
        
        # 2値分類の場合、SHAP値は1つのクラスについてのみ計算されるため、プロットを調整
        shap_values_to_plot = results['shap_explanation']
        if results['is_binary']:
            # Positiveクラス(1)に対するSHAP値をプロット
            shap.summary_plot(shap_values_to_plot, show=False)
        else:
            # 多クラスの場合はそのままプロット
            shap.summary_plot(shap_values_to_plot, show=False)
        
        plt.title(title_text, fontsize=14)
        plt.tight_layout()
        filename = f"{output_dir_shap}/shap_summary_{group_name}_Q{question_num}.png"
        plt.savefig(filename)
        plt.close()

print(f"\nSHAPによる貢献度グラフを '{output_dir_shap}' フォルダに個別に保存しました。")

# --- Step 5: SHAP サマリープロットの個別出力2 ---
output_dir_shap = '250728/fig/feature_importance_plots_xgb_shap_ordered'
os.makedirs(output_dir_shap, exist_ok=True)

for group_name, results_dict in all_results_xgb_shap.items():
    if not results_dict:
        continue
    for target_col, results in results_dict.items():
        question_num = target_col.split('_')[1]
        plt.figure()
        title_text = (f"SHAP Values: {group_name} - Q{question_num}\n"
                      f"Accuracy: {results['accuracy']:.3f}, F1-Score: {results['f1_score']:.3f}")
        
        shap_explanation_obj = results['shap_explanation']
        
        # Explanationオブジェクトをpredictor_colsの順序で並べ替える
        shap_explanation_ordered = shap_explanation_obj[:, predictor_cols]
        
        # 並べ替えたオブジェクトをプロットする
        shap.summary_plot(shap_explanation_ordered, show=False ,sort=False)
        
        plt.title(title_text, fontsize=14)
        plt.tight_layout()
        filename = f"{output_dir_shap}/shap_summary_{group_name}_Q{question_num}.png"
        plt.savefig(filename)
        plt.close()

print(f"\nSHAPによる貢献度グラフ（縦軸固定版）を '{output_dir_shap}' フォルダに個別に保存しました。")