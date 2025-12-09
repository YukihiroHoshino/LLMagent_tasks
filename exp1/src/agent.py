from openai import OpenAI
from pydantic import BaseModel
from typing import Literal

class AgentDecision(BaseModel):
    thought: str
    message: str
    decision: Literal["negotiate", "accept", "reject"]

class Agent:
    # __init__ に api_key 引数を追加
    def __init__(self, agent_id, agent_type, persona, preferences, api_key):
        self.id = agent_id
        self.type = agent_type
        self.persona = persona
        self.preferences = preferences
        self.matched = False
        
        # キーを明示的に渡して初期化
        self.client = OpenAI(api_key=api_key)
    
    def get_preference_rank(self, partner_id):
        try:
            return self.preferences.index(partner_id) + 1
        except ValueError:
            return 999

    def generate_response(self, partner_agent, conversation_history, is_final_turn=False):
        partner_rank = self.get_preference_rank(partner_agent.id)
        
        system_prompt = f"""
あなたは以下のペルソナを持つ「{self.type}」エージェントです。
現在、マッチングシミュレーションに参加しており、相手と交渉を行っています。

【あなたのペルソナ】
ID: {self.id}
属性: {self.persona}

【現在の状況】
相手のエージェントID: {partner_agent.id}
相手の属性概略: {partner_agent.persona.get('occupation') or partner_agent.persona.get('industry')}
**重要: この相手はあなたの選好順位 第{partner_rank}位 です。**

【目的】
会話を通じて相手を見極め、マッチングするか決定してください。
- 上位の相手なら積極的にアピールしてください。
- 下位の相手でも、他の候補とマッチングできないリスクを考慮し、妥協する戦略もあり得ます。
- 相手が同属性（求職者同士など）の場合は、情報交換のみ行い、必ず 'reject' してください。

【出力形式】
JSON形式で以下の情報を出力してください。
1. thought: 相手の発言を踏まえたあなたの内面の思考（相手のランクや反応を考慮）
2. message: 相手への返答メッセージ
3. decision: 
   - "negotiate": まだ会話を続ける（合意形成中）
   - "accept": マッチングを受け入れる
   - "reject": マッチングを拒否する

※ 今回が「最終ターン」の場合、"negotiate" は選択せず、必ず "accept" か "reject" を選んでください。
"""
        
        messages = [{"role": "system", "content": system_prompt}]
        for chat in conversation_history:
            role = "assistant" if chat["speaker"] == self.id else "user"
            messages.append({"role": role, "content": chat["content"]})

        if is_final_turn:
            messages.append({"role": "system", "content": "これが最後の会話ターンです。必ず 'accept' か 'reject' を決定してください。"})

        completion = self.client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=messages,
            response_format=AgentDecision,
        )

        return completion.choices[0].message.parsed