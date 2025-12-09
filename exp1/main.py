import json

def load_data():
    with open('data/input/personas.json', 'r', encoding='utf-8') as f:
        personas = json.load(f)
    
    with open('data/input/preferences.json', 'r', encoding='utf-8') as f:
        preferences = json.load(f)
        
    return personas, preferences