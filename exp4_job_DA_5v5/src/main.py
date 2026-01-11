import os
import json
import pandas as pd
from dotenv import load_dotenv
from llm_client import AgentSimulator
from da_engine import run_da_algorithm

load_dotenv()

# Example Description for DA (Can be swapped for Boston, etc.)
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
• The procedure in Part 1 ends when no Job Seeker is rejected, that is, each Job Seeker is assigned a seat at a Company. At this point, all temporary admissions become final.
"""

def main():
    # 1. Setup
    data_dir = "data"
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Load Preferences
    with open(os.path.join(data_dir, "preferences.json"), "r", encoding="utf-8") as f:
        pref_data = json.load(f)
        
    # Load Quotas (NEW)
    quota_path = os.path.join(data_dir, "quota.json")
    if os.path.exists(quota_path):
        with open(quota_path, "r", encoding="utf-8") as f:
            quotas = json.load(f)
    else:
        # Default quota if file missing
        print("Warning: quota.json not found. Defaulting to 1.")
        quotas = {c: 1 for c in pref_data["companies"]}

    job_seekers_true = pref_data["job_seekers"]
    companies_true = pref_data["companies"]
    
    simulator = AgentSimulator(model="gpt-4o", temperature=0.0)
    
    # 2. Agent Decisions (LLM)
    agent_submissions = {} 
    agent_logs = []
    
    print("--- Starting Agent Simulation (Capacitated) ---")
    
    for seeker_name, true_pref in job_seekers_true.items():
        try:
            # Pass quotas and description to LLM
            result = simulator.get_agent_decision(
                agent_name=seeker_name, 
                true_preference=true_pref,
                quotas=quotas,
                env_description=DA_DESCRIPTION
            )
            
            submitted_list = result.get("choice_ranking_list", [])
            thought = result.get("thought_process", "")
            
            agent_submissions[seeker_name] = submitted_list
            
            agent_logs.append({
                "Agent": seeker_name,
                "True_Preference": str(true_pref),
                "Submitted_List": str(submitted_list),
                "Thought_Process": thought,
                "Is_Honest": (true_pref == submitted_list)
            })
            
            print(f" -> {seeker_name} submitted list (Honest: {true_pref == submitted_list})")
            
        except Exception as e:
            print(f"Failed to get decision for {seeker_name}: {e}")
            agent_submissions[seeker_name] = [] 

    # 3. Matching Calculation (Capacitated DA)
    print("\n--- Running DA Algorithm (Capacitated) ---")
    final_matches_dict = run_da_algorithm(agent_submissions, companies_true, quotas)
    
    # 4. Result Processing
    # matches_dict is {Company: [Seekers]}. Invert to {Seeker: Company}
    seeker_matches = {}
    for company, seekers in final_matches_dict.items():
        for s in seekers:
            seeker_matches[s] = company
            
    # Update logs
    for log in agent_logs:
        agent = log["Agent"]
        matched_company = seeker_matches.get(agent, "Unmatched")
        log["Matched_Company"] = matched_company
        
        try:
            true_pref_list = eval(log["True_Preference"]) 
            if matched_company in true_pref_list:
                rank = true_pref_list.index(matched_company) + 1 
            else:
                rank = "-"
        except:
            rank = "Error"
        
        log["Result_Rank"] = rank

    # 5. Save Output
    df_results = pd.DataFrame(agent_logs)
    print("\n--- Final Results ---")
    print(df_results[["Agent", "Matched_Company", "Result_Rank", "Is_Honest"]])
    
    df_results.to_csv(os.path.join(output_dir, "simulation_results.csv"), index=False)
    
    print(f"\nSaved detailed results to {output_dir}")

if __name__ == "__main__":
    main()