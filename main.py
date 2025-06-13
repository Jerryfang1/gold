from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage, MessageEvent, TextMessage
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# Google Sheets 授權設定
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("金玥報價").worksheet("金價")

@app.route("/webhook", methods=['POST'])
def webhook():
    body = request.get_data(as_text=True)
    signature = request.headers['X-Line-Signature']
    handler.handle(body, signature)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.message.text in ["查詢黃金報價"]:
        user_id = event.source.user_id
        today = datetime.now().strftime("%Y/%m/%d")
        records = sheet.get_all_records()
        matched = next((row for row in records if row['日期'] == today), None)

        if matched:
            price = matched['飾金賣出']
            msg = f"📅 {today} 金玥銀樓金價報價：\n💰 黃金：{price} 元/錢"
        else:
            msg = f"❗ 未找到 {today} 的金價報價，請稍後再試或聯繫店家。"

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))