from flask import Flask, request, abort
from datetime import datetime
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# LINE SDK v3
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging.models import FlexContainer
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    FlexMessage,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent as V3TextMessageContent,
    PostbackEvent
)

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# Google Sheets 授權設定
credentials_json = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_json, scope)
client = gspread.authorize(creds)

# 打開 Sheet
sheet = client.open("金玥報價").worksheet("報價")

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    
    print("=== LINE Webhook Debug ===")
    print("X-Line-Signature:", signature)
    print("Request Body:", body)
    try:
        handler.handle(body, signature)
    except Exception as e:
        print(f"Webhook Error: {e}")
        abort(400)
    return "OK"
    
@handler.add(MessageEvent)
def handle_message(event):
    if isinstance(event.message, V3TextMessageContent):
        text = event.message.text.strip()
        if text == "查詢今日金價":
            reply_gold_price(event.reply_token)

@handler.add(PostbackEvent)
def handle_postback(event):
    if event.postback.data == "action=gold":
        reply_gold_price(event.reply_token)


def reply_gold_price(reply_token):
    today = datetime.now().strftime("%Y/%m/%d")
    alt_today = datetime.now().strftime("%Y-%m-%d")  # 因應不同日期格式

    try:
        records = sheet.get_all_records()
    except Exception as e:
        error_msg = f"無法讀取報價資料：{str(e)}"
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=error_msg)]
            )
        )
        return
    matched = next(
        (row for row in records if str(row.get("日期", "")).strip() in [today, alt_today]),
        None
    )
    
    if not matched:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=f"⚠️ 找不到今日（{today}）報價資料，請聯繫店家。")]
            )
        )
        return

    # 取值
    gold_sell = matched.get("黃金賣出", "N/A")
    gold_buy = matched.get("黃金買入", "N/A")
    pt_sell = matched.get("鉑金賣出", "N/A")
    pt_buy = matched.get("鉑金買入", "N/A")
    date_str = matched.get("日期", "")
    time_str = matched.get("時間", "")

    # 建立 Flex Message 卡片
    flex_content = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "報價時間",
                    "size": "xl",
                    "color": "#1C1c1c",
                    "weight": "bold",
                    "align": "center",
                    "margin": "md"
                },
                {
                    "type": "text",
                    "text": f"🗓️ {date_str} {time_str}",
                    "weight": "bold",
                    "color": "#B08B4F",
                    "align": "center",
                    "margin": "none",
                    "size": "md"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "lg",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#ffffe0",
                    "cornerRadius": "xxl",
                    "spacing": "lg",
                    "paddingAll": "15px",
                    "contents": [
                        {
                            "type": "text",
                            "text": "🟡 黃金",
                            "size": "md",
                            "color": "#1c1c1c",
                            "weight": "bold"
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "🔸 賣出", "color": "#1c1c1c", "flex": 2},
                                {"type": "text", "text": f"{gold_sell} 元／錢", "flex": 3, "color": "#1c1c1c", "align": "end"}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "🔹 買入", "color": "#1c1c1c", "flex": 2},
                                {"type": "text", "text": f"{gold_buy} 元／錢", "flex": 3, "color": "#1c1c1c", "align": "end"}
                            ]
                        }
                    ]
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#3f3f3f",
                    "cornerRadius": "xxl",
                    "paddingAll": "15px",
                    "spacing": "lg",
                    "contents": [
                        {
                            "type": "text",
                            "text": "⚪ 鉑金",
                            "weight": "bold",
                            "size": "md",
                            "color": "#ffffff"
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "🔸 賣出", "flex": 2, "color": "#FFFFFF"},
                                {"type": "text", "text": f"{pt_sell} 元／錢", "color": "#FFFFFF", "flex": 3, "align": "end"}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "🔹 買入", "flex": 2, "color": "#FFFFFF"},
                                {"type": "text", "text": f"{pt_buy} 元／錢", "flex": 3, "color": "#FFFFFF", "align": "end"}
                            ]
                        }
                    ]
                }
            ],
            "margin": "none",
            "offsetTop": "-20px"
        }
    }

    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[
                FlexMessage(
                    alt_text="今日金屬報價",
                    contents=FlexContainer.from_dict(flex_content)
                )
            ]
        )
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


