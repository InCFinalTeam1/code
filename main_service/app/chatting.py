from flask import * 
from flask_socketio import *
from app import socketio
import boto3
import time 
from datetime import datetime

blueprint = Blueprint('chatting', __name__, url_prefix='/chatting' ,template_folder='templates')

# 클라이언트 ID별 채팅방 데이터 저장
clients = {
    "client1": [],
    "client2": []
}

kinesis_client = boto3.client(
    'kinesis', 
    region_name='ap-northeast-2'
)

stream_name = "final_chat_stream"

# 소켓 이벤트 핸들러: 특정 채팅방 참여
@socketio.on('join')
def handle_join(data):
    current_app.logger.info("대화창 접속")
    room = data['room']
    join_room(room)
    emit('status', {'msg': f"{session['login_info']['username']} 님이 {room}에 참여했습니다."}, room=room)

# 소켓 이벤트 핸들러: 메시지 전송
@socketio.on('message')
def handle_message(data):
    room = data['room']
    message = data['message']
    ptime = datetime.fromtimestamp(time.time())
    # 메시지 저장
    # clients[room].append({'user': session['login_info']['username'], 'message': message})
    
    #메시지 kinesis data stream으로 전송
    data = {
            'user': session['login_info']['username'],
            'message': message,
            'timestamp': str(ptime),
            'brand': room
    }
    try:
        response = kinesis_client.put_record(
            StreamName=stream_name,
            Data=json.dumps(data),
            PartitionKey=str(room)
        )
        print(f"Record sent: {response}")
    except Exception as e:
        print(f"Failed to send record to Kinesis: {e}")
        emit('error', {'msg': '메시지 전송에 실패했습니다.'}, room=room)
    
    # boardcast 
    emit('message', {'user': session['login_info']['username'], 'message': message}, room=room)

# 소켓 이벤트 핸들러: 특정 채팅방 나가기
@socketio.on('leave')
def handle_leave(data):
    current_app.logger.info("대화창 나감")
    room = data['room']
    leave_room(room)
    emit('status', {'msg': f"{session['login_info']['username']} 님이 {room}에서 나갔습니다."}, room=room)
