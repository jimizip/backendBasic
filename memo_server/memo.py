from http import HTTPStatus
import random
import urllib.parse
import requests
import json
import urllib
import string
import redis
import mysql.connector
from mysql.connector import Error

from flask import abort, Flask, make_response, render_template, Response, redirect, request

app = Flask(__name__)

# Redis 연결 설정
# redis_client = redis.Redis(host='localhost', port=6379, db=0)

naver_client_id = '2QaKzJI3Tl3ORWNtt7lq'
naver_client_secret = 'J8vYkmQIPD'
naver_redirect_uri = 'http://mjubackend.duckdns.org:10201/auth'
'''
  실습서버에서 사용할 경우 http://mjubackend.duckdns.org:본인포트번호/auth 로 하고,
  AWS 에 배포할 때는 http://본인로드밸런서의DNS주소/auth 로 할 것.
'''

@app.route('/')
def home():
    # HTTP 세션 쿠키를 통해 이전에 로그인 한 적이 있는지를 확인한다.
    # 이 부분이 동작하기 위해서는 OAuth 에서 access token 을 얻어낸 뒤
    # user profile REST api 를 통해 유저 정보를 얻어낸 뒤 'userId' 라는 cookie 를 지정해야 된다.
    # (참고: 아래 onOAuthAuthorizationCodeRedirected() 마지막 부분 response.set_cookie('userId', user_id) 참고)
    userId = request.cookies.get('userId', default=None)
    name = None

    ####################################################
    # TODO: 아래 부분을 채워 넣으시오.
    #       userId 로부터 DB 에서 사용자 이름을 얻어오는 코드를 여기에 작성해야 함
    # userId 쿠키가 설정되어 있는 경우 DB 에서 해당 유저의 이름을 읽어와서 index.html template 에 반영하는 동작

    if userId is not None:
        # user_id = redis_client.get(userId)
        name = get_user_name(userId)

    ####################################################


    # 이제 클라에게 전송해 줄 index.html 을 생성한다.
    # template 로부터 받아와서 name 변수 값만 교체해준다.
    return render_template('index.html', name=name)


# 로그인 버튼을 누른 경우 이 API 를 호출한다.
# 브라우저가 호출할 URL 을 index.html 에 하드코딩하지 않고,
# 아래처럼 서버가 주는 URL 로 redirect 하는 것으로 처리한다.
# 이는 CORS (Cross-origin Resource Sharing) 처리에 도움이 되기도 한다.
#
# 주의! 아래 API 는 잘 동작하기 때문에 손대지 말 것
@app.route('/login')
def onLogin():
    params={
            'response_type': 'code',
            'client_id': naver_client_id,
            'redirect_uri': naver_redirect_uri,
            'state': random.randint(0, 10000)
        }
    urlencoded = urllib.parse.urlencode(params)
    url = f'https://nid.naver.com/oauth2.0/authorize?{urlencoded}'
    return redirect(url)


# 아래는 Authorization code 가 발급된 뒤 Redirect URI 를 통해 호출된다.
@app.route('/auth')
def onOAuthAuthorizationCodeRedirected():
    # TODO: 아래 1 ~ 4 를 채워 넣으시오.

    # 1. redirect uri 를 호출한 request 로부터 authorization code 와 state 정보를 얻어낸다.
    params = request.args.to_dict()
    code = params.get('code')
    state = params.get('state')

    # 2. authorization code 로부터 access token 을 얻어내는 네이버 API 를 호출한다.

    params = {
        'grant_type': 'authorization_code',
        'client_id': naver_client_id,
        'client_secret': naver_client_secret,
        'code': code,
        'state': state,
    }

    unlencoded = urllib.parse.urlencode(params)
    token_request_url = f'https://nid.naver.com/oauth2.0/token?{unlencoded}'

    token_response = requests.get(token_request_url)
    token_data = token_response.json()
    access_token = token_data.get('access_token')

    # 3. 얻어낸 access token 을 이용해서 프로필 정보를 반환하는 API 를 호출하고,
    #    유저의 고유 식별 번호를 얻어낸다.
    profile_request = requests.get("https://openapi.naver.com/v1/nid/me", headers={'Authorization': f'Bearer {access_token}'})
    
    if profile_request.status_code == 200:
        profile_data = profile_request.json().get('response')
        user_id = profile_data.get('id')
        user_name = profile_data.get('name')
        print(f'아이디: {user_id}, 이름: {user_name}')

        # 4. 얻어낸 user id 와 name 을 DB 에 저장한다.
        # 5. 첫 페이지로 redirect 하는데 로그인 쿠키를 설정하고 보내준다.
        #    user_id 쿠키는 "dkmoon" 처럼 정말 user id 를 바로 집어 넣는 것이 아니다.
        #    그렇게 바로 user id 를 보낼 경우 정보가 노출되기 때문이다.
        #    대신 user_id cookie map 을 두고, random string -> user_id 형태로 맵핑을 관리한다.
        #      예: user_id_map = {}
        #          key = random string 으로 얻어낸 a1f22bc347ba3 이런 문자열
        #          user_id_map[key] = real_user_id
        #          user_id = key
        if user_id and user_name:
            # try:
            #     redis_client.set(user_id, user_name)
            # except redis.exceptions.ConnectionError:
            #     print("Redis 연결 실패. Redis 서버가 실행 중인지 확인하세요.")
            # random_key = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
            # redis_client.set(f"session:{random_key}", user_id, ex=3600)
            # response = redirect('/')
            # response.set_cookie('userId', random_key)
            # return response
            save_user(user_id, user_name)
            response = redirect('/')
            response.set_cookie('userId', user_id)
            return response
        else:
            print("Error: Unable to retrieve user information")
    else:
        print(f'Error: {profile_request.status_code}')
    
    return redirect('/')


@app.route('/memo', methods=['GET'])
def get_memos():
    # 로그인이 안되어 있다면 로그인 하도록 첫 페이지로 redirect 해준다.
    userId = request.cookies.get('userId', default=None)
    if not userId:
        return redirect('/')

    # TODO: DB 에서 해당 userId 의 메모들을 읽어오도록 아래를 수정한다.
    # user_id = redis_client.get(userId)
    if not userId:
        return redirect('/')
    # user_id = user_id.decode('utf-8')
    memos = get_memos(userId)
    # memos라는 키 값으로 메모 목록 보내주기
    # memos = redis_client.lrange(f"memos:{user_id}", 0, -1)
    # result = [memo.decode('utf-8') for memo in memos]
    return {'memos': memos}


@app.route('/memo', methods=['POST'])
def post_new_memo():
    # 로그인이 안되어 있다면 로그인 하도록 첫 페이지로 redirect 해준다.
    userId = request.cookies.get('userId', default=None)
    if not userId:
        return redirect('/')

    # 클라이언트로부터 JSON 을 받았어야 한다.
    if not request.is_json:
        abort(HTTPStatus.BAD_REQUEST)

    # TODO: 클라이언트로부터 받은 JSON 에서 메모 내용을 추출한 후 DB에 userId 의 메모로 추가한다.
    json_data = request.get_json()
    memo_text = json_data.get('text')
    
    if not memo_text:
        abort(HTTPStatus.BAD_REQUEST)
    
    # redis_client.rpush(f'memos: {userId}', memo_text)
    save_memo(userId, memo_text)

    return '', HTTPStatus.OK


if __name__ == '__main__':
    app.run('0.0.0.0', port=8000, debug=True)


def create_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            port='3306',
            database='memo_app',
            user='root',
            password='jimin204!'
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
    return None

db_connection = create_connection()

def save_user(user_id, user_name):
    try:
        cursor = db_connection.cursor()
        query = "INSERT INTO users (naver_user_id, name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name = %s"
        cursor.execute(query, (user_id, user_name, user_name))
        db_connection.commit()
    except Error as e:
        print(f"유저 저장 에러 발생: {e}")

def get_user_name(user_id):
    try:
        cursor = db_connection.cursor()
        query = "SELECT name FROM users WHERE naver_user_id = %s"
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Error as e:
        print(f"유저 이름 가져오기 에러: {e}")
    return None

def save_memo(user_id, memo_text):
    try:
        cursor = db_connection.cursor()
        query = "INSERT INTO memos (user_id, content) VALUES (%s, %s)"
        cursor.execute(query, (user_id, memo_text))
        db_connection.commit()
    except Error as e:
        print(f"메모 저장 에러: {e}")

def get_memos(user_id):
    try:
        cursor = db_connection.cursor()
        query = "SELECT content FROM memos WHERE user_id = %s ORDER BY created_at DESC"
        cursor.execute(query, (user_id,))
        return [row[0] for row in cursor.fetchall()]
    except Error as e:
        print(f"메모 가져오기 에러: {e}")
    return []