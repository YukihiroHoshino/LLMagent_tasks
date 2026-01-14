from src.llm.client import LLMClient

class BaseAgent:
    def __init__(self, name, traits):
        self.name = name
        self.traits = traits
        self.history = []
        self.llm = LLMClient()
    
    def add_message(self, role, content):
        self.history.append({"role": role, "content": content})
        
    def get_context(self):
        return self.history
    
    def reset_history(self):
        self.history = []