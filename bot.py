import os
import json
import re
import requests
import lmstudio as lms
from bs4 import BeautifulSoup
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from ddgs import DDGS
from dotenv import load_dotenv
from datetime import datetime

# --- 設定と環境変数 ---
load_dotenv()
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
MODEL_ID = os.environ.get("MODEL_ID")

CURRENT_DATE = datetime.now().strftime("%Y年%m月%d日")

# --- 1. システムプロンプト ---
SYSTEM_PROMPT = f"""
# Role
あなたはSlackで活動する、常に最新情報を把握している優秀なエンジニアリング・アシスタントです。今日の日付は {CURRENT_DATE} です。

# Task
1. **検索の優先**: 学習データよりも最新の情報を優先してください。まず `search_web` で概要を掴みます。
2. **詳細の確認**: 検索結果の中で重要なソースや、ユーザーから指定されたURLがある場合は、必ず `visit_website` を使用して内容を精査してください。
3. **回答の質**: 技術的な正確さを重視し、複数のソースを組み合わせて回答を構成してください。
4. **制約**: 回答はすべて日本語で行い、思考プロセス（<|channel>thought等）は出力に含めないでください。
"""

app = App(token=SLACK_BOT_TOKEN)
model = lms.llm(MODEL_ID)

# --- 2. ツール関数 ---

def search_web(query: str) -> str:
    """
    インターネットで最新情報を検索し、結果のリストを返します。

    Args:
        query (str): 検索したいキーワードや質問文。
    """
    print(f"\n🔍 [TOOL EXECUTION] search_webを開始: query='{query}'")
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=5)]
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        print(f"❌ [TOOL ERROR] search_web: {e}")
        return f"Search Error: {e}"

def visit_website(url: str) -> str:
    """
    指定されたURLのウェブサイトにアクセスし、そのテキスト内容を取得します。
    詳細な情報が必要な場合に使用します。

    Args:
        url (str): 閲覧したいウェブサイトのURL。
    """
    print(f"\n🌐 [TOOL EXECUTION] visit_websiteを開始: url='{url}'")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # HTMLのパースとテキスト抽出
        soup = BeautifulSoup(response.text, 'html.parser')

        # スクリプトやスタイルの削除
        for script_or_style in soup(["script", "style", "header", "footer", "nav"]):
            script_or_style.decompose()

        text = soup.get_text(separator=' ', strip=True)
        # トークン制限を考慮し、最初の5000文字程度に制限
        return text[:5000]
    except Exception as e:
        print(f"❌ [TOOL ERROR] visit_website: {e}")
        return f"Error visiting website: {e}"

# --- 3. 補助関数: クリーニング ---

def clean_text(text: str) -> str:
    if not text: return ""
    text = re.sub(r'<\|channel>thought.*?<channel\|>', '', text, flags=re.DOTALL)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'<\|.*?\|>', '', text)
    text = re.sub(r'<.*?\|>', '', text)
    return text.strip()

# --- 4. Slackイベント処理 ---

@app.event("app_mention")
def handle_mention(event, say, client):
    channel_id = event['channel']
    thread_ts = event.get('thread_ts', event['ts'])
    user_id = event['user']

    print(f"\n--- 📥 New Request from {user_id} ---")

    full_history_prompt = ""
    try:
        replies = client.conversations_replies(channel=channel_id, ts=thread_ts)
        for msg in replies['messages']:
            raw_content = re.sub(r'<@.*?>', '', msg.get('text', '')).strip()
            if not raw_content: continue

            is_bot = msg.get('bot_id') is not None or msg.get('user') == context_bot_id
            role_label = "model" if is_bot else "user"
            full_history_prompt += f"<|turn|>{role_label}\n{clean_text(raw_content)}\n"

    except Exception as e:
        print(f"⚠️ [WARN] History fetch failed: {e}")
        full_history_prompt = f"<|turn|>user\n{re.sub(r'<@.*?>', '', event.get('text', '')).strip()}\n"

    chat = lms.Chat(SYSTEM_PROMPT)
    chat.add_user_message(full_history_prompt)

    final_answer = [""]

    def on_message(message):
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tc in message.tool_calls:
                func_name = getattr(tc, 'name', getattr(tc.function, 'name', 'unknown'))
                func_args = getattr(tc, 'arguments', getattr(tc.function, 'arguments', '{}'))
                print(f"🛠️  [DEBUG: MODEL INTENT] モデルがツール呼び出しを決定: {func_name}")
                print(f"   Arguments: {func_args}")

        if message.role == "assistant":
            if isinstance(message.content, str):
                content = message.content
            else:
                content = "".join([getattr(p, 'text', '') for p in message.content if hasattr(p, 'text')])

            if content.strip() and not (hasattr(message, 'tool_calls') and message.tool_calls):
                final_answer[0] = content

        chat.append(message)

    try:
        print("🤖 Thinking...")
        model.act(
            chat,
            tools=[search_web, visit_website],
            on_message=on_message
        )

        answer = clean_text(final_answer[0])
        if answer:
            say(text=f"<@{user_id}>\n{answer}", thread_ts=thread_ts)
            print("📤 Response sent to Slack.")
        else:
            say(text="回答を生成できませんでした。", thread_ts=thread_ts)

    except Exception as e:
        print(f"❌ [CRITICAL ERROR]: {e}")
        say(text=f"エラーが発生しました: {e}", thread_ts=thread_ts)

if __name__ == "__main__":
    try:
        auth = app.client.auth_test()
        context_bot_id = auth["user_id"]
    except:
        context_bot_id = None

    print(f"LM Studio Bot is running... (Bot ID: {context_bot_id})")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
