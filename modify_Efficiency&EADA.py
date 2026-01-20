import os
import json
import pandas as pd
import glob
import copy
import ast
import numpy as np

# ==========================================
# 1. Algorithm Definitions
# ==========================================

def run_eada_enforced_modified(seekers_prefs, companies_prefs, quotas):
    """
    EADA Enforced Algorithm (Modified Waiver Logic)
    """
    current_seekers_prefs = copy.deepcopy(seekers_prefs)
    max_loops = 100 
    loop_count = 0
     
    while loop_count < max_loops:
        loop_count += 1
         
        trace_log, da_matches = _run_simultaneous_da(current_seekers_prefs, companies_prefs, quotas)
         
        final_assignments = {}
        for c, s_list in da_matches.items():
            for s in s_list:
                final_assignments[s] = c
         
        blocking_instances = [] 
        for event in trace_log:
            blocker = event['blocker']
            company = event['company']
            step = event['step']
            final_match = final_assignments.get(blocker)
             
            if final_match != company:
                blocking_instances.append({
                    'step': step, 
                    'blocker': blocker, 
                    'company': company
                })
         
        if not blocking_instances:
            return da_matches
         
        max_step = max(b['step'] for b in blocking_instances)
        target_interrupters = set(b['blocker'] for b in blocking_instances if b['step'] == max_step)
         
        changed = False
        for seeker in target_interrupters:
            companies_to_remove = set(b['company'] for b in blocking_instances if b['blocker'] == seeker)
            for company in companies_to_remove:
                if company in current_seekers_prefs[seeker]:
                    current_seekers_prefs[seeker].remove(company)
                    changed = True
         
        if not changed:
            return da_matches
            
    return da_matches

def _run_simultaneous_da(seekers_prefs, companies_prefs, quotas):
    matches = {c: [] for c in companies_prefs}
    free_seekers = list(seekers_prefs.keys())
    proposals_count = {s: 0 for s in seekers_prefs}
    company_rankings = {c: {s: i for i, s in enumerate(prefs)} for c, prefs in companies_prefs.items()}
     
    trace_log = []
    step = 0
     
    while True:
        step += 1
        current_round_proposals = {c: [] for c in companies_prefs}
        if not free_seekers:
            break
        candidates_to_process = list(free_seekers)
        free_seekers = [] 
        has_new_proposals = False
         
        for seeker in candidates_to_process:
            pref_list = seekers_prefs.get(seeker, [])
            idx = proposals_count[seeker]
            if idx < len(pref_list):
                target_company = pref_list[idx]
                proposals_count[seeker] += 1
                if target_company in current_round_proposals:
                    current_round_proposals[target_company].append(seeker)
                    has_new_proposals = True
                else:
                    free_seekers.append(seeker)
            else:
                pass

        if not has_new_proposals:
            break
             
        for company, new_applicants in current_round_proposals.items():
            if not new_applicants and not matches[company]:
                continue
            current_holders = matches[company]
            all_candidates = current_holders + new_applicants
            rank_map = company_rankings.get(company, {})
            valid_candidates = [s for s in all_candidates if s in rank_map]
            rejected_candidates_this_turn = [s for s in all_candidates if s not in rank_map]
            valid_candidates.sort(key=lambda s: rank_map[s])
            capacity = quotas.get(company, 1)
            accepted = valid_candidates[:capacity]
            rejected_capacity = valid_candidates[capacity:]
            total_rejected = rejected_capacity + rejected_candidates_this_turn
            matches[company] = accepted
            for r in total_rejected:
                free_seekers.append(r)
            if total_rejected and accepted:
                for blocker in accepted:
                    trace_log.append({
                        'type': 'rejection_caused',
                        'step': step,
                        'blocker': blocker,
                        'company': company
                    })
    return trace_log, matches

# ==========================================
# 2. Metric Calculation Functions (Robust Version)
# ==========================================

def check_stability(seeker_matches, seekers_true_prefs, companies_true_prefs, quotas):
    if not seekers_true_prefs or not companies_true_prefs:
        return False

    # マッチング結果の逆引き辞書作成
    company_matches = {}
    # 全ての企業キーを初期化（quotasやprefsから）
    all_companies = set(companies_true_prefs.keys()) | set(quotas.keys())
    for c in all_companies:
        company_matches[c] = []
        
    for s, c in seeker_matches.items():
        if c != "Unmatched" and c in company_matches:
            company_matches[c].append(s)

    for s, s_pref in seekers_true_prefs.items():
        current_match = seeker_matches.get(s, "Unmatched")
        if current_match in s_pref:
            current_s_rank = s_pref.index(current_match)
        else:
            current_s_rank = float('inf')

        # ブロッキングペアの探索
        # 探索対象の企業は「求職者の選好リストにある企業」と「実際の企業マスタ」の積集合
        # これにより存在しない名前でのエラーを防ぐ
        target_companies = set(companies_true_prefs.keys())
        
        for c in s_pref:
            if c not in target_companies: continue
            
            # 条件1: 求職者にとって現在のマッチより良いか
            c_rank_for_s = s_pref.index(c)
            if c_rank_for_s < current_s_rank:
                c_pref = companies_true_prefs[c]
                if s not in c_pref: continue

                c_capacity = quotas.get(c, 1)
                c_current_assignees = company_matches.get(c, [])
                
                # 条件2a: 定員に空きがある
                if len(c_current_assignees) < c_capacity:
                    return False 
                
                # 条件2b: 定員がいっぱいだが、現在の誰かより好まれている
                worst_assignee = max(c_current_assignees, key=lambda x: c_pref.index(x) if x in c_pref else float('inf'))
                worst_rank = c_pref.index(worst_assignee) if worst_assignee in c_pref else float('inf')
                s_rank_for_c = c_pref.index(s)

                if s_rank_for_c < worst_rank:
                    return False 
    return True

def check_pareto_efficiency_bruteforce(seeker_matches, seekers_true_prefs, quotas):
    """
    全探索による提案側パレート効率性のチェック (Robust Version)
    名前の不一致（School_A vs Company_A）による誤判定を防ぐため、
    探索対象の企業リストを選好リストの実データから構築する。
    """
    if not seekers_true_prefs:
        return False

    seekers = list(seekers_true_prefs.keys())
    
    # 1. 探索すべきターゲット企業のリストアップ
    # quotasのキーだけでなく、選好リストに含まれる全ての企業名を対象にする
    # これにより "School_A" vs "Company_A" 問題を吸収
    target_companies = set(quotas.keys())
    for prefs in seekers_true_prefs.values():
        for p in prefs:
            target_companies.add(p)
    target_companies = list(target_companies)
    
    # 定員の整備（選好リストにしかない名前は定員1と仮定するか、quotasにあるものだけを信じるか）
    # ここでは「選好リストにある名前」が重要なので、quotasにないものはデフォルト1とする
    safe_quotas = quotas.copy()
    for c in target_companies:
        if c not in safe_quotas:
            safe_quotas[c] = 1

    # 2. 現在のマッチングのランク計算
    current_ranks = {}
    for s in seekers:
        match = seeker_matches.get(s, "Unmatched")
        pref = seekers_true_prefs.get(s, [])
        if match in pref:
            current_ranks[s] = pref.index(match)
        else:
            current_ranks[s] = float('inf')

    found_improvement = False
    
    def backtrack(idx, current_quota_usage, assignment_ranks):
        nonlocal found_improvement
        if found_improvement: return

        if idx == len(seekers):
            is_worsened = False
            is_strictly_better = False
            
            for i, s in enumerate(seekers):
                new_r = assignment_ranks[i]
                curr_r = current_ranks[s]
                
                if new_r > curr_r: # 悪化した
                    is_worsened = True
                    break
                if new_r < curr_r: # 改善した
                    is_strictly_better = True
            
            if not is_worsened and is_strictly_better:
                found_improvement = True
            return

        s = seekers[idx]
        s_pref = seekers_true_prefs.get(s, [])
        
        # 1. 企業への割り当て
        # ここで target_companies (選好リストに登場する名前含む) を回すのが重要
        for c in target_companies:
            # 容量チェック
            if current_quota_usage.get(c, 0) < safe_quotas.get(c, 1):
                
                # 選好リスト内ランク計算
                if c in s_pref:
                    rank = s_pref.index(c)
                else:
                    # 選好リストにない企業への割り当てはランク無限大（拒否と同じ）
                    rank = float('inf')
                
                # 枝刈り: 現状より悪化するならスキップ
                if rank > current_ranks[s]:
                    continue
                
                current_quota_usage[c] = current_quota_usage.get(c, 0) + 1
                assignment_ranks.append(rank)
                backtrack(idx + 1, current_quota_usage, assignment_ranks)
                assignment_ranks.pop()
                current_quota_usage[c] -= 1
                if found_improvement: return

        # 2. Unmatchedへの割り当て
        rank_unmatched = float('inf')
        if rank_unmatched <= current_ranks[s]:
            assignment_ranks.append(rank_unmatched)
            backtrack(idx + 1, current_quota_usage, assignment_ranks)
            assignment_ranks.pop()

    backtrack(0, {}, [])
    return not found_improvement

# ==========================================
# 3. Main Processing Logic
# ==========================================

def process_all_experiments(root_folder="00_Gemini"):
    if not os.path.exists(root_folder):
        print(f"Error: Folder '{root_folder}' not found.")
        return

    all_folders = [f for f in os.listdir(root_folder) if os.path.isdir(os.path.join(root_folder, f))]
    print(f"Found {len(all_folders)} folders in total.")

    for folder_name in all_folders:
        folder_path = os.path.join(root_folder, folder_name)
        data_dir = os.path.join(folder_path, "data")
        output_dir = os.path.join(folder_path, "output")
        
        pref_path = os.path.join(data_dir, "preferences.json")
        quota_path = os.path.join(data_dir, "quota.json")

        # --- 1. Identify Scenario and Keys (Robust) ---
        scenario = "job" # default
        
        parts = folder_name.split('_')
        exp_id_part = parts[0] # "exp4123"
        
        if exp_id_part.startswith("exp"):
            id_str = exp_id_part[3:] # "4123"
        else:
            id_str = exp_id_part
            
        # IDによる判定 (2文字目: 1=job, 2=school, 3=nursery)
        if len(id_str) >= 2:
            indicator = id_str[1]
            if indicator == '1':
                scenario = 'job'
            elif indicator == '2':
                scenario = 'school'
            elif indicator == '3':
                scenario = 'nursery'
            # フォールバック
            elif 'school' in folder_name:
                scenario = 'school'
            elif 'nursery' in folder_name:
                scenario = 'nursery'
        else:
            if 'school' in folder_name:
                scenario = 'school'
            elif 'nursery' in folder_name:
                scenario = 'nursery'
        
        if scenario == 'school':
            seeker_key = 'students'
            company_key = 'schools'
        elif scenario == 'nursery':
            seeker_key = 'parents'
            company_key = 'nurseries'
        else:
            seeker_key = 'job_seekers'
            company_key = 'companies'
            
        # --- 2. Load Configuration ---
        if not os.path.exists(pref_path):
            continue
            
        try:
            with open(pref_path, 'r', encoding='utf-8') as f:
                pref_data = json.load(f)
            
            seekers_true_prefs = pref_data.get(seeker_key, {})
            companies_prefs = pref_data.get(company_key, {})
            
            # デフォルトキーへのフォールバック
            if not seekers_true_prefs:
                seekers_true_prefs = pref_data.get("job_seekers", {})
            if not companies_prefs:
                companies_prefs = pref_data.get("companies", {})

            if not seekers_true_prefs:
                print(f"Skipping {folder_name}: Preferences empty.")
                continue

            if os.path.exists(quota_path):
                with open(quota_path, 'r', encoding='utf-8') as f:
                    quotas = json.load(f)
            else:
                # クオータがない場合は全企業に対して1を設定
                quotas = {c: 1 for c in companies_prefs.keys()}
            
        except Exception as e:
            print(f"Error reading config in {folder_name}: {e}")
            continue

        # --- 3. Find latest details csv (Exclude 'modified') ---
        if not os.path.exists(output_dir):
            continue
            
        csv_files = glob.glob(os.path.join(output_dir, "*details*.csv"))
        csv_files = [f for f in csv_files if "modified" not in f]
        
        if not csv_files:
            continue
            
        latest_csv_path = sorted(csv_files)[-1]
        
        is_eada = "EADA" in folder_name
        
        print(f"Processing: {folder_name} (Scenario: {scenario}) -> {os.path.basename(latest_csv_path)}")
        
        try:
            df = pd.read_csv(latest_csv_path)
            
            # カラム名正規化
            if 'Matched_Partner' in df.columns and 'Matched_Company' not in df.columns:
                df['Matched_Company'] = df['Matched_Partner']
            
            # EADAチェック
            if is_eada and 'Submitted_List' not in df.columns:
                 print(f"  Warning: EADA folder but missing Submitted_List. Skipping.")
                 continue
                 
            # 必須カラムチェック
            if 'Trial' not in df.columns or 'Agent' not in df.columns:
                 print(f"  Warning: Missing Trial or Agent columns. Skipping.")
                 continue

            new_rows = []
            trial_stats = []
            trials = df['Trial'].unique()
            
            for trial_id in trials:
                trial_df = df[df['Trial'] == trial_id]
                
                # --- A. Determine Matching ---
                seeker_matches = {}
                
                if is_eada:
                    agent_submissions = {}
                    for _, row in trial_df.iterrows():
                        agent = row['Agent']
                        try:
                            sub_list = ast.literal_eval(row['Submitted_List']) if isinstance(row['Submitted_List'], str) else row['Submitted_List']
                            agent_submissions[agent] = sub_list
                        except:
                            agent_submissions[agent] = []
                    
                    final_matches_dict = run_eada_enforced_modified(agent_submissions, companies_prefs, quotas)
                    
                    for company, seekers in final_matches_dict.items():
                        for s in seekers:
                            seeker_matches[s] = company
                else:
                    for _, row in trial_df.iterrows():
                        agent = row['Agent']
                        m_comp = row.get('Matched_Company', 'Unmatched')
                        if pd.isna(m_comp): m_comp = "Unmatched"
                        seeker_matches[agent] = m_comp

                # Unmatched補完
                for s in seekers_true_prefs:
                    if s not in seeker_matches:
                        seeker_matches[s] = "Unmatched"

                # --- B. Calculate Metrics (Robust Check) ---
                is_stable = check_stability(seeker_matches, seekers_true_prefs, companies_prefs, quotas)
                is_efficient = check_pareto_efficiency_bruteforce(seeker_matches, seekers_true_prefs, quotas)
                
                honest_count_in_trial = 0
                has_honesty_info = 'Submitted_List' in df.columns and 'True_Preference' in df.columns
                
                # --- C. Update Rows ---
                for _, row in trial_df.iterrows():
                    agent = row['Agent']
                    is_honest = False
                    
                    if has_honesty_info:
                        try:
                            true_pref = ast.literal_eval(row['True_Preference']) if isinstance(row['True_Preference'], str) else row['True_Preference']
                            sub_list = ast.literal_eval(row['Submitted_List']) if isinstance(row['Submitted_List'], str) else row['Submitted_List']
                            is_honest = (true_pref == sub_list)
                        except:
                            is_honest = False
                            true_pref = []
                    else:
                        true_pref = seekers_true_prefs.get(agent, [])

                    if is_honest:
                        honest_count_in_trial += 1
                        
                    matched_company = seeker_matches.get(agent, "Unmatched")
                    
                    try:
                        if matched_company in true_pref:
                            rank = true_pref.index(matched_company) + 1
                        else:
                            rank = "-"
                    except:
                        rank = "Error"

                    new_row = row.copy()
                    new_row['Matched_Company'] = matched_company
                    new_row['Result_Rank'] = rank
                    new_row['Stability'] = is_stable
                    new_row['Efficiency'] = is_efficient
                    if has_honesty_info:
                        new_row['Is_Honest'] = is_honest
                    
                    new_rows.append(new_row)
                
                total_seekers = len(seekers_true_prefs)
                if has_honesty_info:
                    honest_ratio = honest_count_in_trial / total_seekers if total_seekers > 0 else 0
                else:
                    honest_ratio = 0

                trial_stats.append({
                    "is_stable": is_stable,
                    "is_efficient": is_efficient,
                    "honest_ratio": honest_ratio
                })

            # --- D. Save Results ---
            if not new_rows:
                continue

            new_df = pd.DataFrame(new_rows)
            base_name = os.path.basename(latest_csv_path)
            name_part, ext = os.path.splitext(base_name)
            
            new_details_name = f"{name_part}_Efficiency&EADAmodified{ext}"
            new_details_path = os.path.join(output_dir, new_details_name)
            
            summary_base_name = base_name.replace("details", "summary")
            if "details" not in base_name: 
                summary_base_name = "summary_" + base_name
            new_summary_name = f"{os.path.splitext(summary_base_name)[0]}_Efficiency&EADAmodified.csv"
            new_summary_path = os.path.join(output_dir, new_summary_name)
            
            new_df.to_csv(new_details_path, index=False)
            
            num_trials = len(trials)
            total_stable = sum(1 for t in trial_stats if t["is_stable"])
            total_efficient = sum(1 for t in trial_stats if t["is_efficient"])
            avg_honest_rate = sum(t["honest_ratio"] for t in trial_stats) / num_trials if num_trials > 0 else 0
            
            summary_data = {
                "Metric": ["Stability Rate", "Efficiency Rate", "Avg Honesty Rate"],
                "Value": [
                    total_stable / num_trials if num_trials > 0 else 0,
                    total_efficient / num_trials if num_trials > 0 else 0,
                    avg_honest_rate
                ],
                "Description": [
                    "Ratio of trials with no blocking pairs",
                    "Ratio of trials that are Pareto efficient for seekers",
                    "Ratio of honest agents across all trials"
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_csv(new_summary_path, index=False)
            
            print(f"  Saved: {new_details_name}")
            print(f"  Saved: {new_summary_name}")
            print(f"  -> Stab: {summary_data['Value'][0]:.2f}, Eff: {summary_data['Value'][1]:.2f}, Honesty: {summary_data['Value'][2]:.2f}")

        except Exception as e:
            print(f"Error processing csv in {folder_name}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    process_all_experiments()