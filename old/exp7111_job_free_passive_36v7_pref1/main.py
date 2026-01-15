import os
import datetime
import pandas as pd
from src.environment import MatchingSimulation

# --- 実験設定 ---
NUM_TRIALS = 2  # 試行回数

# --- 評価関数 (提供されたものを統合) ---
def check_stability(seeker_matches, seekers_true_prefs, companies_true_prefs, quotas):
    """
    安定性(Stability)のチェック。ブロッキングペアが存在しなければTrue。
    """
    # Inverse matches: {Company: [Seeker1, ...]}
    company_matches = {c: [] for c in companies_true_prefs}
    for s, c in seeker_matches.items():
        if c != "Unmatched" and c in company_matches:
            company_matches[c].append(s)

    for s, s_pref in seekers_true_prefs.items():
        current_match = seeker_matches.get(s, "Unmatched")
        
        # 現在のマッチ相手の順位 (低いほど良い)
        if current_match in s_pref:
            current_s_rank = s_pref.index(current_match)
        else:
            current_s_rank = float('inf')

        for c in companies_true_prefs:
            # 条件1: 求職者sが、現在の相手よりも企業cを好んでいる
            if c in s_pref:
                c_rank_for_s = s_pref.index(c)
                if c_rank_for_s < current_s_rank:
                    c_pref = companies_true_prefs[c]
                    if s not in c_pref: continue

                    c_capacity = quotas.get(c, 1)
                    c_current_assignees = company_matches[c]
                    
                    # 条件2a: 企業cに空席がある
                    if len(c_current_assignees) < c_capacity:
                        return False 
                    
                    # 条件2b: 企業cが、現在の内定者よりも求職者sを好んでいる
                    worst_assignee = max(c_current_assignees, key=lambda x: c_pref.index(x) if x in c_pref else float('inf'))
                    worst_rank = c_pref.index(worst_assignee) if worst_assignee in c_pref else float('inf')
                    s_rank_for_c = c_pref.index(s)

                    if s_rank_for_c < worst_rank:
                        return False 
    return True

def check_pareto_efficiency(seeker_matches, seekers_true_prefs, quotas):
    """
    求職者側のパレート効率性(Efficiency)のチェック。
    """
    # 空席情報の整理
    company_counts = {}
    for c in quotas: company_counts[c] = 0
    for s, c in seeker_matches.items():
        if c != "Unmatched": company_counts[c] = company_counts.get(c, 0) + 1
            
    # 1. 無駄のチェック (より良い空席があるか)
    for s, s_pref in seekers_true_prefs.items():
        current_match = seeker_matches.get(s, "Unmatched")
        current_rank = s_pref.index(current_match) if current_match in s_pref else float('inf')
        for c in s_pref:
            if s_pref.index(c) < current_rank:
                if company_counts.get(c, 0) < quotas.get(c, 1):
                    return False 

    # 2. 交換サイクルのチェック
    c_to_s = {}
    for s, c in seeker_matches.items():
        if c not in c_to_s: c_to_s[c] = []
        c_to_s[c].append(s)

    nodes = list(seekers_true_prefs.keys())
    
    def get_better_companies(seeker):
        pref = seekers_true_prefs[seeker]
        cur = seeker_matches.get(seeker, "Unmatched")
        if cur not in pref: return pref
        idx = pref.index(cur)
        return pref[:idx]

    for start_node in nodes:
        stack = [(start_node, [start_node])]
        while stack:
            curr, path = stack.pop()
            if len(path) > len(nodes): continue
            
            targets = get_better_companies(curr)
            for t_company in targets:
                holders = c_to_s.get(t_company, [])
                for holder in holders:
                    if holder == start_node: return False # Cycle found
                    if holder not in path:
                        new_path = path + [holder]
                        stack.append((holder, new_path))
    return True

# --- Main Execution ---
if __name__ == "__main__":
    print(f"Starting LLM Matching Simulation ({NUM_TRIALS} Trials)...")
    
    # 出力準備
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    all_details = []
    trial_stats = []
    
    for i in range(1, NUM_TRIALS + 1):
        print(f"\n[Trial {i}/{NUM_TRIALS}] Running simulation...")
        
        # シミュレーションの実行
        sim = MatchingSimulation()
        sim.run()
        
        # --- データ抽出 ---
        # 1. エージェント情報と選好の取得
        # environment.pyの実装に基づき、エージェントオブジェクトから情報を取得
        seekers_true_prefs = {agent.name: agent.preferences for agent in sim.seekers}
        companies_true_prefs = {agent.name: agent.preferences for agent in sim.companies}
        quotas = sim.quotas
        
        # 2. マッチング結果の取得
        # エージェントがmatched_partner属性を持っていると仮定
        seeker_matches = {}
        for agent in sim.seekers:
            partner = getattr(agent, "matched_partner", None)
            seeker_matches[agent.name] = partner if partner else "Unmatched"
            
        # --- 検証 (Stability & Efficiency) ---
        is_stable = check_stability(seeker_matches, seekers_true_prefs, companies_true_prefs, quotas)
        is_efficient = check_pareto_efficiency(seeker_matches, seekers_true_prefs, quotas)
        
        print(f"  -> Stability: {is_stable}, Efficiency: {is_efficient}")
        
        # --- ログ記録 ---
        trial_honest_agents = 0
        total_agents = len(sim.seekers)
        
        for agent in sim.seekers:
            
            # 詳細データの追加
            all_details.append({
                "Trial": i,
                "Agent": agent.name,
                "Matched_Partner": seeker_matches[agent.name],
                "Stability": is_stable,
                "Efficiency": is_efficient
            })
            
        # 統計データの記録
        trial_stats.append({
            "Trial": i,
            "is_stable": is_stable,
            "is_efficient": is_efficient
        })

    # --- CSV出力 1: 詳細データ ---
    df_details = pd.DataFrame(all_details)
    details_filename = f"{timestamp}_details.csv"
    df_details.to_csv(os.path.join(output_dir, details_filename), index=False)
    
    # --- CSV出力 2: まとめデータ ---
    # 統計計算
    stability_rate = sum(1 for t in trial_stats if t["is_stable"]) / NUM_TRIALS
    efficiency_rate = sum(1 for t in trial_stats if t["is_efficient"]) / NUM_TRIALS
    
    df_summary = pd.DataFrame([{
        "Stability_Rate": stability_rate,
        "Efficiency_Rate": efficiency_rate,
        "Num_Trials": NUM_TRIALS
    }])
    summary_filename = f"{timestamp}_summary.csv"
    df_summary.to_csv(os.path.join(output_dir, summary_filename), index=False)
    
    print("\n--- Experiment Completed ---")
    print(f"Details saved to: {output_dir}/{details_filename}")
    print(f"Summary saved to: {output_dir}/{summary_filename}")
    print(df_summary)