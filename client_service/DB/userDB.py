from flask import *
import boto3
from decimal import Decimal

dynamodb = boto3.resource(
    'dynamodb',
    region_name='ap-northeast-2'
)

table = dynamodb.Table('users')

class UserDao:
    def __init__(self):
        pass

    def get_all_users(self):
        # 모든 요소 조회
        response = table.scan()
        users = response['Items'] 
        return convert_decimal(users)
    
    # 사용자 조회 (id와 password로 확인)
    def get_user(self, id, password):
        
        response = table.get_item(
            Key={
                'user_id': id  # user_id를 기본 키로 사용
            }
        )
       
        # 사용자 확인
        user = response.get('Item')
        if user and user.get('userpass') == password:
            return convert_decimal(user)
        return None
    
    # 사용자 정보 ID로 조회 (마이페이지에서 사용)
    def get_user_by_id(self, user_id):
        response = table.get_item(
            Key={
                'user_id': user_id
            }
        )

        # 사용자 정보 반환
        return convert_decimal(response.get('Item'))
    
    def insert_user(self, user_name, id, password, answer, cart=[]):
        # DynamoDB에 사용자 데이터 삽입
        response = table.put_item(
            Item={
                'user_id': id,  # user_id를 기본 키로 사용
                'username': user_name,
                'userpass': password,
                'answer': answer,
                'cart' : []
            }
        )

        return f"Insert OK: {response['ResponseMetadata']['HTTPStatusCode']}"

    def get_current_user(self):
        user_id = session.get('user_id')  # 세션에서 사용자 ID를 가져옴
        if user_id:
            return convert_decimal(self.get_user_by_id(user_id))  # 사용자 ID로 사용자 정보 조회
        return None

    def get_cart_by_id(self,user_id):
        response = table.get_item(
            Key={
                'user_id': user_id  # user_id를 기본 키로 사용
            }
        )
        # cart 확인
        cart = response.get('Item').get('cart')
        
        if cart == None: 
            cart = []

        return convert_decimal(cart)
    
    def update_cart(self,user_id,product_id, quantity):
        # 장바구니 업데이트
        try:
            # 현재 장바구니 가져오기
            response = table.get_item(Key={'user_id': user_id})
            cart = response.get('Item').get('cart')
         
            # 장바구니 항목 업데이트
            updated_cart = []
            item_found = False
            
            for item, curr_quantity in cart:
                item_name = item
                if item_name == product_id:
                    # 해당 상품의 수량 업데이트
                    curr_quantity = quantity
                    item_found = True
                updated_cart.append([item,curr_quantity])
            if not item_found:
                # 상품이 없으면 새로 추가
                updated_cart.append([product_id, Decimal(quantity)])
            
            # 업데이트된 장바구니 저장
            response = table.update_item(
                Key={'user_id': user_id},
                UpdateExpression="SET cart = :updated_cart",
                ExpressionAttributeValues={
                    ':updated_cart': updated_cart
                },
                ReturnValues="UPDATED_NEW"
            )
            flash("장바구니에 상품이 변경되었습니다.")
            return convert_decimal(response)
        except Exception as e:
            print(f"장바구니 업데이트 오류: {e}")
            flash("장바구니 추가에 실패했습니다.")

    def remove_from_cart(self, user_id, product_id):
        # 장바구니 업데이트
        try:
            # 현재 장바구니 가져오기
            response = table.get_item(Key={'user_id': user_id})
            cart = response.get('Item').get('cart')
            
            # 장바구니 항목 업데이트
            updated_cart = []
            for item, curr_quantity in cart:
                item_name = item
                if item_name == product_id:
                    continue
                updated_cart.append([item,Decimal(curr_quantity)])
           
            # 업데이트된 장바구니 저장
            response = table.update_item(
                Key={'user_id': user_id},
                UpdateExpression="SET cart = :updated_cart",
                ExpressionAttributeValues={
                    ':updated_cart': updated_cart
                },
                ReturnValues="UPDATED_NEW"
            )
            flash("장바구니에 상품이 삭제되었습니다.")
            return response
        except Exception as e:
            print(f"장바구니 업데이트 오류: {e}")
            flash("장바구니 삭제에 실패했습니다.")

    def remove_all_from_cart(self, user_id):
        response = table.get_item(Key={'user_id': user_id})
        # 업데이트된 장바구니 저장
        response = table.update_item(
            Key={'user_id': user_id},
            UpdateExpression="SET cart = :updated_cart",
            ExpressionAttributeValues={
                ':updated_cart': []
            },
            ReturnValues="UPDATED_NEW"
        )

def convert_decimal(data):
    """DynamoDB에서 반환된 데이터를 JSON 직렬화 가능하게 변환"""
    if isinstance(data, list):
        return [convert_decimal(item) for item in data]
    elif isinstance(data, dict):
        return {k: convert_decimal(v) for k, v in data.items()}
    elif isinstance(data, Decimal):
        return float(data)  # 또는 str(data)
    else:
        return data