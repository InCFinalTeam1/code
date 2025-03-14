import json
import time
import random
from wsgi import app

def test_checkout(cart_items):
    client = app.test_client()  # Flask 테스트 클라이언트 생성
    with client.session_transaction() as session:
        session['login_info'] = {'user_id': 'user1'}  # 세션 데이터 설정

    response = client.post('/bucket/checkout', data={
        'cart_items': str(cart_items)
    })

    print("Response data:", response.data.decode())
    assert response.status_code == 302  # 리다이렉트 성공 여부 확인

items = [
        [
            {'product_name': '소품', 'price': 9500, 'quantity': 1, 'image_path': 'https://imagebucketfinalproject.s3.ap-northeast-2.amazonaws.com/%EC%95%84%EC%9D%B4%ED%8C%A8%EB%93%9C+%ED%94%84%EB%A1%9C/%EC%95%84%EC%9D%B4%ED%8C%A8%EB%93%9C.jpg'}
        ],
        [
            {'product_name': '초록모자', 'price': 20000, 'quantity': 1, 'image_path': 'https://imagebucketfinalproject.s3.ap-northeast-2.amazonaws.com/%EC%95%84%EC%9D%B4%ED%8C%A8%EB%93%9C+%ED%94%84%EB%A1%9C/%EC%95%84%EC%9D%B4%ED%8C%A8%EB%93%9C.jpg'}
        ],
        [
            {'product_name': '안경', 'price': 200000, 'quantity': 1, 'image_path': 'https://imagebucketfinalproject.s3.ap-northeast-2.amazonaws.com/%EC%95%84%EC%9D%B4%ED%8C%A8%EB%93%9C+%ED%94%84%EB%A1%9C/%EC%95%84%EC%9D%B4%ED%8C%A8%EB%93%9C.jpg'}
        ],
        [
            {'product_name': '커피', 'price': 7000, 'quantity': 1, 'image_path': 'https://imagebucketfinalproject.s3.ap-northeast-2.amazonaws.com/%EC%95%84%EC%9D%B4%ED%8C%A8%EB%93%9C+%ED%94%84%EB%A1%9C/%EC%95%84%EC%9D%B4%ED%8C%A8%EB%93%9C.jpg'}
        ]
    ]

# 판매 데이터 샘플 전송
if __name__ == "__main__":

    while True:
        random_item = random.choice(items) 
        json_str = json.dumps(random_item , ensure_ascii=False)
        # 테스트 실행 3초 마다 랜덤으로 주문
        test_checkout(json_str)
        # time.sleep(3)