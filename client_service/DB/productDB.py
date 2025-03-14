from flask import *
import boto3
from boto3.dynamodb.conditions import Attr
from decimal import Decimal

dynamodb = boto3.resource(
    'dynamodb',
    region_name='ap-northeast-2'
)

table = dynamodb.Table('products')

class ProductDao:
    def __init__(self):
        pass

    def get_all_products(self):
        # 모든 요소 조회
        response = table.scan()
        products = response['Items'] 
        return convert_decimal(products)
    
    def get_product(self, product_id):
        response =  table.get_item(
            Key={
                'product_id': product_id
            }
        )   
        product_detail = response.get('Item')
        return convert_decimal(product_detail)
    
    def get_products_by_client(self, client_id):
        try:
            # client_id를 기준으로 제품 필터링
            response = table.scan(
                FilterExpression=Attr('client_id').eq(client_id)
            )
            products = response.get('Items', [])
            return convert_decimal(products)
        except Exception as e:
            print("Error fetching products by client:", str(e))
            return []
    
    def search_products_by_query_and_client(self, query, client_id):
        # 검색 쿼리를 처리하는 메서드
        # 검색 쿼리와 클라이언트 ID를 처리하는 메서드
        try:
            response = table.scan(
                FilterExpression=(
                    Attr('product_id').contains(query) & Attr('client_id').eq(client_id)
                )
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"Error searching products by query and client: {e}")
            return []
    
    def insert_product(self, id, price,description, client_id,category_id, image):

        # DynamoDB에 사용자 데이터 삽입
        response = table.put_item(
            Item={
                'product_id': id, 
                'price': price,
                'description': description,
                'client_id':client_id,
                'category_id':category_id,
                'image_path': image
            }
        )

    def delete_product(self,product_id):
        response = table.delete_item(
            Key={
                'product_id': product_id  # 삭제할 항목의 기본 키
            }
        )

    def update_product(self, product_id, price, description, client_id, category_id, image):
        try:
            response = table.update_item(
                Key={
                    'product_id': product_id
                },
                UpdateExpression="SET image=:i, price=:p, description=:d,client_id=:c, category_id=:a",
                ExpressionAttributeValues={
                    ':i': str(image),  # image 값을 문자열로 처리
                    ':p': int(price),  # price를 정수로 변환
                    ':d': str(description),  # description 값을 문자열로 처리
                    ':c': str(client_id), 
                    ':a': str(category_id) 
                },
                ReturnValues="UPDATED_NEW"  # 업데이트된 항목 반환 (선택사항)
            )
            print("Update successful:", response)
            return response
        except Exception as e:
            print("Error updating product:", str(e))
            raise

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