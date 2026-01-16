import os
import json
import pandas as pd
import glob
import copy
import ast
import numpy as np

# ==========================================
# 1. Algorithm Definitions (Modified EADA)
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
# 2. Metric Calculation Functions
# ==========================================

def check_stability(seeker_matches, seekers_true_prefs, companies_true_prefs, quotas):
    if not seekers_true_prefs or not companies_true_prefs:
        return False

    company_matches = {c: [] for c in companies_true_prefs}
    for s, c in seeker_matches.items():
        if c != "Unmatched" and c in company_matches:
            company_matches[c].append(s)

    for s, s_pref in seekers_true_prefs.items():
        current_match = seeker_matches.get(s, "Unmatched")
        if current_match in s_pref:
            current_s_rank = s_pref.index(current_match)
        else:
            current_s_rank = float('inf')

        for c in companies_true_prefs:
            if c in s_pref:
                c_rank_for_s = s_pref.index(c)
                if c_rank_for_s < current_s_rank:
                    c_pref = companies_true_prefs[c]
                    if s not in c_pref: continue

                    c_capacity = quotas.get(c, 1)
                    c_current_assignees = company_matches[c]
                    
                    if len(c_current_assignees) < c_capacity:
                        return False 
                    
                    worst_assignee = max(c_current_assignees, key=lambda x: c_pref.index(x) if x in c_pref else float('inf'))
                    worst_rank = c_pref.index(worst_assignee) if worst_assignee in c_pref else float('inf')
                    s_rank_for_c = c_pref.index(s)

                    if s_rank_for_c < worst_rank:
                        return False 
    return True

def check_pareto_efficiency(seeker_matches, seekers_true_prefs, quotas):
    if not seekers_true_prefs:
        return False

    company_counts = {}
    for c in quotas: company_counts[c] = 0
    for s, c in seeker_matches.items():
        if c != "Unmatched": company_counts[c] = company_counts.get(c, 0) + 1
            
    for s, s_pref in seekers_true_prefs.items():
        current_match = seeker_matches.get(s, "Unmatched")
        current_rank = s_pref.index(current_match) if current_match in s_pref else float('inf')
        for c in s_pref:
            if s_pref.index(c) < current_rank:
                if company_counts.get(c, 0) < quotas.get(c, 1):
                    return False 

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
                    if holder == start_node: return False 
                    if holder not in path:
                        new_path = path + [holder]
                        stack.append((holder, new_path))
    return True

# ==========================================
# 3. Main Processing Logic
# ==========================================

def process_eada_modifications(root_folder="01_GPT"):
    if not os.path.exists(root_folder):
        print(f"Error: Folder '{root_folder}' not found.")
        return

    all_folders = [f for f in os.listdir(root_folder) if os.path.isdir(os.path.join(root_folder, f))]
    target_folders = [f for f in all_folders if "EADA" in f]
    
    print(f"Found {len(target_folders)} folders with 'EADA'.")

    for folder_name in target_folders:
        folder_path = os.path.join(root_folder, folder_name)
        data_dir = os.path.join(folder_path, "data")
        output_dir = os.path.join(folder_path, "output")
        
        pref_path = os.path.join(data_dir, "preferences.json")
        quota_path = os.path.join(data_dir, "quota.json")

        # 1. フォルダ名からIDを特定し、キーを決定する
        # Folder Format Example: exp4200_school_...
        folder_parts = folder_name.split('_')
        exp_id_str = folder_parts[0]
        if exp_id_str.startswith("exp"):
            exp_id = exp_id_str[3:]
        else:
            exp_id = exp_id_str

        # デフォルトキー
        seeker_key = "job_seekers"
        company_key = "companies"
        
        # IDによるキーの切り替え
        if exp_id.startswith("42"): # School Scenario
            seeker_key = "students"
            company_key = "schools"
        elif exp_id.startswith("43"): # Nursery Scenario
            seeker_key = "parents"
            company_key = "nurseries"
            
        # 2. Load Configuration
        if not os.path.exists(pref_path):
            print(f"Skipping {folder_name}: preferences.json not found.")
            continue
            
        try:
            with open(pref_path, 'r', encoding='utf-8') as f:
                pref_data = json.load(f)
            
            # 動的に決定したキーで取得
            seekers_true_prefs = pref_data.get(seeker_key, {})
            companies_prefs = pref_data.get(company_key, {})
            
            # 取得できなかった場合のフェイルセーフ（念の為元のキーも試す）
            if not seekers_true_prefs:
                seekers_true_prefs = pref_data.get("job_seekers", {})
            if not companies_prefs:
                companies_prefs = pref_data.get("companies", {})

            # それでも空ならスキップ
            if not seekers_true_prefs:
                print(f"Skipping {folder_name}: Could not find preferences for '{seeker_key}' or 'job_seekers'.")
                continue

            if os.path.exists(quota_path):
                with open(quota_path, 'r', encoding='utf-8') as f:
                    quotas = json.load(f)
            else:
                quotas = {c: 1 for c in companies_prefs.keys()}
            
        except Exception as e:
            print(f"Error reading config in {folder_name}: {e}")
            continue

        # 3. Find latest details csv
        if not os.path.exists(output_dir):
            continue
            
        csv_files = glob.glob(os.path.join(output_dir, "*details*.csv"))
        csv_files = [f for f in csv_files if "modified" not in f]
        
        if not csv_files:
            continue
            
        latest_csv_path = sorted(csv_files)[-1]
        print(f"Processing: {folder_name} (Keys: {seeker_key}/{company_key}) -> {os.path.basename(latest_csv_path)}")
        
        try:
            df = pd.read_csv(latest_csv_path)
            
            required_cols = ['Trial', 'Agent', 'Submitted_List', 'True_Preference']
            if not all(col in df.columns for col in required_cols):
                print(f"  Warning: Missing columns in CSV. Skipping.")
                continue

            new_rows = []
            trial_stats = []

            trials = df['Trial'].unique()
            
            for trial_id in trials:
                trial_df = df[df['Trial'] == trial_id]
                
                # --- A. Submitted List Parsing ---
                agent_submissions = {}
                for _, row in trial_df.iterrows():
                    agent = row['Agent']
                    try:
                        sub_list = ast.literal_eval(row['Submitted_List']) if isinstance(row['Submitted_List'], str) else row['Submitted_List']
                        agent_submissions[agent] = sub_list
                    except:
                        agent_submissions[agent] = []
                
                # --- B. Run Modified EADA Algorithm ---
                final_matches_dict = run_eada_enforced_modified(agent_submissions, companies_prefs, quotas)
                
                seeker_matches = {}
                for company, seekers in final_matches_dict.items():
                    for s in seekers:
                        seeker_matches[s] = company
                for s in seekers_true_prefs:
                    if s not in seeker_matches:
                        seeker_matches[s] = "Unmatched"

                # --- C. Calculate Metrics ---
                is_stable = check_stability(seeker_matches, seekers_true_prefs, companies_prefs, quotas)
                is_efficient = check_pareto_efficiency(seeker_matches, seekers_true_prefs, quotas)
                
                honest_count_in_trial = 0
                
                for _, row in trial_df.iterrows():
                    agent = row['Agent']
                    try:
                        true_pref = ast.literal_eval(row['True_Preference']) if isinstance(row['True_Preference'], str) else row['True_Preference']
                        sub_list = agent_submissions.get(agent, [])
                    except:
                        true_pref = []
                        sub_list = []

                    is_honest = (true_pref == sub_list)
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
                    new_row['Is_Honest'] = is_honest
                    
                    new_rows.append(new_row)
                
                total_seekers = len(seekers_true_prefs)
                honest_ratio = honest_count_in_trial / total_seekers if total_seekers > 0 else 0

                trial_stats.append({
                    "is_stable": is_stable,
                    "is_efficient": is_efficient,
                    "honest_ratio": honest_ratio
                })

            # --- D. Save Results ---
            if not new_rows:
                print(f"  Warning: No data rows processed for {folder_name}.")
                continue

            new_df = pd.DataFrame(new_rows)
            base_name = os.path.basename(latest_csv_path)
            name_part, ext = os.path.splitext(base_name)
            new_details_name = f"{name_part}_EADAmodified{ext}"
            new_details_path = os.path.join(output_dir, new_details_name)
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
            
            summary_base_name = base_name.replace("details", "summary")
            if "details" not in base_name: 
                summary_base_name = "summary_" + base_name
            
            new_summary_name = f"{os.path.splitext(summary_base_name)[0]}_EADAmodified.csv"
            new_summary_path = os.path.join(output_dir, new_summary_name)
            
            summary_df.to_csv(new_summary_path, index=False)
            
            print(f"  Saved: {new_details_name}")
            print(f"  Saved: {new_summary_name}")
            print(f"  -> Stability: {summary_data['Value'][0]:.2f}, Efficiency: {summary_data['Value'][1]:.2f}, Honesty: {summary_data['Value'][2]:.2f}")

        except Exception as e:
            print(f"Error processing csv in {folder_name}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    process_eada_modifications()