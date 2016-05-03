# -*- coding: utf-8 -*-
# implemented by dr_asa
# other codes are also available on GitHub (https://github.com/asashiho)

import json
import falcon
import requests
from logging import DEBUG, StreamHandler, getLogger

# logger
logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)

# LINEのアクセスキーとエンドポイント
LINE_CHANNELID = os.environ.get('LINE_CHANNELID', '')
LINE_CHANNELSEC = os.environ.get('LINE_CHANNELSEC', '')
LINE_MID = os.environ.get('LINE_MID', '')
LINE_URI = 'https://trialbot-api.line.me/v1/events'

# DocomoAPIのアクセスキーとエンドポイント
DOCOMO_API_KEY = os.environ.get('DOCOMO_API_KEY', '')
DIALOG_URL = 'https://api.apigw.smt.docomo.ne.jp/dialogue/v1/dialogue?APIKEY=' + DOCOMO_API_KEY


#雑談結果を取得 (DocomoAPI 雑談対話)
def getDialogue( utt ):

    url = DIALOG_URL
    payload = {
        'utt': utt,
        'context': '',
        'nickname': 'miya',
        'nickname_y': 'みや',
        'sex': '女',
        'bloodtype': 'AB',
        'birthdateY': '1995',
        'birthdateM': '5',
        'birthdateD': '31',
        'age': '20',
        'constellations': '双子座',
        'place': '横浜',
        'mode': 'dialog',
    }
    r = requests.post(url, data=json.dumps(payload))

    return r.json()['utt']


# LINE BOTからのcallback処理を行うクラス
class CallbackResource(object):
    # LINE送信用ヘッダ
    header = {
        'Content-Type': 'application/json; charset=UTF-8',
        'X-Line-ChannelID': LINE_CHANNELID,
        'X-Line-ChannelSecret': LINE_CHANNELSEC,
        'X-Line-Trusted-User-With-ACL': LINE_MID,
    }

    def on_post(self, req, resp):


        # 受けとったメッセージの読み込み
        body = req.stream.read()
        if not body:
            raise falcon.HTTPBadRequest('Empty request body',
                                        'A valid JSON document is required.')

        receive_params = json.loads(body.decode('utf-8'))

        for msg in receive_params['result']:

            # 送信されたデータの種類（
            #1:Text,2:Image,3:Video,4:Audio,7:Location,8:Sticker,10:Contact）
            id = msg['content']['id']

            # Docomo雑談対話APIの呼び出し
            diagMsg = getDialogue(msg['content']['text'])
            
            # LINE送信データの生成（雑談結果を返す）
            send_content = {
                'to': [msg['content']['from']],
                'toChannel': 1383378250,  # 固定値（API仕様）
                'eventType': '138311608800106203',  # 固定値（API仕様）
                'content': {
                    'contentType': 1,
                    'toType': 1,
                    'text': diagMsg,
                },
            }
            send_content = json.dumps(send_content)
            logger.debug('send_content: {}'.format(send_content))

            # LINE送信
            res = requests.post(LINE_URI, data=send_content, headers=self.header)
            logger.debug('res: {} {}'.format(res.status_code, res.reason))

            resp.body = json.dumps('line-ok')

# ELBヘルスチェック用
class HelthResource(object):
    def on_get(self, req, resp):
        resp.body = json.dumps('heartbeat')

# Webサーバのルーティング設定
app = falcon.API()
app.add_route('/', HelthResource())
app.add_route('/callback', CallbackResource())

# メイン処理
if __name__ == '__main__':
    # Webサーバ起動
    from wsgiref import simple_server
    httpd = simple_server.make_server('',80,app)
    httpd.serve_forever()
