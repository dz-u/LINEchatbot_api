KEY = 'KEY'#LINEbotKEY
WEBHOOK = 'WEBHOOKKEY'

import os
from flask import Flask, abort, request
from linebot.v3.webhook import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    QuickReply, QuickReplyItem, MessageAction
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
)

from openai import OpenAI


app = Flask(__name__)

handler = WebhookHandler(KEY)
configuration = Configuration(access_token=WEBHOOK)

import csv

# ユーザ属性を取得する関数
def get_columns_from_csv(file_path, search_value):
    with open(file_path, mode='r', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        header = next(csv_reader)  # ヘッダーを読み飛ばす
        for row in csv_reader:
            if row[0] == search_value:
                return row[1:5]
        return None  # 該当する値が見つからなかった場合

# セール中の商品を取得する関数    
def extract_sale_items(csv_file_path):
    sale_items = []

    # CSVファイルを読み込む
    with open(csv_file_path, mode = 'r',encoding = 'utf-8') as file:
        reader = csv.reader(file)
       # next(reader)
      
        for row in reader:
            product_name = row[0] 
            on_sale = row[3]       
            if on_sale == '1':
                sale_items.append(product_name)

    result = ','.join(sale_items)
    return result

def generate_text(user_info, sale_item, user_request):
    # クライアントインスタンスの生成。接続先の設定。
    client = OpenAI(
    api_key="aaaa",#api_key_openai
    base_url="aaaaaa"#URL
    )
    request_str = ""
    for r in user_request:
        request_str += "・"
        request_str += r

    cook_prompt = cook_prompt = f"""
    ###ユーザ属性
    年齢：{user_info[0]}, 性別：{user_info[1]}, 職業：{user_info[2]}, 家族構成：{user_info[3]}
    ###材料候補
    {sale_item}
    ###ユーザの要望
    {request_str}
    ###指示
       あなたは、料理を提案し、そのレシピを伝えるプロです。
        対称のユーザが好みそうな料理を一つ提案し、そのレシピをステップバイステップで説明してください。
        広く受け入れられている味のバランスを重視して材料の組み合わせを提案してください。また、ここに記載していない材料も使っても構いません。
    """
    #reply_text.append(TextMessage(text=cook_prompt))

    # GPTモデルのインスタンス作成。API呼び出し
    response = client.chat.completions.create(
    model="aaaa", # モデルの名前
    messages = [{"role":"user","content":cook_prompt}], # 入力するプロンプト
    temperature=0.7,                                                            # 出力のランダム度合い(可変)
    max_tokens=800,                                                             # 最大トークン数(固定)
    top_p=0.95,                                                                 # 予測する単語を上位何%からサンプリングするか(可変)
    frequency_penalty=0,                                                        # 単語の繰り返しをどのくらい許容するか(可変)
    presence_penalty=0,                                                         # 同じ単語をどのくらい使うか(可変)
    stop=None                                                                   # 文章生成を停止する単語を指定する(可変)
    )

    message_prompt = f"""
    #命令
    あなたは文章をわかりやすく人に伝えるプロです
        あなたに文章の構成に従ってお客様にメッセージを送信してもらいます。
        具体的な役割としては、提案された料理とそのレシピをお客様に送信し、料理に利用されているセール中の商品を
        レコメンドすることです。
        料理名とそのレシピを、わかりやすくお客様の属性に合う文で伝えてください。
    #文章の構成
    提案する料理名→使用する材料→レシピの手順→料理のおすすめポイント→セール商品
    ###提案した料理
    {response.choices[0].message.content.strip()}
    ###お客様属性
    年齢：{user_info[0]}, 性別：{user_info[1]}, 職業：{user_info[2]}, 家族構成：{user_info[3]}
    ###セール中の商品
    {sale_item}
    """

    # GPTモデルのインスタンス作成。API呼び出し
    message = client.chat.completions.create(
    model="aaaaaa",                                                  # モデルの名前
    messages = [{"role":"user","content":message_prompt}], # 入力するプロンプト
    temperature=0.7,                                                            # 出力のランダム度合い(可変)
    max_tokens=800,                                                             # 最大トークン数(固定)
    top_p=0.95,                                                                 # 予測する単語を上位何%からサンプリングするか(可変)
    frequency_penalty=0,                                                        # 単語の繰り返しをどのくらい許容するか(可変)
    presence_penalty=0,                                                         # 同じ単語をどのくらい使うか(可変)
    stop=None                                                                   # 文章生成を停止する単語を指定する(可変)
    )
    return message.choices[0].message.content.strip()



@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        #相手の送信した内容で条件分岐して回答を変数に代入
        global ask_age
        global ask_gender
        global ask_job
        global request_state
        global check
        global generate
        global user_info
        global user_request
        global sale_item
        global end
        input_text = event.message.text
        reply_text = []
        if input_text == "スタート":
            user_info = []
            user_request = []
            ask_age=True
            ask_gender=False
            ask_job = False
            request_state = False
            check = False
            generate=False
            reply_text.append(TextMessage(text="私は料理生成botです。"))
            ages = ["10代-20代", "30代-40代", "50代以上"]
            quickreply = QuickReply(items=[])  ## クイックリプライインスタンス化
            for age in ages:
                item = QuickReplyItem(action=MessageAction(label=age, text=age))
                quickreply.items.append(item)
            reply_text.append(TextMessage(text='年代を教えてください。', quickReply=quickreply))
        
        elif ask_age:
            ask_age=False
            ask_gender=True
            ask_job = False
            request_state = False
            check = False
            generate=False
            user_info.append(input_text)
            genders = ["男性", "女性"]
            quickreply = QuickReply(items=[])  ## クイックリプライインスタンス化
            for gender in genders:
                item = QuickReplyItem(action=MessageAction(label=gender, text=gender))
                quickreply.items.append(item)
            reply_text.append(TextMessage(text='性別を教えてください。', quickReply=quickreply))

        elif ask_gender:
            ask_age=False
            ask_gender=False
            ask_job = True
            request_state = False
            check = False
            generate=False
            user_info.append(input_text)
            jobs = ["学生", "社会人", "主婦"]
            quickreply = QuickReply(items=[])  ## クイックリプライインスタンス化
            for job in jobs:
                item = QuickReplyItem(action=MessageAction(label=job, text=job))
                quickreply.items.append(item)
            reply_text.append(TextMessage(text='職業を教えてください。', quickReply=quickreply))

        elif ask_job:
            ask_age=False
            ask_gender=False
            ask_job = False
            request_state = True
            first = True
            check = False
            generate = False
            user_info.append(input_text)
            family_types = ["独身", "夫婦のみ", "子供あり"]
            quickreply = QuickReply(items=[])  ## クイックリプライインスタンス化
            for type in family_types:
                item = QuickReplyItem(action=MessageAction(label=type, text=type))
                quickreply.items.append(item)
            reply_text.append(TextMessage(text='家族構成を教えてください。', quickReply=quickreply))

        elif request_state:
            user_info.append(input_text)
            ask_age=False
            ask_gender=False
            ask_job = False
            request_state = False
            check = True
            generate = False
            start = ["特になし"]
            quickreply = QuickReply(items=[])  ## クイックリプライインスタンス化
            for s in start:
                item = QuickReplyItem(action=MessageAction(label=s, text=s))
                quickreply.items.append(item)
            reply_text.append(TextMessage(text='生成する料理に要望があれば教えてください。無ければ「特になし」を押してください。', quickReply=quickreply))

        
        elif check:
            if "特になし" in user_request:
                user_request.remove('特になし')

            user_request.append(input_text)
            ask_age=False
            ask_gender=False
            ask_job = False
            request_state = False
            check = False
            generate = True
            start = ["生成開始"]
            quickreply = QuickReply(items=[])  ## クイックリプライインスタンス化
            for s in start:
                item = QuickReplyItem(action=MessageAction(label=s, text=s))
                quickreply.items.append(item)
            reply_text.append(TextMessage(text='「生成開始」を押してください。', quickReply=quickreply))


        elif generate:
            ask_age=False
            ask_gender=False
            ask_job = False
            request_state = False
            check = False
            generate = False
            end = True
            csv_file_path = './new_item_data.csv'
            sale_item = extract_sale_items(csv_file_path)
            cotomi_text = generate_text(user_info, sale_item, user_request)
            reply_text.append(TextMessage(text=cotomi_text))
            next_actions = ["再生成","終了"]
            quickreply = QuickReply(items=[])  ## クイックリプライインスタンス化
            for action in next_actions:
                item = QuickReplyItem(action=MessageAction(label=action, text=action))
                quickreply.items.append(item)
            reply_text.append(TextMessage(text='新たな要望を加えて料理を再生成したい場合は「再生成」を押してください。終了する場合は「終了」を押してください。', quickReply=quickreply))

        elif end:
            if input_text == "終了":
                ask_age=False
                ask_gender=False
                ask_job = False
                request_state = False
                check = False
                generate = False
                end = False
                reply_text.append(TextMessage(text='ご利用ありがとうございました。再びシステムをご利用になるには「スタート」と送信してください。'))
            
            elif input_text == "再生成":
                ask_age=False
                ask_gender=False
                ask_job = False
                request_state = False
                first = False
                check = True
                generate = False
                reply_text.append(TextMessage(text='再生成する料理の要望を教えてください。'))


            


        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=reply_text
            )
        )



if __name__ == "__main__":
    port = int(os.getenv("PORT", aaaa))#aaaa←ポート番号入力
    app.run(host="0.0.0.0", port=port, debug=False)