import random
import os
from .agent import Agent
from .utils import save_conversation_log

class Environment:
    # __init__ に api_key 引数を追加
    def __init__(self, personas_data, preferences_data, output_dir, api_key):
        self.agents = {}
        self.unmatched_pool = []
        self.matched_pairs = []
        self.round = 0
        self.output_dir = output_dir
        self.api_key = api_key  # キーを保持
        
        self._initialize_agents(personas_data, preferences_data)
    
    def _initialize_agents(self, personas, prefs):
        for p in personas['job_seekers']:
            # Agent生成時に api_key を渡す
            agent = Agent(p['id'], 'JobSeeker', p, prefs['job_seekers_preferences'][p['id']], self.api_key)
            self.agents[agent.id] = agent
            self.unmatched_pool.append(agent.id)
            
        for p in personas['companies']:
            # Agent生成時に api_key を渡す
            agent = Agent(p['id'], 'Company', p, prefs['companies_preferences'][p['id']], self.api_key)
            self.agents[agent.id] = agent
            self.unmatched_pool.append(agent.id)

    def get_unmatched_by_type(self):
        js = [aid for aid in self.unmatched_pool if self.agents[aid].type == 'JobSeeker']
        co = [aid for aid in self.unmatched_pool if self.agents[aid].type == 'Company']
        return js, co

    def run_simulation(self):
        print(f"--- Simulation Start: {len(self.unmatched_pool)} agents ---")

        while len(self.unmatched_pool) > 0:
            self.round += 1
            js_pool, co_pool = self.get_unmatched_by_type()

            if len(js_pool) == 1 and len(co_pool) == 1:
                self._force_match(js_pool[0], co_pool[0])
                break

            if len(self.unmatched_pool) < 2:
                break 

            pair_ids = random.sample(self.unmatched_pool, 2)
            agent_a = self.agents[pair_ids[0]]
            agent_b = self.agents[pair_ids[1]]

            print(f"\nRound {self.round}: {agent_a.id} vs {agent_b.id}")
            self._process_interaction(agent_a, agent_b)

        print("\n--- Simulation Finished ---")
        return self.matched_pairs

    def _process_interaction(self, agent_a, agent_b):
        dialogue_history = []
        max_turns = 2 
        
        is_negotiation = (agent_a.type != agent_b.type)
        speakers = [agent_a, agent_b] if random.random() > 0.5 else [agent_b, agent_a]

        for i in range(max_turns * 2):
            current_speaker = speakers[i % 2]
            target_agent = speakers[(i + 1) % 2]
            is_final = (i >= (max_turns * 2) - 2)
            
            resp = current_speaker.generate_response(target_agent, dialogue_history, is_final_turn=is_final)
            
            dialogue_history.append({
                "speaker": current_speaker.id,
                "content": resp.message,
                "thought": resp.thought,
                "decision": resp.decision
            })
            
            print(f"  {current_speaker.id} ({resp.decision}): {resp.message[:30]}...")

        last_decision_a = next((x['decision'] for x in reversed(dialogue_history) if x['speaker'] == agent_a.id), "reject")
        last_decision_b = next((x['decision'] for x in reversed(dialogue_history) if x['speaker'] == agent_b.id), "reject")

        if is_negotiation and last_decision_a == "accept" and last_decision_b == "accept":
            print(f"  >>> MATCHED! {agent_a.id} & {agent_b.id}")
            self.matched_pairs.append({
                "round": self.round,
                "job_seeker": agent_a.id if agent_a.type == "JobSeeker" else agent_b.id,
                "company": agent_b.id if agent_b.type == "Company" else agent_a.id,
                "method": "negotiation"
            })
            self.unmatched_pool.remove(agent_a.id)
            self.unmatched_pool.remove(agent_b.id)
            result_status = "Matched"
        else:
            print(f"  >>> Failed: {last_decision_a} / {last_decision_b}")
            result_status = "Unmatched"

        log_dir = os.path.join(self.output_dir, "conversation_logs")
        save_conversation_log(self.round, agent_a.id, agent_b.id, dialogue_history, result_status, output_dir=log_dir)

    def _force_match(self, js_id, co_id):
        print(f"\nFinal Round (Force Match): {js_id} vs {co_id}")
        self.matched_pairs.append({
            "round": self.round,
            "job_seeker": js_id,
            "company": co_id,
            "method": "forced"
        })
        self.unmatched_pool = []
        
        log_dir = os.path.join(self.output_dir, "conversation_logs")
        save_conversation_log(self.round, js_id, co_id, [], "Forced_Matched", output_dir=log_dir)