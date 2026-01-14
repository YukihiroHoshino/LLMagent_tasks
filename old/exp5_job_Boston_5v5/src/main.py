import os
import json
import pandas as pd
from dotenv import load_dotenv
from llm_client import AgentSimulator
from boston_engine import run_boston_algorithm

# Load .env
load_dotenv()

def main():
    # 1. Setup
    input_path = os.path.join("data", "preferences.json")
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    job_seekers_true = data["job_seekers"]
    companies_true = data["companies"]

    # Initialize simulator with temperature=0.7
    simulator = AgentSimulator(model="gpt-4o", temperature=0.7)
    
    # 2. Agent Decisions (LLM)
    agent_submissions = {} # {Seeker_Name: [Submitted_List]}
    agent_logs = []
    
    print("--- Starting Agent Simulation (Temperature: 0.0) ---")
    
    for seeker_name, true_pref in job_seekers_true.items():
        try:
            # Call LLM
            result = simulator.get_agent_decision(seeker_name, true_pref)
            
            submitted_list = result.get("choice_ranking_list", [])
            thought = result.get("thought_process", "")
            
            # Store for Algorithm
            agent_submissions[seeker_name] = submitted_list
            
            # Store for Logging
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
            agent_submissions[seeker_name] = [] # Fallback empty list

    # 3. Matching Calculation (Boston Algorithm)
    print("\n--- Running Boston Algorithm ---")
    # Note: Companies use TRUE preferences, Seekers use SUBMITTED preferences
    final_matches_dict = run_boston_algorithm(agent_submissions, companies_true)
    
    # 4. Result Processing
    # Convert {Company: Seeker} to {Seeker: Company} for easier reading
    seeker_matches = {v: k for k, v in final_matches_dict.items()}
    
    # Add match results to logs
    for log in agent_logs:
        agent = log["Agent"]
        matched_company = seeker_matches.get(agent, "Unmatched")
        log["Matched_Company"] = matched_company
        
        # Calculate Rank Index (0-based) of the result in True Preference
        try:
            # string representation back to list for check
            true_pref_list = eval(log["True_Preference"]) 
            if matched_company in true_pref_list:
                rank = true_pref_list.index(matched_company) + 1 # 1-based rank
            else:
                rank = "-"
        except:
            rank = "Error"
        
        log["Result_Rank"] = rank

    # 5. Save Output
    df_results = pd.DataFrame(agent_logs)
    
    # Display in console
    print("\n--- Final Results ---")
    print(df_results[["Agent", "Matched_Company", "Result_Rank", "Is_Honest"]])
    
    # Save to CSV and JSON
    csv_path = os.path.join(output_dir, "simulation_results.csv")
    json_path = os.path.join(output_dir, "simulation_results.json")
    
    df_results.to_csv(csv_path, index=False)
    df_results.to_json(json_path, orient="records", indent=2)
    
    print(f"\nSaved detailed results to {output_dir}")

if __name__ == "__main__":
    main()