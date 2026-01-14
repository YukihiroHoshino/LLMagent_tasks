import os
import json
import pandas as pd
import datetime
from dotenv import load_dotenv
from llm_client import AgentSimulator
from algorithm_engine import run_eada_algorithm

load_dotenv()

NUM_TRIALS = 100  # 実験回数

# Example Description for DA
DA_DESCRIPTION = """
The assignment is generated according to the following procedure:

Part 1
Step 1
• For each Job Seeker, an application is sent to the Company that they ranked first on their "Choice Ranking List".
• If a Company receives only one application, the Job Seeker is temporarily admitted.
• If a Company receives more than one application, the Job Seeker with the highest priority (based on the Company's internal standards) is temporarily admitted and the remaining Job Seekers are rejected.

Step 2
• For each Job Seeker who was rejected in the previous step, an application is sent to the Company that they ranked second on their "Choice Ranking List".
• Each Company that receives new applications considers the Job Seeker it admitted in the previous step together with the new applicants. Among these, the Job Seeker with the highest priority is temporarily admitted and the remaining Job Seekers are rejected.

Following steps
• The procedure continues according to the same rules.

End of Part 1
• The procedure in Part 1 ends when no Job Seeker is rejected.

Part 2
This part checks for "blocking Job Seekers" based on the distinction between temporary admissions (which occur during the steps of Part 1) and final admissions (determined at the end of Part 1).
A Job Seeker is identified as a blocking Job Seeker at a Company if their situation corresponds to the following specific case:
1. Prevention: The Job Seeker was temporarily admitted at a Company during the steps of Part 1, and this temporary admission caused other Job Seekers to be rejected from that Company.
2. Discrepancy: However, this temporary admission differs from the Job Seeker's final admission. That is, the Job Seeker eventually moved to a different Company (or remained unmatched) by the end of Part 1.
In this case, the Job Seeker's temporary presence "blocked" others from a seat that the Job Seeker did not ultimately utilize.

Step 1
• The computer looks for the last step of the procedure in Part 1 in which a Job Seeker has become a blocking Job Seeker.
• If a Job Seeker is a blocking Job Seeker at a Company, the computer will automatically remove the respective Company from the Job Seeker's "Choice Ranking List" and rerun the procedure described in Part 1.
• Note: This automatic waiver will never change your final admission but may improve other Job Seekers' final admissions.

Step 2
• If the procedure has not ended (i.e., blocking Job Seekers are still found), the procedure described in the previous step is repeated.

Final Step
• The procedure ends when there is no step in which a Job Seeker becomes a blocking Job Seeker. The admissions at this point are final.
"""

# ... (check_stability と check_pareto_efficiency 関数は変更なしのため省略) ...
# 必要であれば前回のコードの check_stability, check_pareto_efficiency をここに貼り付けてください

def check_stability(seeker_matches, seekers_true_prefs, companies_true_prefs, quotas):
    # (前回のコードと同じ内容)
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
    # (前回のコードと同じ内容)
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

def main():
    # 1. Setup
    data_dir = "data"
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with open(os.path.join(data_dir, "preferences.json"), "r", encoding="utf-8") as f:
        pref_data = json.load(f)
        
    quota_path = os.path.join(data_dir, "quota.json")
    if os.path.exists(quota_path):
        with open(quota_path, "r", encoding="utf-8") as f:
            quotas = json.load(f)
    else:
        print("Warning: quota.json not found. Defaulting to 1.")
        quotas = {c: 1 for c in pref_data["companies"]}

    job_seekers_true = pref_data["job_seekers"]
    companies_true = pref_data["companies"]
    
    simulator = AgentSimulator(model="gemini-2.5-flash-preview-09-2025", temperature=0.7)
    
    all_trials_details = [] 
    trial_stats = []
    
    print(f"--- Starting Agent Simulation ({NUM_TRIALS} Trials) [Complete Information] ---")
    
    for trial in range(1, NUM_TRIALS + 1):
        print(f"\n[Trial {trial}/{NUM_TRIALS}] Processing...")
        
        agent_submissions = {} 
        current_trial_logs = []
        
        # --- Phase 1: LLM Agents Submit Preferences ---
        for seeker_name, true_pref in job_seekers_true.items():
            try:
                # 【修正箇所】 全エージェントの情報を渡す
                result = simulator.get_agent_decision(
                    agent_name=seeker_name, 
                    true_preference=true_pref,
                    all_seeker_prefs=job_seekers_true, # 追加
                    all_company_prefs=companies_true,  # 追加
                    quotas=quotas,
                    env_description=DA_DESCRIPTION
                )
                
                submitted_list = result.get("choice_ranking_list", [])
                thought = result.get("thought_process", "")
                
                agent_submissions[seeker_name] = submitted_list
                
                current_trial_logs.append({
                    "Trial": trial,
                    "Agent": seeker_name,
                    "True_Preference": str(true_pref),
                    "Submitted_List": str(submitted_list),
                    "Thought_Process": thought,
                    "Is_Honest": (true_pref == submitted_list)
                })
                
            except Exception as e:
                print(f"Failed to get decision for {seeker_name}: {e}")
                agent_submissions[seeker_name] = [] 

        # --- Phase 2: Run Matching Algorithm ---
        final_matches_dict = run_eada_algorithm(agent_submissions, companies_true, quotas)
        
        seeker_matches = {}
        for company, seekers in final_matches_dict.items():
            for s in seekers:
                seeker_matches[s] = company
        
        # --- Phase 3: Evaluate ---
        is_stable = check_stability(seeker_matches, job_seekers_true, companies_true, quotas)
        is_efficient = check_pareto_efficiency(seeker_matches, job_seekers_true, quotas)
        
        print(f"  -> Stability: {is_stable}, Efficiency: {is_efficient}")
        
        # --- Phase 4: Logs ---
        honest_count = 0
        for log in current_trial_logs:
            agent = log["Agent"]
            matched_company = seeker_matches.get(agent, "Unmatched")
            
            log["Matched_Company"] = matched_company
            log["Stability"] = is_stable
            log["Efficiency"] = is_efficient
            
            try:
                true_pref_list = eval(log["True_Preference"]) 
                if matched_company in true_pref_list:
                    rank = true_pref_list.index(matched_company) + 1 
                else:
                    rank = "-"
            except:
                rank = "Error"
            log["Result_Rank"] = rank
            
            if log["Is_Honest"]:
                honest_count += 1
                
            all_trials_details.append(log)

        trial_stats.append({
            "is_stable": is_stable,
            "is_efficient": is_efficient,
            "honest_ratio": honest_count / len(job_seekers_true)
        })

    # --- 5. Output ---
    df_details = pd.DataFrame(all_trials_details)
    details_filename = f"experiment_{timestamp_str}_details.csv"
    df_details.to_csv(os.path.join(output_dir, details_filename), index=False)
    
    total_stable = sum(1 for t in trial_stats if t["is_stable"])
    total_efficient = sum(1 for t in trial_stats if t["is_efficient"])
    avg_honest_rate = sum(t["honest_ratio"] for t in trial_stats) / NUM_TRIALS
    
    summary_data = {
        "Metric": ["Stability Rate", "Efficiency Rate", "Avg Honesty Rate"],
        "Value": [
            total_stable / NUM_TRIALS,
            total_efficient / NUM_TRIALS,
            avg_honest_rate
        ],
        "Description": [
            "Ratio of trials with no blocking pairs",
            "Ratio of trials that are Pareto efficient for seekers",
            "Ratio of honest agents across all trials"
        ]
    }
    
    df_summary = pd.DataFrame(summary_data)
    summary_filename = f"experiment_{timestamp_str}_summary.csv"
    df_summary.to_csv(os.path.join(output_dir, summary_filename), index=False)
    
    print("\n--- Final Results ---")
    print(df_summary)
    print(f"\nSaved files to {output_dir}:")
    print(f"- {details_filename}")
    print(f"- {summary_filename}")

if __name__ == "__main__":
    main()