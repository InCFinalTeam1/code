from flask import *
import boto3
from decimal import Decimal
# from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource(
    'dynamodb',
    region_name='ap-northeast-2'
)

table = dynamodb.Table('orders')

class orderDao:
    def __init__(self):
        pass

    def get_all_orders(self):
        # 모든 요소 조회
        response = table.scan()
        orders = response['Items'] 
        return convert_decimal(orders)
    
    def put_order(self,order):
        response = table.put_item(
            Item=order
        )
    
    def get_orders_by_id(self,user_id):
        # user_id에 해당하는 아이템만 조회
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)  # user_id 필터링
        )
        orders = response['Items']
        return convert_decimal(orders)
    
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