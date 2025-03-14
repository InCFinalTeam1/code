from flask import * 
from DB.userDB import *
from DB.clientDB import *
from DB.s3 import *
import json
import urllib3
import os
import boto3

blueprint = Blueprint('user', __name__, url_prefix='/user' ,template_folder='templates')
lambda_client = boto3.client('lambda', region_name='ap-northeast-2')

# 로그인 기능
@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        auth_mainservice_url = current_app.config['AUTH_MAINSERVICE_URL']
        auth_clientservice_url = current_app.config['AUTH_CLIENTSERVICE_URL']
        auth_analyze_url = current_app.config['AUTH_ANALYZE_URL']
        username = request.form['username']
        password = request.form['password']
        if request.form['is_influencer'] == 'no':
            # 사용자 정보 조회
            user = UserDao().get_user(username, password)
            
            if user:  # 사용자가 존재할 경우
                session['login_info'] = user  # 로그인 정보 세션에 저장
                flash('로그인 성공!')  # 로그인 성공 메시지
                current_app.logger.info(user['user_id']+ " 사용자님 로그인")
                # return redirect(url_for('influ.influ',clients=clients))  # => 리디렉션 처리
                return redirect(f'{auth_mainservice_url}/influ/flu')  # => 리디렉션 처리
            else:
                flash('로그인 실패. 사용자 이름 또는 비밀번호를 확인하세요.')  # 오류 메시지
                return redirect(url_for('user.login'))  # 로그인 실패 시 로그인 페이지로 이동
        else:
            client = clientDao().get_client(username, password)
            if client:  # 사용자가 존재할 경우
                session['login_info'] = client  # 로그인 정보 세션에 저장
                flash('로그인 성공!')  # 로그인 성공 메시지
                current_app.logger.info(client['client_id']+ " 클라이언트님 로그인")
                return redirect(f'{auth_analyze_url}/analyze')  # => 리디렉션 처리
            else:
                flash('로그인 실패. 사용자 이름 또는 비밀번호를 확인하세요.')  # 오류 메시지
                return redirect(url_for('user.login'))  # 로그인 실패 시 로그인 페이지로 이동
        
    return render_template('login.html')

# 로그아웃
@blueprint.route('/logout')
def logout():
    auth_mainservice_url = current_app.config['AUTH_MAINSERVICE_URL']
    if 'login_info' in session:
        # current_app.logger.info(session['login_info']+ " 님 로그아웃")
        session.pop('login_info', None)
        # session.pop('user_id', None)
        flash('로그아웃 되었습니다.')  # 로그아웃 메시지
    return redirect(f'{auth_mainservice_url}/influ/flu')

# 회원가입
@blueprint.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        current_app.logger.info("회원가입 시도")
        id = request.form['user_id']
        password = request.form['UserPw']
        confirm_password = request.form['UserPwConfirm']
        user_name = request.form['UserName']
        answer = request.form['FindPwAnswer']

        if password != confirm_password:
            flash('비밀번호가 일치하지 않습니다.')
            return redirect(url_for('user.signup'))
        
        if request.form['is_influencer'] == 'no':
            user_dao = UserDao()
            existing_user = user_dao.get_user_by_id(id)
        else:
            user_dao = clientDao()
            existing_user = user_dao.get_client_by_id(id)
            
        if existing_user:
            flash('이미 사용 중입니다. 다른 값을 넣어주세요.')
            return redirect(url_for('user.signup'))
        
        if request.form['is_influencer'] == 'no':
            result = user_dao.insert_user(user_name, id, password, answer)
        else:
            phone = request.form['influencerPhone']
            email = request.form['influencerEmail']
            photo = request.files['influencerPhoto']
            photo_url = upload_file_to_s3(photo, user_name)
            result = user_dao.insert_client(user_name, id, password, answer,email,phone,photo_url)
            # Lambda 호출 (SNS를 통해 Slack 알림 전송)
            lambda_payload = {
                "Records": [{
                    "Sns": {
                        "Message": json.dumps({
                            "user_name": user_name,
                            "id": id,
                            "email": email,
                            "phone": phone
                        })
                    }
                }]
            }
            
            lambda_client.invoke(
                FunctionName="slack_notification",
                InvocationType="Event",
                Payload=json.dumps(lambda_payload)
            )
 
        if 'Insert OK' in result:
            flash('회원가입이 완료되었습니다.')
            current_app.logger.info("회원 가입 성공")
            return redirect(url_for('user.login'))
        else:
            flash('FATAL ERROR !')
            current_app.logger.warning("회원가입 실패")
            return redirect(url_for('user.main'))

    return render_template('signup.html')

@blueprint.route('/check_duplicate', methods=['POST'])
def check_duplicate():
    data = request.get_json()  # 클라이언트에서 보낸 JSON 데이터
    user_id = data.get("user_id")
    
    existing_user = UserDao().get_user_by_id(user_id)
    if existing_user:
        return jsonify({"status": "error", "message": "이미 등록된 아이디입니다."})
    else:
        return jsonify({"status": "success", "message": "사용 가능한 아이디입니다."})
