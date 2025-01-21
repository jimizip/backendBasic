# 실행환경

http://memo-60212160-279781320.ap-northeast-2.elb.amazonaws.com

http://memo-60212160-279781320.ap-northeast-2.elb.amazonaws.com/memo/

# 

# 필요 패키지 설치

`pip` 을 이용해 필요 패키지를 설치합니다.
(필요시 `virtualenv` 환경을 이용하세요.)

```
$ pip install -r requirements.txt
$ pip install flask mysql-connector-python python-dotenv requests
```

# 주요 기능

- Naver OAuth를 통한 사용자 로그인
- 로그인한 사용자의 메모 작성 및 조회
- MySQL 데이터베이스를 이용한 사용자 정보 및 메모 저장

# 기술 스택
- Python, Flask, Uwsgi, Nginx
- Database: MySQL
- Authentication: Naver OAuth 2.0

# AWS 인프라 구성
- EC2
- RDS
- Auto Scaling
- Elastic Load Balancing (ELB)
- Amazon Machine Images (AMI):
- EC2 Launch Templates

# index.html 이 호출하는 REST API 들

`index.html` 은 `memo.py` 에 다음 API 들을 호출합니다.

* `GET /login` : authorization code 를 얻어오는 URL 로 redirect 시켜줄 것을 요청합니다. (아래 [네이버 로그인 API 호출](#네이버-로그인-API-호출) 설명 참고)

* `GET /memo` : 현재 로그인한 유저가 작성한 메모 목록을 JSON 으로 얻어옵니다. 결과 JSON 은 다음과 같은 형태가 되어야 합니다.
  ```
  {"memos": ["메모내용1", "메모내용2", ...]}
  ```

* `POST /memo` : 새 메모를 추가합니다. HTTP 요청은 다음과 같은 JSON 을 전송해야 됩니다.
  ```
  {"text": "메모내용"}
  ```
  새 메모가 생성된 경우 memo.py 는 `200 OK` 를 반환합니다.

# 코드 설명

1. '/': 사용자의 세션 ID를 확인하고, 해당 사용자의 이름을 데이터베이스에서 조회하여 홈 페이지를 렌더링합니다. 로그인하지 않은 경우 로그인 버튼이 표시됩니다.
```
  sessionId = request.cookies.get('sessionId', default=None)
    name = None

    if sessionId is not None:
        db_connection.reconnect()
        query = 'SELECT u.name FROM user u JOIN sessions s ON u.id = s.user_id WHERE s.session_key = %s'
        cursor.execute(query, (sessionId,))
        result = cursor.fetchone()
        name = result[0] if result else None
```

2. '/auth': 인증 코드를 사용하여 액세스 토큰을 요청하고, 사용자 프로필 정보를 가져옵니다. 사용자 ID와 이름을 데이터베이스에 저장하고, 세션을 생성하여 쿠키에 저장합니다.
```
    # code 와 state 가져와 액세스 토큰 요청
    params = request.args.to_dict()
    code = params.get('code')
    state = params.get('state')

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

    profile_request = requests.get("https://openapi.naver.com/v1/nid/me", headers={'Authorization': f'Bearer {access_token}'})
    
    profile_data = profile_request.json()
    user_id = profile_data.get('response').get('id')
    user_name = profile_data.get('response').get('name')

    # 사용자 ID와 이름을 데이터베이스에 저장하고, 세션을 생성하여 쿠키에 저장
    if user_id and user_name:
        db_connection.reconnect()
        query = 'INSERT INTO user (id, name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name = %s'
        cursor.execute(query, (user_id, user_name, user_name))
        db_connection.commit()

        session_id = create_session(user_id)

        response = redirect('/')
        response.set_cookie('sessionId', session_id)
        return response
```
3. '/memo' (GET): 로그인한 사용자의 메모 목록을 조회합니다. 세션 ID를 통해 해당 사용자의 메모를 데이터베이스에서 가져와 JSON 형식으로 반환합니다.
```
    sessionId = request.cookies.get('sessionId', default=None)
    if not sessionId:
        return redirect('/')

    db_connection.reconnect()
    query = 'SELECT m.text FROM memo m JOIN sessions s ON m.user_id = s.user_id WHERE s.session_key = %s'
    cursor.execute(query, (sessionId,))
    memos = cursor.fetchall()
    
    result = []
    for row in memos:
        result.append({
            'text': row[0]
        })
    
    return {'memos': result}
```
4. '/memo' (POST): 요청 본문에서 메모 내용을 받아 데이터베이스에 저장합니다. 세션 ID를 통해 현재 로그인한 사용자의 ID를 확인하고, 해당 사용자에 대한 메모를 추가합니다.
```
    json_data = request.json
    memo_text = json_data.get('text')
    
    if not memo_text:
        abort(HTTPStatus.BAD_REQUEST)
    
    db_connection.reconnect()
    query = 'INSERT INTO memo (user_id, text) SELECT user_id, %s FROM sessions WHERE session_key = %s'
    cursor.execute(query, (memo_text, sessionId))
    db_connection.commit()
```

# 데이터 베이스 연결
- MySQL 데이터베이스와의 연결은 mysql.connector 라이브러리를 사용
  ```
    def create_connection():
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_DATABASE'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        return connection
  ```