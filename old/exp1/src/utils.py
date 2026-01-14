import json
import os
import pandas as pd

def load_json(filepath):
    """JSONファイルを読み込む"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, filepath):
    """データをJSONとして保存する"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_conversation_log(round_num, agent1_id, agent2_id, dialogue_history, result, output_dir):
    """会話ログを保存する"""
    # ファイル名を生成
    filename = f"round_{round_num:03d}_{agent1_id}_{agent2_id}.json"
    
    # 完全なパスを作成
    path = os.path.join(output_dir, filename)
    
    log_data = {
        "round": round_num,
        "agent_1": agent1_id,
        "agent_2": agent2_id,
        "result": result,
        "dialogue": dialogue_history
    }
    save_json(log_data, path)

def save_match_results(results, filepath):
    """マッチング結果をCSV保存する"""
    df = pd.DataFrame(results)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False, encoding='utf-8-sig')