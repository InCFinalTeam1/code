from flask import *
import boto3
from boto3.dynamodb.conditions import Attr
from decimal import Decimal

dynamodb = boto3.resource(
    'dynamodb',
    region_name='ap-northeast-2'
)

table = dynamodb.Table('clients')

class clientDao:
    def __init__(self):
        pass

    def get_all_clients(self):
        # 모든 요소 조회
        response = table.scan()
        clients = response['Items'] 
        return convert_decimal(clients)

    # 사용자 조회 (id와 password로 확인)
    def get_client(self, id, password):
        
        response = table.get_item(
            Key={
                'client_id': id  # client_id를 기본 키로 사용
            }
        )
       
        # 사용자 확인
        user = response.get('Item')
        if user and user.get('userpass') == password:
            return convert_decimal(user)
        return None
    
    def get_client_by_id(self, client_id):
        response = table.get_item(
            Key={
                'client_id': client_id
            }
        )

        # 사용자 정보 반환
        return convert_decimal(response.get('Item'))
    
    def insert_client(self, user_name, id, password, answer,email,phone,photo):
        # DynamoDB에 사용자 데이터 삽입
        response = table.put_item(
            Item={
                'client_id': id,
                'username': user_name,
                'userpass': password,
                'answer': answer,
                'email' : email,
                'phone' : phone,
                'photo' : photo
            }
        )
        return f"Insert OK: {response['ResponseMetadata']['HTTPStatusCode']}"

    def delete_client(self,client_id):
        response = table.delete_item(
            Key={
                'client_id': client_id  # 삭제할 항목의 기본 키
            }
        )
    
    def search_client_by_query(self, query):
        # 검색 쿼리를 처리하는 메서드
        # 검색 쿼리와 클라이언트 ID를 처리하는 메서드
        try:
            response = table.scan(
                FilterExpression=(
                    Attr('client_id').contains(query)
                )
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"Error searching products by query and client: {e}")
            return []
        
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