import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import boto3
import json
import os
import time
import re
from collections import Counter
from typing import Dict, Optional, List, Tuple

def extract_value(d):
    """DynamoDB 값 추출 헬퍼 함수"""
    if isinstance(d, dict):
        key = list(d.keys())[0]
        if key == 'N':
            return int(d[key])
        elif key == 'S' and d[key].replace('.', '').isdigit():
            return int(float(d[key]))
        return d[key]
    return d

def parse_cart_items(cart_items, product_dict):
    """장바구니 아이템을 파싱하고 총액을 계산"""
    parsed_items = []
    total_quantity = 0
    total_price = 0
    
    try:
        # cart_items의 다양한 형태, 처리
        if isinstance(cart_items, dict):
            if 'L' in cart_items:
                cart_items = cart_items['L']
            else:
                cart_items = [cart_items]
        elif not isinstance(cart_items, list):
            cart_items = [cart_items]
        
        for item in cart_items:
            # item이 딕셔너리인지 확인
            if isinstance(item, dict):
                # 중첩된 리스트 또는 딕셔너리 처리
                if 'L' in item:
                    item = item['L']
                
                # 다양한 형태의 product_id 추출
                if isinstance(item, list):
                    product_id = extract_value(item[0]) if item else None
                    quantity = extract_value(item[1]) if len(item) > 1 else 1
                elif isinstance(item, dict):
                    product_id = extract_value(item.get('product_id', item.get('id')))
                    quantity = extract_value(item.get('quantity', 1))
                else:
                    continue
            else:
                # 단순 값인 경우
                product_id = extract_value(item)
                quantity = 1
            
            # 상품 가격 추출
            product_price = product_dict.get(product_id, 0)
            
            # 0으로 나누는 것 방지
            if isinstance(product_price, dict):
                product_price = product_price.get('price', 0)
            
            item_total = quantity * product_price
            
            parsed_items.append({
                'product_id': product_id,
                'quantity': quantity,
                'price': product_price,
                'item_total': item_total
            })
            total_quantity += quantity
            total_price += item_total
    
    except Exception as e:
        print(f"❌ 장바구니 처리 중 오류: {str(e)}")
        print(f"현재 item: {item}")
        print(f"Product Dict: {product_dict}")
    
    return parsed_items, total_quantity, total_price

class AthenaManager:
    def __init__(self):
        self.region = 'ap-northeast-2'
        self.athena_client = boto3.client('athena', region_name=self.region)
        self.database = 'test'  # Athena 데이터베이스 이름
        self.output_location = 's3://final-chat-data/athena_result/'  # 쿼리 결과 저장 위치
        self.table_name = 'logs'  # 테이블명이 "logs"인지 확인
        
    def run_query(self, query):
        """Athena 쿼리 실행 및 결과 반환"""
        try:
            
            response = self.athena_client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={
                    'Database': self.database
                },
                ResultConfiguration={
                    'OutputLocation': self.output_location
                }
            )
            
            query_execution_id = response['QueryExecutionId']
            
            # 쿼리 완료 대기
            state = 'RUNNING'
            while (state == 'RUNNING' or state == 'QUEUED'):
                response = self.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
                state = response['QueryExecution']['Status']['State']
                
                if state == 'FAILED' or state == 'CANCELLED':
                    st.error(f"쿼리 실행 실패: {response['QueryExecution']['Status']['StateChangeReason']}")
                    return pd.DataFrame()
                    
                time.sleep(1)  # 1초 대기
            
            # 결과 가져오기
            results = self.athena_client.get_query_results(QueryExecutionId=query_execution_id)
            
            # 결과를 데이터프레임으로 변환
            if 'ResultSet' in results and 'Rows' in results['ResultSet']:
                columns = [col['Label'] for col in results['ResultSet']['ResultSetMetadata']['ColumnInfo']]
                rows = []
                
                # 첫 번째 행(헤더)을 제외하고 데이터 추출
                for row in results['ResultSet']['Rows'][1:]:
                    data = []
                    for datum in row['Data']:
                        if 'VarCharValue' in datum:
                            data.append(datum['VarCharValue'])
                        else:
                            data.append(None)
                    rows.append(data)
                
                df = pd.DataFrame(rows, columns=columns)
                return df
            else:
                return pd.DataFrame()
        
        except Exception as e:
            st.error(f"Athena 쿼리 오류 상세: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return pd.DataFrame()
        
    def refresh_table_metadata(self):
        """테이블 메타데이터 새로고침"""
        query = f"MSCK REPAIR TABLE {self.table_name}"
        try:
            self.run_query(query)
            st.success(f"{self.table_name} 테이블 메타데이터가 새로고침되었습니다.")
        except Exception as e:
            st.error(f"메타데이터 새로고침 중 오류 발생: {str(e)}")
    
    def get_chat_product_mentions(self, start_date, end_date, product_names):
        """채팅 로그에서 상품 언급 횟수 조회"""
        if not product_names:
            return pd.DataFrame()  # 상품 이름이 없으면 빈 데이터프레임 반환
            
        product_conditions = []
        for product in product_names:
            # SQL 인젝션 방지를 위한 이스케이프 처리
            escaped_product = product.replace("'", "''")
            product_conditions.append(f"LOWER(message) LIKE '%{escaped_product.lower()}%'")
        
        product_condition = " OR ".join(product_conditions)
        
        query = f"""
        WITH product_mentions AS (
        SELECT 
            user,
            CASE 
            {' '.join([f"WHEN LOWER(message) LIKE '%{p.lower().replace(chr(39), chr(39)+chr(39))}%' THEN '{p}'" for p in product_names])}
            ELSE 'Other'
            END AS product_name
        FROM logs
        WHERE ({product_condition})
        AND SUBSTRING(timestamp, 1, 10) BETWEEN '{start_date}' AND '{end_date}'
        )
        SELECT 
        product_name,
        COUNT(*) AS mention_count
        FROM product_mentions
        WHERE product_name != 'Other'
        GROUP BY product_name
        ORDER BY mention_count DESC
        """
        
        return self.run_query(query)
    
    def get_chat_brand_counts(self, start_date, end_date):
        """브랜드별 채팅 횟수 조회"""
        
        query = f"""
        SELECT 
        partition_0 AS brand,
        COUNT(*) AS chat_count
        FROM logs
        WHERE SUBSTRING(timestamp, 1, 10) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY partition_0
        ORDER BY chat_count DESC
        """
        
        return self.run_query(query)
    
    def get_chat_user_product_interests(self, start_date, end_date, product_names):
        """사용자별 상품 관심도 분석"""
        if not product_names:
            return pd.DataFrame()  # 상품 이름이 없으면 빈 데이터프레임 반환
            
        product_conditions = []
        for product in product_names:
            escaped_product = product.replace("'", "''")
            product_conditions.append(f"LOWER(message) LIKE '%{escaped_product.lower()}%'")
        
        product_condition = " OR ".join(product_conditions)
        
        query = f"""
        WITH product_mentions AS (
        SELECT 
            user,
            CASE 
            {' '.join([f"WHEN LOWER(message) LIKE '%{p.lower().replace(chr(39), chr(39)+chr(39))}%' THEN '{p}'" for p in product_names])}
            ELSE 'Other'
            END AS product_name
        FROM logs
        WHERE ({product_condition})
        AND SUBSTRING(timestamp, 1, 10) BETWEEN '{start_date}' AND '{end_date}'
        )
        SELECT 
        user,
        product_name,
        COUNT(*) AS mention_count
        FROM product_mentions
        WHERE product_name != 'Other'
        GROUP BY user, product_name
        ORDER BY user, mention_count DESC
        """
        
        return self.run_query(query)
    
    def get_product_list(self):
        """상품 목록 조회"""
        query = """
        SELECT 
        product_id,
        client_id,
        category_id,
        price
        FROM products
        """
        
        return self.run_query(query)

class DataManager:
    def __init__(self):
        try:
            self.athena_manager = AthenaManager()
            self.product_dict = self.fetch_products_data()
            self.raw_orders = self.fetch_dynamodb_data()
            self.processed_orders = self.process_orders_data(self.raw_orders)
            self.product_names = self.get_product_names()
        except Exception as e:
            st.error(f"데이터 초기화 중 오류 발생: {str(e)}")
            raise
        
    def get_product_names(self):
        """상품 ID 목록을 추출 (실제로는 상품명임)"""
        if self.processed_orders.empty:
            # Athena에서 상품 목록 가져오기
            product_df = self.athena_manager.get_product_list()
            if not product_df.empty:
                return product_df['product_id'].unique().tolist()
            return []
        
        return self.processed_orders['product_id'].unique().tolist()

    def fetch_products_data(self):
        try:
            dynamodb = boto3.client("dynamodb", region_name="ap-northeast-2")
            response = dynamodb.scan(TableName="products")
            products_data = response["Items"]

            product_dict = {}
            for item in products_data:
                try:
                    product_id = extract_value(item['product_id'])
                    price = int(extract_value(item['price']))
                    client_id = extract_value(item.get('client_id', 'Unknown'))
                
                    product_dict[product_id] = {
                        'price': price,
                        'client_id': client_id
                    }
                except (ValueError, KeyError) as e:
                    print(f"❌ 상품 데이터 처리 오류: {str(e)}")
                    continue

            return product_dict
        except Exception as e:
            st.error(f"상품 데이터 로드 중 오류 발생: {str(e)}")
            raise

    def fetch_dynamodb_data(self):
        try:
            dynamodb = boto3.client("dynamodb", region_name="ap-northeast-2")
            paginator = dynamodb.get_paginator('scan')
            orders_data = []
            
            for page in paginator.paginate(TableName="orders"):
                orders_data.extend(page["Items"])

            processed_data = []
            for item in orders_data:
                try:
                    cart_items, total_quantity, total_price = parse_cart_items(
                        item.get("cart_items", {}),
                        self.product_dict
                    )
                    
                    timestamp_raw = extract_value(item['timestamp'])
                    if isinstance(timestamp_raw, (int, float)):
                        timestamp = datetime.fromtimestamp(timestamp_raw)
                    elif isinstance(timestamp_raw, str):
                        timestamp = datetime.strptime(timestamp_raw, "%y-%m-%d")
                    else:
                        timestamp = None

                    if timestamp:
                        processed_item = {
                            'order_id': extract_value(item['order_id']),
                            'user_id': extract_value(item['user_id']),
                            'timestamp': timestamp,
                            'cart_items': cart_items,
                            'total_quantity': total_quantity,
                            'total_price': total_price
                        }
                        processed_data.append(processed_item)
                    
                except Exception as e:
                    print(f"주문 처리 중 오류: {str(e)}")
                    continue

            return pd.DataFrame(processed_data)
        except Exception as e:
            st.error(f"주문 데이터 로드 중 오류 발생: {str(e)}")
            raise

    def process_orders_data(self, df_orders: pd.DataFrame) -> pd.DataFrame:
        try:
            if df_orders.empty:
                return pd.DataFrame()

            order_items = []
            for _, order in df_orders.iterrows():
                # cart_items가 문자열이나 dict일 수 있으므로 안전하게 처리
                cart_items = order.get('cart_items', [])
                if isinstance(cart_items, str):
                    import json
                    try:
                        cart_items = json.loads(cart_items)
                    except:
                        cart_items = []
                
                # 각 항목 순회
                for item in cart_items:
                    # product_id 추출 (다양한 형태 대비)
                    product_id = None
                    if isinstance(item, dict):
                        product_id = item.get('product_id') or item.get('id') or item.get('product', 'Unknown')
                    elif isinstance(item, str):
                        product_id = item
                    
                    # 제품 정보 가져오기
                    product_info = self.product_dict.get(product_id, {'client_id': 'Unknown', 'price': 0})
                    
                    # quantity와 price 안전하게 추출
                    quantity = 1
                    price = product_info['price']
                    
                    if isinstance(item, dict):
                        quantity = item.get('quantity', 1)
                        price = item.get('price', price)
                    
                    # timestamp 처리
                    timestamp = order.get('timestamp')
                    if not isinstance(timestamp, datetime):
                        try:
                            timestamp = pd.to_datetime(timestamp)
                        except:
                            timestamp = pd.Timestamp.now()
                    
                    order_items.append({
                        'order_id': order.get('order_id', 'Unknown'),
                        'user_id': order.get('user_id', 'Unknown'),
                        'timestamp': timestamp,
                        'product_id': product_id,
                        'client_id': product_info['client_id'],
                        'quantity': quantity,
                        'price': price,
                        'item_total': quantity * price
                    })
            
            # DataFrame 생성 및 타입 변환
            df_items = pd.DataFrame(order_items)
            
            # 데이터 타입 변환 (오류 방지)
            df_items['quantity'] = pd.to_numeric(df_items['quantity'], errors='coerce').fillna(0)
            df_items['price'] = pd.to_numeric(df_items['price'], errors='coerce').fillna(0)
            df_items['item_total'] = pd.to_numeric(df_items['item_total'], errors='coerce').fillna(0)

            return df_items

        except Exception as e:
            st.error(f"주문 데이터 처리 중 오류 발생: {str(e)}")
            return pd.DataFrame()
        
    def get_chat_analysis(self, start_date_str, end_date_str, product_names):
        """채팅 로그 분석 데이터 가져오기"""
        with st.spinner("채팅 로그 분석 중..."):
            try:
                # 테이블 메타데이터 새로고침
                self.athena_manager.refresh_table_metadata()
                # 상품별 언급 횟수
                product_mentions = self.athena_manager.get_chat_product_mentions(
                    start_date_str, end_date_str, product_names
                )
                
                # 브랜드별 채팅 횟수 (기존의 daily_counts를 brand_counts로 변경)
                brand_counts = self.athena_manager.get_chat_brand_counts(
                    start_date_str, end_date_str
                )
                
                # 사용자별 상품 관심도
                user_interests = self.athena_manager.get_chat_user_product_interests(
                    start_date_str, end_date_str, product_names
                )
                
                return product_mentions, brand_counts, user_interests
            except Exception as e:
                st.error(f"채팅 로그 분석 중 오류 발생: {str(e)}")
                # 오류 발생 시 빈 데이터프레임 반환
                return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
class ChartManager:
    def __init__(self, product_dict: Dict):
        self.product_dict = product_dict

    def make_line_chart(self, df_filtered: pd.DataFrame) -> Optional[go.Figure]:
        if df_filtered.empty:
            return None
                
        try:
            # 날짜 변환
            chart_data = df_filtered.copy()
            chart_data['date'] = pd.to_datetime(chart_data['timestamp']).dt.date
            
            # 날짜, 클라이언트ID, 제품ID별 매출 합계
            df_grouped = chart_data.groupby(['date', 'client_id'])['item_total'].sum().reset_index()
            
            # Plotly 그래프 생성
            fig = go.Figure()
            
            for client in df_grouped['client_id'].unique():
                client_data = df_grouped[df_grouped['client_id'] == client]
                fig.add_trace(go.Scatter(
                    x=client_data['date'], 
                    y=client_data['item_total'],
                    mode='lines+markers',
                    name=client
                ))
            
            # 레이아웃 수정 - 범례 위치 변경 및 여백 조정
            fig.update_layout(
                height=400,
                # 위쪽 여백을 늘려 범례를 위한 공간 확보
                margin=dict(l=10, r=10, t=80, b=10),
                # 범례 위치를 상단 중앙으로 변경
                legend=dict(
                    orientation="h",  # 수평 방향 범례
                    yanchor="top",    # 상단 기준점
                    y=1.12,           # 그래프 위 충분한 공간
                    xanchor="center", # 중앙 정렬
                    x=0.5,            # 중앙 위치
                ),
                xaxis_title="날짜",
                yaxis_title="판매량",
                # 모드바 설정 변경
                modebar=dict(
                    orientation='v',  # 수직 모드바
                )
            )
            
            return fig

        except Exception as e:
            st.error(f"차트 생성 중 오류 발생: {str(e)}")
            return None

    def make_order_table(self, df_filtered: pd.DataFrame) -> pd.DataFrame:
        if df_filtered.empty:
            return pd.DataFrame()
            
        try:
            # 날짜별, 상품별 매출 집계
            table_data = df_filtered.copy()
            table_data['date'] = table_data['timestamp'].dt.strftime('%y-%m-%d')
            
            # 디버깅: 원본 데이터 출력
            print("원본 데이터:")
            print(table_data)
            
            # 피벗 테이블 생성
            table = pd.pivot_table(
                table_data,
                values='item_total',
                index='product_id',
                columns='date',
                aggfunc='sum',
                fill_value=0
            )
            
            # 디버깅: 피벗 테이블 출력
            print("피벗 테이블:")
            print(table)
            
            # 합계 행 추가
            if not table.empty:
                table.loc['Total'] = table.sum()
            
            return table
        except Exception as e:
            st.error(f"테이블 생성 중 오류 발생: {str(e)}")
            return pd.DataFrame()

    def make_top_users_table(self, df_filtered: pd.DataFrame) -> pd.DataFrame:
        if df_filtered.empty:
            return pd.DataFrame()
                
        try:
            # 사용자별로 item_total 합산
            user_stats = df_filtered.groupby('user_id').agg({
                'item_total': 'sum',      # order_total 대신 item_total 사용
                'order_id': 'nunique',
                'quantity': 'sum'
            }).reset_index()
            
            user_stats.columns = ['User ID', '총 주문 금액', '주문 횟수', '총 주문 수량']
            return user_stats.sort_values('총 주문 금액', ascending=False)

        except Exception as e:
            st.error(f"사용자 테이블 생성 중 오류 발생: {str(e)}")
            return pd.DataFrame()
    
    def make_product_mentions_chart(self, product_mentions_df):
        """상품별 언급 횟수 차트 생성"""
        if product_mentions_df.empty:
            return None
            
        try:
            # 데이터프레임의 열 이름을 문자열로 변환
            df = product_mentions_df.copy()
            df.columns = df.columns.astype(str)
            
            # mention_count 열을 숫자로 변환
            df['mention_count'] = pd.to_numeric(df['mention_count'], errors='coerce')
            
            # 상위 10개 상품만 선택
            df = df.nlargest(10, 'mention_count')
            
            # 차트 생성
            fig = px.bar(
                df,
                x='mention_count',
                y='product_name',
                orientation='h',
                title='상품별 언급 횟수',
                labels={'mention_count': '언급 횟수', 'product_name': '상품명'},
                color='mention_count',
                color_continuous_scale=px.colors.sequential.Viridis
            )
            
            # 레이아웃 수정
            fig.update_layout(
                height=400,
                margin=dict(l=10, r=10, t=50, b=10),
                coloraxis_showscale=False
            )
            
            return fig
            
        except Exception as e:
            st.error(f"상품 언급 차트 생성 중 오류 발생: {str(e)}")
            return None
    
    def make_brand_chat_chart(self, brand_counts_df):
        """브랜드별 채팅 횟수 차트 생성"""
        if brand_counts_df.empty:
            return None
                
        try:
            # 데이터프레임의 열 이름을 문자열로 변환
            df = brand_counts_df.copy()
            df.columns = df.columns.astype(str)
            
            # chat_count 열을 숫자로 변환
            df['chat_count'] = pd.to_numeric(df['chat_count'], errors='coerce')
            
            # 차트 생성
            fig = px.bar(
                df,
                x='brand',  # 이전의 'date'에서 'brand'로 수정
                y='chat_count',
                title='브랜드별 채팅 횟수',
                labels={'chat_count': '채팅 횟수', 'brand': '브랜드'},
                color='chat_count',
                color_continuous_scale=px.colors.sequential.Viridis
            )
            
            # 레이아웃 수정
            fig.update_layout(
                height=400,
                margin=dict(l=10, r=10, t=50, b=10),
                xaxis_title="브랜드",
                yaxis_title="채팅 횟수"
            )
            
            return fig
                
        except Exception as e:
            st.error(f"브랜드별 채팅 차트 생성 중 오류 발생: {str(e)}")
            return None
    
    def make_user_product_interest_chart(self, user_interests_df):
        """사용자별 상품 관심도 히트맵 생성"""
        if user_interests_df.empty:
            return None
            
        try:
            # 데이터프레임의 열 이름을 문자열로 변환
            df = user_interests_df.copy()
            df.columns = df.columns.astype(str)
            
            # mention_count 열을 숫자로 변환
            df['mention_count'] = pd.to_numeric(df['mention_count'], errors='coerce')
            
            # 피벗 테이블 생성
            pivot_df = df.pivot_table(
                index='user',
                columns='product_name',
                values='mention_count',
                fill_value=0
            )
            
            # 최소 5명의 사용자만 선택 (너무 많으면 히트맵이 복잡해짐)
            if len(pivot_df) > 5:
                # 총 언급 횟수가 많은 상위 5명 사용자 선택
                user_totals = pivot_df.sum(axis=1).sort_values(ascending=False)
                top_users = user_totals.head(5).index
                pivot_df = pivot_df.loc[top_users]
            
            # 히트맵 생성
            fig = px.imshow(
                pivot_df,
                labels=dict(x="상품명", y="사용자", color="언급 횟수"),
                x=pivot_df.columns,
                y=pivot_df.index,
                color_continuous_scale='Viridis',
                aspect="auto"
            )
            
            # 레이아웃 수정
            fig.update_layout(
                height=400,
                margin=dict(l=10, r=10, t=50, b=10),
                xaxis={'side': 'top'}
            )
            
            # 셀에 값 표시
            for i, user in enumerate(pivot_df.index):
                for j, product in enumerate(pivot_df.columns):
                    value = pivot_df.iloc[i, j]
                    if value > 0:  # 0보다 큰 값만 표시
                        fig.add_annotation(
                            x=j,
                            y=i,
                            text=str(int(value)),
                            showarrow=False,
                            font=dict(color="white" if value > 3 else "black")
                        )
            
            return fig
            
        except Exception as e:
            st.error(f"사용자 관심도 차트 생성 중 오류 발생: {str(e)}")
            return None

class DashboardManager:
    def __init__(self, data_manager, chart_manager):
        self.data_manager = data_manager
        self.chart_manager = chart_manager

    def setup_page(self):
        st.set_page_config(
            page_title="인플루언서 대시보드",
            page_icon="🧸",
            layout="wide"
        )
        self.apply_custom_css()

    def apply_custom_css(self):
        # 기존 웹사이트 스타일을 적용
        st.markdown("""
        <style>
        /* Streamlit 요소 숨기기 */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* 컨테이너 스타일 조정 - 여백 제거 */
        [data-testid="stMainBlockContainer"] {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
        }
        
        [data-testid="stVerticalBlock"] {
            padding: 0 !important;
            margin: 0 !important;
            gap: 0;
        }
        
        /* 사이드바 및 메인 컨텐츠 간격 조정 */
        section[data-testid="stSidebar"] {
            width: 15rem !important; /* 사이드바 너비 조정 */
            padding-top: 0 !important;
            background-color: #f8f9fa;
        }
        .st-emotion-cache-1ibsh2c {
            padding: 0;
        }
        
        /* 네비게이션 바 스타일 */
        .navbar {
            background-color: #f8f9fa;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 0.5rem 1rem;
            width: 100%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .navbar-brand img {
            width: 100px;
            height: auto;
        }
        
        .navbar-nav {
            display: flex;
            padding-left: 0;
            margin-bottom: 0;
            list-style: none;
            margin-left: auto;
        }
        
        .nav-item {
            margin-left: 1rem;
        }
        
        .nav-link {
            font-family: 'Nanum Pen Script', cursive;
            color: #333 !important;
            font-size: 24px;
            text-decoration: none !important;
            padding: 0.5rem 0;
            display: block;
        }
        
        .nav-link:hover {
            color: #555;
        }
        
        /* 유저 이름 스타일 */
        .username-style {
            font-size: 30px;
            font-weight: bold;
            color: #555;
            margin-left: 1rem;
        }
        
        /* 메인 컨텐츠 영역 */
        .main-content {
            padding: 20px;
        }
        
        /* 필기체 스타일 */
        .fancy-title {
            font-size: 2.5em;
            text-align: center;
            color: #333;
            font-family: 'Dancing Script', cursive;
        }
        
        /* 버튼 스타일 */
        .btn-primary {
            background-color: #333;
            border: none;
            color: white;
        }
        
        .btn-primary:hover {
            background-color: #555;
        }
        
        /* 데이터프레임 스타일 */
        [data-testid="stDataFrame"] th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        </style>
        
        <!-- 폰트 불러오기 -->
        <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Nanum+Pen+Script&display=swap" rel="stylesheet">
        """, unsafe_allow_html=True)

    def setup_sidebar(self):
        with st.sidebar:
            st.title('🧸 데이터 필터')
            
            analysis_type = st.radio("분석 기준을 선택하세요", 
                                ["사용자 기준", "상품 기준", "사용자-상품 연계"])

            df = self.data_manager.processed_orders
            min_date = df['timestamp'].min().date()
            max_date = df['timestamp'].max().date()
            
            start_date = st.date_input("시작 날짜", 
                                    min_value=min_date,
                                    max_value=max_date, 
                                    value=min_date)
            end_date = st.date_input("끝 날짜", 
                                    min_value=min_date,
                                    max_value=max_date, 
                                    value=max_date)

            # 클라이언트 선택
            selected_clients = st.multiselect(
                "Client ID를 선택하세요.",
                sorted(df['client_id'].unique())
            )

            # 클라이언트 선택 시 해당 클라이언트의 제품만 필터링
            if selected_clients:
                available_products = df[df['client_id'].isin(selected_clients)]['product_id'].unique()
                selected_products = st.multiselect(
                    "상품을 선택하세요.",
                    sorted(available_products)
                )
            else:
                selected_products = st.multiselect(
                    "상품을 선택하세요.",
                    sorted(df['product_id'].unique())
                )

            selected_users = st.multiselect(
                "사용자를 선택하세요.",
                sorted(df['user_id'].unique())
            )

            return analysis_type, start_date, end_date, selected_users, selected_products, selected_clients

    def apply_filters(self, analysis_type, start_date, end_date, selected_users, selected_products, selected_clients):
        df = self.data_manager.processed_orders
        
        # 날짜 필터링
        mask = (df['timestamp'].dt.date >= start_date) & (df['timestamp'].dt.date <= end_date)
        df_filtered = df[mask].copy()
        
        # 사용자/상품 필터링
        if selected_users:
            df_filtered = df_filtered[df_filtered['user_id'].isin(selected_users)]
        if selected_products:
            df_filtered = df_filtered[df_filtered['product_id'].isin(selected_products)]
        if selected_clients:
            df_filtered = df_filtered[df_filtered['client_id'].isin(selected_clients)]
            
        return df_filtered

    def render_dashboard(self, df_filtered, start_date, end_date, selected_products):
        # 메인 컨텐츠 시작
        st.markdown('<div class="main-content">', unsafe_allow_html=True)
        
        # 제목 및 차트 헤더
        st.markdown('<h2 class="fancy-title">상품별 매출 추이</h2>', unsafe_allow_html=True)
        
        # 메인 차트
        line_chart = self.chart_manager.make_line_chart(df_filtered)
        if line_chart is not None:
            st.plotly_chart(line_chart, use_container_width=True)
        else:
            st.info('데이터가 없습니다.')
        
        # 하단 섹션 - 두 컬럼 레이아웃
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown('#### 상품별 일간 매출')
            product_table = self.chart_manager.make_order_table(df_filtered)
            if not product_table.empty:
                st.dataframe(product_table, use_container_width=True, height=300)
            else:
                st.info('데이터가 없습니다.')
        
        with col2:
            st.markdown('#### Top 사용자')
            top_users = self.chart_manager.make_top_users_table(df_filtered)
            
            if not top_users.empty:
                max_value = int(top_users['총 주문 금액'].max())
                st.dataframe(
                    top_users,
                    hide_index=True,
                    column_config={
                        "User ID": st.column_config.TextColumn(
                            "사용자 ID"
                        ),
                        "총 주문 금액": st.column_config.ProgressColumn(
                            "총 주문 금액",
                            min_value=0,
                            max_value=max_value,
                            format="₩ %d"
                        ),
                        "주문 횟수": st.column_config.NumberColumn(
                            "주문 횟수",
                            format="%d회"
                        ),
                        "총 주문 수량": st.column_config.NumberColumn(
                            "총 주문 수량",
                            format="%d개"
                        )
                    },
                    height=300
                )
            else:
                st.info('데이터가 없습니다.')
        
        # 채팅 로그 분석 섹션
        st.markdown('#### 채팅 로그 분석')
        
        # Athena를 통한 채팅 로그 데이터 가져오기
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # 상품 목록 (선택된 상품이 없으면 전체 상품 사용)
        product_names = selected_products if selected_products else self.data_manager.product_names
        
        # 채팅 로그 분석 데이터 가져오기
        product_mentions, brand_counts, user_interests = self.data_manager.get_chat_analysis(
            start_date_str, end_date_str, product_names
        )
        
        chat_tab1, chat_tab2, chat_tab3 = st.tabs(["상품별 언급", "브랜드별 채팅 횟수", "사용자-상품 관심도"])
        
        with chat_tab1:
            if not product_mentions.empty:
                # 차트 생성
                mentions_chart = self.chart_manager.make_product_mentions_chart(product_mentions)
                if mentions_chart:
                    st.plotly_chart(mentions_chart, use_container_width=True)
                
                # 데이터 테이블 표시
                st.markdown("##### 상품별 언급 횟수 상세")
                st.dataframe(product_mentions, use_container_width=True)
            else:
                st.info("선택한 기간 내 상품 언급 데이터가 없습니다.")
            
        with chat_tab2:
            if not brand_counts.empty:
                # 차트 생성 (함수명 변경됨)
                brand_chart = self.chart_manager.make_brand_chat_chart(brand_counts)
                if brand_chart:
                    st.plotly_chart(brand_chart, use_container_width=True)
                
                # 데이터 테이블 표시
                st.markdown("##### 브랜드별 채팅 횟수 상세")
                st.dataframe(brand_counts, use_container_width=True)
            else:
                st.info("브랜드별 채팅 데이터가 없습니다.") 
                
        with chat_tab3:
            if not user_interests.empty:
                # 히트맵 생성
                user_interest_chart = self.chart_manager.make_user_product_interest_chart(user_interests)
                if user_interest_chart:
                    st.plotly_chart(user_interest_chart, use_container_width=True)
                
                # 사용자별 관심도 상세 정보
                st.markdown("##### 사용자별 상품 관심도 상세")
                st.dataframe(user_interests, use_container_width=True)
            else:
                st.info("선택한 기간 내 사용자-상품 관심도 데이터가 없습니다.")
        
        # 채팅 로그와 구매 연계 분석
        st.markdown('#### 채팅 언급 vs 구매 전환율')
        
        try:
            # 채팅에서 언급된 상품 목록
            if not product_mentions.empty:
                mentioned_products = set(product_mentions['product_name'].tolist())
                
                # 구매된 상품 목록 (product_id가 실제로는 상품명임)
                purchased_products = set(df_filtered['product_id'].unique().tolist())
                
                # 교집합 (언급 후 구매)
                mentioned_and_purchased = mentioned_products.intersection(purchased_products)
                
                # 언급되었지만 구매되지 않은 상품
                mentioned_not_purchased = mentioned_products - purchased_products
                
                # 구매되었지만 언급되지 않은 상품
                purchased_not_mentioned = purchased_products - mentioned_products
                
                # 데이터 준비
                conversion_data = pd.DataFrame({
                    '상품 분류': ['언급 & 구매', '언급만', '구매만'],
                    '상품 수': [len(mentioned_and_purchased), len(mentioned_not_purchased), len(purchased_not_mentioned)]
                })
                
                # 데이터가 있는 경우만 표시
                if conversion_data['상품 수'].sum() > 0:
                    # 차트 생성
                    fig = px.pie(
                        conversion_data,
                        values='상품 수',
                        names='상품 분류',
                        title='채팅 언급과 구매 관계',
                        color='상품 분류',
                        color_discrete_map={
                            '언급 & 구매': '#2ECC71',
                            '언급만': '#F39C12',
                            '구매만': '#3498DB'
                        }
                    )
                    
                    # 레이아웃 수정
                    fig.update_layout(
                        height=400,
                        margin=dict(l=10, r=10, t=50, b=10)
                    )
                    
                    # 차트 표시
                    col1, col2 = st.columns([3, 2])
                    
                    with col1:
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # 전환율 계산
                        mentioned_count = len(mentioned_products)
                        converted_count = len(mentioned_and_purchased)
                        
                        if mentioned_count > 0:
                            conversion_rate = (converted_count / mentioned_count) * 100
                        else:
                            conversion_rate = 0
                        
                        # 통계 요약
                        st.markdown(f"""
                        ### 채팅-구매 분석 요약
                        
                        - **채팅에서 언급된 상품**: {mentioned_count}개
                        - **실제 구매된 언급 상품**: {converted_count}개
                        - **전환율**: {conversion_rate:.1f}%
                        
                        #### 언급 후 구매된 상품 TOP 5
                        """)
                        
                        # 언급 후 구매된 상품 목록 표시
                        if mentioned_and_purchased:
                            # 언급 순위와 매출 정보 결합
                            conversion_detail = []
                            
                            for product in mentioned_and_purchased:
                                mention_count = product_mentions[product_mentions['product_name'] == product]['mention_count'].values[0]
                                sales = df_filtered[df_filtered['product_id'] == product]['item_total'].sum()
                                
                                conversion_detail.append({
                                    '상품명': product,
                                    '언급 횟수': int(mention_count),
                                    '매출액': sales
                                })
                            
                            # 데이터프레임 생성 및 정렬
                            conversion_df = pd.DataFrame(conversion_detail)
                            conversion_df = conversion_df.sort_values('매출액', ascending=False).head(5)
                            
                            # 테이블 표시
                            st.dataframe(conversion_df, use_container_width=True)
                        else:
                            st.info("언급 후 구매된 상품이 없습니다.")
                else:
                    st.info("분석 가능한 데이터가 없습니다.")
            else:
                st.info("채팅 언급 데이터가 없어 전환율을 계산할 수 없습니다.")
                
        except Exception as e:
            st.error(f"전환율 분석 중 오류 발생: {str(e)}")
        
        # 메인 컨텐츠 끝
        st.markdown('</div>', unsafe_allow_html=True)
        
    def initialize_session(self):
        """URL 파라미터에서 사용자 정보를 가져와 세션 상태 초기화"""
        if 'is_initialized' not in st.session_state:
            # URL 쿼리 파라미터에서 사용자 정보 가져오기
            username = st.query_params.get("username", "관리자")
            client_id = st.query_params.get("client_id", "")
            
            # 세션 상태에 저장
            st.session_state.username = username
            st.session_state.client_id = client_id
            st.session_state.is_authenticated = bool(username)
            st.session_state.is_initialized = True
    
    def get_service_urls(self):
        """다른 서비스의 URL을 가져옴"""
        
        base_url = os.getenv('AUTH_MAINSERVICE_URL',"https://www.ssginc.store") ## 서비스
        client_url = os.getenv('AUTH_CLIENTSERVICE_URL',"https://www.ssginc.store") ## 서비스
        
        # 서비스 URL 생성
        service_urls = {
            "상품 관리": f"{client_url}/client/manage_product",
            "주문 관리": f"{client_url}/client/manage_order",
            "로그아웃": f"{base_url}/user/logout"
        }
        
        return service_urls
    
    def render_navbar_with_links(self):
        """서비스 링크가 포함된 네비게이션 바 렌더링"""
        # 사용자 정보 가져오기
        username = st.session_state.get('client_id', '관리자')
        
        # 서비스 URL 가져오기
        service_urls = self.get_service_urls()
        
        # HTML 문자열 직접 작성 (중간 변수 사용하지 않음)
        navbar_html = f"""
        <nav class="navbar navbar-expand-lg navbar-light bg-light">
            <a class="navbar-brand" href="#">
                <img src="https://via.placeholder.com/100x50?text=Logo" alt="쇼핑몰 로고">
            </a>        
            <span class="username-style ml-3">안녕하세요 {username} 님</span>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ml-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{service_urls['상품 관리']}" target="_self">상품 관리</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{service_urls['주문 관리']}" target="_self">주문 관리</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{service_urls['로그아웃']}" target="_self">로그아웃</a>
                    </li>
                </ul>
            </div>
        </nav>
        """
        
        # 네비게이션 바 렌더링
        st.markdown(navbar_html, unsafe_allow_html=True)


def main():
    try:
        # 매니저 초기화
        data_manager = DataManager()
        chart_manager = ChartManager(data_manager.product_dict)
        dashboard = DashboardManager(data_manager, chart_manager)
        
        # 페이지 설정
        dashboard.setup_page()
        
        # 세션 초기화 (추가)
        dashboard.initialize_session()
        
        # 링크가 포함된 네비게이션 바 렌더링 (기존 render_navbar 대체)
        dashboard.render_navbar_with_links()
        
        # 나머지 코드는 그대로...
        analysis_type, start_date, end_date, selected_users, selected_products, selected_clients = dashboard.setup_sidebar()
        df_filtered = dashboard.apply_filters(
            analysis_type, start_date, end_date, selected_users, selected_products, selected_clients
        )
        # 대시보드 렌더링 (채팅 로그 분석 추가)
        dashboard.render_dashboard(df_filtered, start_date, end_date, selected_products)
        
    except Exception as e:
        st.error(f"대시보드 실행 중 오류가 발생했습니다: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        
def health_check():
    # 실제 필요한 체크 로직 (DB 연결 등) 추가 가능
    st.json({"status": "OK"})

if __name__ == "__main__":
    # URL 파라미터로 헬스체크 요청 감지
    if "healthcheck" in st.query_params:
        health_check()
    else:
        main()  # 기존 메인 함수