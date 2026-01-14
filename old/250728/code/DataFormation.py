import pandas as pd
import os

# --- 0. 初期設定 ---
# プロジェクトのルートディレクトリから実行することを前提としたパス設定

# 入力ファイルのパス
input_path_gpt_w_pref = '250728/data/temp1.0/gpt_agent_results_high_univ_1.0.csv'
input_path_gpt_wo_pref = '250728/data/temp1.0/gpt_agent_results_high_univ_1.0_NoMeasure.csv'
input_path_survey = '250728/data/20191031_DatasetCreation.csv'

# 出力ディレクトリのパス
output_dir = '250728/data'
output_filename = 'merged_results_high_univ_1.0_wpref.csv'
os.makedirs(output_dir, exist_ok=True) # ディレクトリがなければ作成

try:
    # --- 1. データの読み込み ---
    print("データの読み込みを開始します...")
    df_gpt_w_pref = pd.read_csv(input_path_gpt_w_pref)
    df_gpt_wo_pref = pd.read_csv(input_path_gpt_wo_pref)
    df_survey = pd.read_csv(input_path_survey)

    # --- 2. データの結合 ---
    # まず、最初の2つのデータフレームを結合する
    print("1回目のマージを実行します (df_gpt_w_pref と df_gpt_wo_pref)...")
    merged_df_temp = pd.merge(df_gpt_w_pref, df_gpt_wo_pref, on='ID', how='left', suffixes=('_w_pref', '_wo_pref'))

    # 次に、1回目の結合結果と3つ目のデータフレームを結合する
    print("2回目のマージを実行します (上記結果と df_survey)...")
    merged_df = pd.merge(merged_df_temp, df_survey, on='ID', how='left')
    print("データの結合が完了しました。")

    # 処理中のSettingWithCopyWarningを回避
    df = merged_df.copy() 

    # --- 2. 列の計算と生成 ---
    print("\n新しい列の計算を開始します...")
    # age = eduyear + 6
    df['age'] = df['eduYear'] + 6
    print("'age'列を計算しました。")
    
    # pref_Disc = prefDiscNowL + prefDisc1MoL
    df['pref_Disc'] = df['prefDiscNowL'] + df['prefDisc1MoL']
    print("'pref_Disc'列を計算しました。")

    # gptとsurveyの比較のための計算
    df['question_15_gpt_w_pref'] = 4 - df['question_15_ans_w_pref']
    df['question_16_gpt_w_pref'] = 2 - df['question_16_ans_w_pref']
    df['question_17_gpt_w_pref'] = 2 - df['question_17_ans_w_pref']
    df['question_18_gpt_w_pref'] = df['question_18_ans_w_pref'] - 1

    df['question_15_gpt_wo_pref'] = 4 - df['question_15_ans_wo_pref']
    df['question_16_gpt_wo_pref'] = 2 - df['question_16_ans_wo_pref']
    df['question_17_gpt_wo_pref'] = 2 - df['question_17_ans_wo_pref']
    df['question_18_gpt_wo_pref'] = df['question_18_ans_wo_pref'] - 1
    print("gptとsurveyの比較を計算しました。")

    # --- 3. 列の選択と改名 ---
    print("\n列の選択と改名を行います...")
    
    # 仕様に基づき、列を改名
    df_renamed = df.rename(columns={
        'score10': 'financialKnowledge',
        'overconfScore10': 'overconfidence',
        'prefRiskAver': 'pref_RiskAver',
        'prefLossAver': 'pref_LossAver',
        'question_15_gpt_w_pref': 'question_15_gpt_w_pref',
        'question_16_gpt_w_pref': 'question_16_gpt_w_pref',
        'question_17_gpt_w_pref': 'question_17_gpt_w_pref',
        'question_18_gpt_w_pref': 'question_18_gpt_w_pref',
        'question_15_gpt_wo_pref': 'question_15_gpt_wo_pref',
        'question_16_gpt_wo_pref': 'question_16_gpt_wo_pref',
        'question_17_gpt_wo_pref': 'question_17_gpt_wo_pref',
        'question_18_gpt_wo_pref': 'question_18_gpt_wo_pref',
        'fBehInve': 'question_15_survey',
        'fBehInfo': 'question_16_survey',
        'fBehGameChgRank': 'question_18_survey' 
    })
    
    # 最終的に残す列のリストを定義
    final_columns = [
        'ID', 'school', 'male', 'age', 'financialKnowledge',
        'overconfidence', 'pref_Disc', 'pref_RiskAver', 'pref_LossAver',
        'question_15_gpt_w_pref', 'question_16_gpt_w_pref', 'question_17_gpt_w_pref', 'question_18_gpt_w_pref',
        'question_15_gpt_wo_pref', 'question_16_gpt_wo_pref', 'question_17_gpt_wo_pref', 'question_18_gpt_wo_pref',
        'question_15_survey', 'question_16_survey', 'question_18_survey'
    ]
    
    # 既存の列から、最終的に必要な列だけを、指定の順序で抽出
    existing_final_columns = [col for col in final_columns if col in df_renamed.columns]
    final_df = df_renamed[existing_final_columns]

    print("列の選択と改名が完了しました。")
    print("最終的なデータの列構成:", final_df.columns.tolist())

    # --- 4. 欠損値の処理 ---
    print("\n欠損値の処理を開始します...")
    ids_before_dropping = final_df['ID'].dropna().unique().tolist()
    
    # 最終的に選択した列に一つでも欠損値があれば、その行を削除
    cleaned_df = final_df.dropna()
    
    ids_after_dropping = cleaned_df['ID'].dropna().unique().tolist()
    removed_ids = sorted(list(set(ids_before_dropping) - set(ids_after_dropping)))

    print("\n-------------------------------------------")
    if removed_ids:
        print(f"欠損値が含まれていたため、以下の {len(removed_ids)} 件のIDが削除されました。")
        print(removed_ids)
    else:
        print("欠損値により削除されたIDはありませんでした。")
    print("-------------------------------------------")

    # --- 5. 結果の保存 ---
    output_path = os.path.join(output_dir, output_filename)
    cleaned_df.to_csv(output_path, index=False, encoding='utf-8-sig')

    print(f"\n処理が完了し、最終的なデータが '{os.path.abspath(output_path)}' に保存されました。")
    print(f"最終的なデータは {len(cleaned_df)} 行です。")

except FileNotFoundError as e:
    print(f"\nエラー: ファイル '{e.filename}' が見つかりません。")
    print("プロジェクトのルートディレクトリからスクリプトを実行しているか、ファイルパスが正しいか確認してください。")
except KeyError as e:
    print(f"\nエラー: 指定された列 {e} がデータ内に見つかりません。入力CSVの列名を確認してください。")
except Exception as e:
    print(f"\n予期せぬエラーが発生しました: {e}")