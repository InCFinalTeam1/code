# Python 3.9 Slim 이미지를 기반으로 설정
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일 복사
COPY . .

# 의존성 설치
RUN pip install --no-cache-dir -r requirements.txt && chmod +x $(which gunicorn)

# Gunicorn으로 애플리케이션 실행
CMD ["gunicorn", "-b", "0.0.0.0:8000", "--worker-class", "eventlet", "wsgi:app"]
