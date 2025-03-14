from flask import Flask
from config import Config
import logging
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
# 컨텍스트 전파 설정을 위한 import
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.propagators.b3 import B3Format
from opentelemetry.propagators.jaeger import JaegerPropagator

from app.user import blueprint as user_blueprint

def create_app():
    app = Flask(__name__)
    app.secret_key = 'bsdajvkbakjbfoehihewrpqkldn21pnifninelfbBBOIQRqnflsdnljneoBBOBi2rp1rp12r9uh'
    app.config.from_object(Config)
    
    # 블루프린트 등록
    app.register_blueprint(user_blueprint)
    
    # 로깅 설정
    app.logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler('app.log')
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)
    
    # 컨텍스트 전파자 설정 - B3와 Jaeger 전파자 모두 사용
    set_global_textmap(CompositePropagator([B3Format(), JaegerPropagator()]))
    
    # OpenTelemetry 리소스 설정
    resource = Resource(attributes={
        SERVICE_NAME: "project-user-app-service"
    })
    
    # 트레이서 프로바이더 설정
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    
    # Jaeger 익스포터 설정
    jaeger_exporter = JaegerExporter(
        collector_endpoint="http://jaeger-collector.istio-system.svc.cluster.local:14268/api/traces"
    )
    
    # 스팬 프로세서 추가
    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    
    # Flask 자동 계측 적용 - 요청/응답 헤더 추적 활성화
    FlaskInstrumentor().instrument_app(app, tracer_provider=provider, excluded_urls="healthcheck")
    
    # Requests 라이브러리 계측 - 요청 헤더에 트레이스 정보 포함
    RequestsInstrumentor().instrument(tracer_provider=provider)
    
    return app