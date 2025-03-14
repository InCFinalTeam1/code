import boto3
import json
import time
from decimal import Decimal

kinesis_client = boto3.client(
    'kinesis', 
    region_name='ap-northeast-2'
)

stream_name = "mini3-data-stream"

dynamodb = boto3.resource(
    'dynamodb',
    region_name='ap-northeast-2'
)

table = dynamodb.Table('sales')

class salesdataDao:

    def __init__(self):
        pass

    def get_quantity_by_id(self, product_id):
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Key('product_id').eq(product_id)  # product_id 필터링
        )
        p_num = response['Items'][0]['quantity']
        return convert_decimal(p_num)

    def insert_data(self, product_id):
        # DynamoDB에 사용자 데이터 삽입
        response = table.put_item(
            Item={
                'product_id': product_id,  # product_id를 기본 키로 사용
                'quantity': 0
            }
        )

        return f"Insert OK: {response['ResponseMetadata']['HTTPStatusCode']}"
    
    def delete_product(self,product_id):
        response = table.delete_item(
            Key={
                'product_id': product_id  # 삭제할 항목의 기본 키
            }
        )

    # 판매 데이터 전송 함수
    def send_sales_data(self, product_id, quantity):
        data = {
            "product_id": product_id,
            "quantity": quantity
        }
        response = kinesis_client.put_record(
            StreamName=stream_name,
            Data=json.dumps(data),
            PartitionKey=str(product_id)  # 샤드 분배를 위한 키
        )
        print(f"Record sent: {response}")

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
# # 판매 데이터 샘플 전송
# if __name__ == "__main__":
#     for i in range(4):  # 10개의 판매 데이터 전송
#         salesdataDao().send_sales_data(product_id=f"test1", quantity=1)
#         time.sleep(10)  # 1초 간격