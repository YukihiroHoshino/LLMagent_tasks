import re

def extract_action(text):
    """
    テキストから ACTION: [TAG] を抽出する。
    見つからない場合はNoneを返す。
    """
    match = re.search(r"ACTION:\s*\[(APPLY|TALK|WITHDRAW|HOLD|REJECT)\]", text)
    if match:
        return match.group(1)
    return "TALK"  # デフォルト