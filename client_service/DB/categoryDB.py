from flask import *
import boto3
from decimal import Decimal

dynamodb = boto3.resource(
    'dynamodb',
    region_name='ap-northeast-2'
)

table = dynamodb.Table('categories')

class categoryDao:
    def __init__(self):
        pass

    def get_all_categories(self):
        # 모든 요소 조회
        response = table.scan()
        categories = response['Items'] 
        return convert_decimal(categories)

    def insert_category(self, name):
        # DynamoDB에 사용자 데이터 삽입
        response = table.put_item(
            Item={
                'category_id': name
            }
        )

    def delete_category(self,category_id):
        response = table.delete_item(
            Key={
                'category_id': category_id  # 삭제할 항목의 기본 키
            }
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