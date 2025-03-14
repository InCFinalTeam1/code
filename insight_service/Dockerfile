# Base image (Python 3.9 사용)
FROM python:3.9

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일 복사
COPY . .

# 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# Streamlit 실행 (포트 8501 사용)
CMD ["streamlit", "run", "streamlit_app.py"]
