import random

def generate_preferences(seekers, companies):
    """
    求職者と企業のリストを受け取り、それぞれのランダムな選好リストを生成する。
    """
    preferences = {}
    
    # 求職者の選好（全企業をランダム順で）
    for s in seekers:
        prefs = companies.copy()
        random.shuffle(prefs)
        preferences[s] = prefs
        
    # 企業の選好（全求職者をランダム順で）
    for c in companies:
        prefs = seekers.copy()
        random.shuffle(prefs)
        preferences[c] = prefs
        
    return preferences