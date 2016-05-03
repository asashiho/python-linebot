# -*- coding: utf-8 -*-
# implemented by dr_asa
# other codes are also available on GitHub (https://github.com/asashiho)

import json
import falcon
import requests
from logging import DEBUG, StreamHandler, getLogger
from PIL import Image
from StringIO import StringIO

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
IMGRECG_URI = 'https://api.apigw.smt.docomo.ne.jp/imageRecognition/v1/recognize'

#画像データを送信し、カテゴリの候補上位1つを取得 
#(DocomoAPI 画像認識)
def getImageInfo(imageFile, recog):

    #register_openers()
    f = open(imageFile, 'rb')

    result = requests.post(
        url = IMGRECG_URI,
        params={'APIKEY': DOCOMO_API_KEY, 'recog': recog, 'numOfCandidates': 1},
        data=f,
        headers={'Content-Type': 'application/octet-stream'},
    )
    logger.debug(result.status_code)
    logger.debug(result.url)
    respdata =result.text

    # jsonデータの'candidates'を返す
    return json.loads(respdata)['candidates']

#LINEから画像データを取得
def getImageLine( id ):

    line_url = 'https://trialbot-api.line.me/v1/bot/message/'+ id +'/content/'
    
    # 画像取得のためのLINE送信用ヘッダ
    header = {
        'Content-type': 'application/json; charset=UTF-8',
        'X-Line-ChannelID': LINE_CHANNELID,
        'X-Line-ChannelSecret': LINE_CHANNELSEC,
        'X-Line-Trusted-User-With-ACL': LINE_MID,
    }

    # 画像の取得
    result = requests.get(line_url, headers=header)

    # 画像の保存
    i = Image.open(StringIO(result.content))
    filename = '/tmp/' + id + '.jpg'
    i.save(filename)

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

        # LINE受信データの読み込み
        body = req.stream.read()
        if not body:
            raise falcon.HTTPBadRequest('Empty request body',
                                        'A valid JSON document is required.')

        receive_params = json.loads(body.decode('utf-8'))

        # LINE受信パラメータの取り出し
        for msg in receive_params['result']:

            # LINEから画像取得して保存
            id = msg['content']['id']
            logger.debug('messageID:')
            logger.debug(msg['content']['id'])
            getImageLine( id )

            # 画像ファイル名, カテゴリの設定
            image = '/tmp/'+id+'.jpg'
            recog = 'cd'

            # 画像認識APIの呼出し
            candidate = getImageInfo(image, recog)

            # 画像認識結果を取得し、LINEに返信する
            for can in candidate:

                # アーティスト名の取得
                artist =can['detail']['artist']

                result = can['detail']['itemName'] + '\n' \
                       + can['detail']['releaseDate'] + '\n' \
                       + artist[0].encode('utf-8') + '\n' \
                       + can['detail']['label']

                # LINE送信データの生成
                send_content = {
                    'to': [msg['content']['from']],
                    'toChannel': 1383378250,  # 固定値（API仕様）
                    'eventType': '138311608800106203',  # 固定値（API仕様）
                    'content': {
                        'contentType': 1,
                        'toType': 1,
                        'text': result,
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
