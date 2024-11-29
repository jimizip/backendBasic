from http import HTTPStatus
import random
import urllib.parse
import requests
import json
import urllib
import string
import mysql.connector
import secrets
from dotenv import load_dotenv
import os
import logging
import uuid

load_dotenv()

from flask import abort, Flask, make_response, render_template, Response, redirect, request, session

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())  # Flask 세션을 위한 비밀 키 설정

# 로깅 설정
logging.basicConfig(level=logging.INFO)

naver_client_id = os.getenv('NAVER_CLIENT_ID')
naver_client_secret = os.getenv('NAVER_CLIENT_SECRET')
naver_redirect_uri = os.getenv('NAVER_REDIRECT_URI')

def create_connection():
    connection = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_DATABASE'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    return connection

db_connection = create_connection()
cursor = db_connection.cursor(dictionary=True)

@app.route('/')
def home():
    user_id = session.get('user_id')
    name = None

    if user_id:
        try:
            db_connection.reconnect()
            query = 'SELECT name FROM user WHERE id=%s'
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            if result:
                name = result['name']
        except mysql.connector.Error as err:
            logging.error(f"Database error: {err}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")

    return render_template('index.html', name=name)

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

@app.route('/auth')
def onOAuthAuthorizationCodeRedirected():
    try:
        params = request.args.to_dict()
        code = params.get('code')
        state = params.get('state')

        token_params = {
            'grant_type': 'authorization_code',
            'client_id': naver_client_id,
            'client_secret': naver_client_secret,
            'code': code,
            'state': state,
        }

        token_url = 'https://nid.naver.com/oauth2.0/token'
        token_response = requests.get(token_url, params=token_params)
        token_data = token_response.json()
        access_token = token_data.get('access_token')

        profile_url = "https://openapi.naver.com/v1/nid/me"
        headers = {'Authorization': f'Bearer {access_token}'}
        profile_response = requests.get(profile_url, headers=headers)
        profile_data = profile_response.json()

        user_id = profile_data['response']['id']
        user_name = profile_data['response']['name']

        db_connection.reconnect()
        
        # 사용자 정보 업데이트 또는 삽입
        query = '''
        INSERT INTO user (id, name) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE name = %s
        '''
        cursor.execute(query, (user_id, user_name, user_name))
        db_connection.commit()

        # 세션에 사용자 정보 저장
        session['user_id'] = user_id
        session['user_name'] = user_name

        return redirect('/memo/')

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return "로그인 처리 중 오류가 발생했습니다.", 500
    except mysql.connector.Error as err:
        logging.error(f"Database error: {err}")
        return "데이터베이스 오류가 발생했습니다.", 500
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return "예기치 않은 오류가 발생했습니다.", 500

@app.route('/memo', methods=['GET'])
def get_memos():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/')

    try:
        db_connection.reconnect()
        query = 'SELECT text FROM memo WHERE user_id=%s'
        cursor.execute(query, (user_id,))
        memos = cursor.fetchall()
        return {'memos': [memo['text'] for memo in memos]}
    except mysql.connector.Error as err:
        logging.error(f"Database error: {err}")
        return "데이터베이스 오류가 발생했습니다.", 500
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return "예기치 않은 오류가 발생했습니다.", 500

@app.route('/memo', methods=['POST'])
def post_new_memo():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/')

    if not request.is_json:
        abort(HTTPStatus.BAD_REQUEST)

    try:
        json_data = request.json
        memo_text = json_data.get('text')
        
        if not memo_text:
            abort(HTTPStatus.BAD_REQUEST)
        
        db_connection.reconnect()
        query = 'INSERT INTO memo (user_id, text) VALUES (%s, %s)'
        cursor.execute(query, (user_id, memo_text))
        db_connection.commit()

        return '', HTTPStatus.OK
    except mysql.connector.Error as err:
        logging.error(f"Database error: {err}")
        return "데이터베이스 오류가 발생했습니다.", 500
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return "예기치 않은 오류가 발생했습니다.", 500

if __name__ == '__main__':
    app.run('0.0.0.0', port=8000, debug=True)