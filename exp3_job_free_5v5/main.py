# main.py
from src.environment import MatchingSimulation

if __name__ == "__main__":
    print("Starting LLM Matching Simulation...")
    sim = MatchingSimulation()
    sim.run()