from flask import * 
from DB.userDB import *
from DB.productDB import *
import boto3

blueprint = Blueprint('s3', __name__, url_prefix='/s3' ,template_folder='templates')

# AWS S3 설정
S3_BUCKET = 'imagebucketfinalproject'
S3_REGION = 'ap-northeast-2'
s3 = boto3.client(
    's3', 
    region_name=S3_REGION
    )

def upload_file_to_s3(file, folder=''):
    try:
        file_name = f"{folder}/{file.filename}" if folder else file.filename
        s3.upload_fileobj(
            file,
            S3_BUCKET,
            file_name
        )
        file_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{file_name}"
        return file_url
    except Exception as e:
        print(f"파일 업로드 실패: {e}")
        return None
    
def delete_object(product_id):
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=product_id)
        if 'Contents' in response:  # 해당 디렉터리에 객체가 존재하는 경우
            for obj in response['Contents']:
                s3_key = obj['Key']
                # 객체 삭제
                s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
                flash(f"Deleted {s3_key} from S3.", "success")
        else:
            flash(f"No objects found under directory: {product_id}.", "info")
    except Exception as e:
        flash(f"Error deleting image from S3: {str(e)}", "danger")