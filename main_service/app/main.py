from flask import *
from DB.productDB import *
from DB.clientDB import *
from DB.categoryDB import *

blueprint = Blueprint('main', __name__, template_folder='templates')

SLIDER_IMAGES = {
    "박수환": [  # 예: 클라이언트 ID 1에 해당하는 이미지
        "/static/image/Park_1.jpg",
        "/static/image/Park_2.jpg",
        "/static/image/Free.jpg"
    ],
    "GD": [  # 예: 클라이언트 ID 2에 해당하는 이미지
        "/static/image/GD_1.jpg",
        "/static/image/GD_2.jpg",
        "/static/image/Free.jpg"
    ],
    "국승빈": [  # 예: 클라이언트 ID 3에 해당하는 이미지
        "/static/image/Bang_2.jpg",
        "/static/image/Bang_3.jpg",
        "/static/image/Free.jpg"
    ],
}

# 메인 화면
@blueprint.route('/main/<client_id>')
def main(client_id):
    current_app.logger.info(client_id + " 쇼핑몰 접속")
    products = ProductDao().get_products_by_client(client_id)
    clients = clientDao().get_all_clients()
    categories = categoryDao().get_all_categories()

    # 페이지네이션
    page = int(request.args.get('page', 1))
    per_page = 8
    start = (page - 1) * per_page
    end = start + per_page
    total_pages = (len(products) + per_page - 1) // per_page
    current_products = products[start:end]
    pages = get_pagination(page, total_pages)
    
    slider_images = SLIDER_IMAGES.get(client_id, ["/static/image/Free.jpg"])
    
    return render_template('home.html', 
                            products=current_products, 
                            int=int,  # 여기에 list 형식으로 static에 있는 이미지 렌더링
                            clients=clients,
                            categories=categories,
                            page=page, 
                            pages=pages, 
                            total_pages=total_pages,
                            client_id=client_id,
                            slider_images=slider_images
                            )

@blueprint.route('/search')    
def search():
    client_id = request.args.get('client_id', '')
    query = request.args.get('query', '')
    products = ProductDao().get_products_by_client(client_id)
    clients = clientDao().get_all_clients()
    categories = categoryDao().get_all_categories()
    current_app.logger.info(query + "상품 검색")
    
    if query:
        products = ProductDao().search_products_by_query_and_client(query,client_id)
    else:
        products = ProductDao().get_products_by_client(client_id)

    # 페이지네이션
    page = request.args.get('page', 1, type=int)
    per_page = 8
    total_pages = (len(products) - 1) // per_page + 1
    paginated_list = products[(page - 1) * per_page: page * per_page]
    pages = get_pagination(page, total_pages)
    slider_images = SLIDER_IMAGES.get(client_id, ["/static/image/Free.jpg"])
    return render_template('home.html', 
                            clients=clients,
                            categories=categories,
                            products=paginated_list , 
                            page=page, 
                            pages=pages, 
                            total_pages=total_pages,
                            query=query,
                            client_id=client_id,
                            slider_images=slider_images,
                            int=int)

def get_pagination(page, total_pages, max_visible=10):
    if total_pages <= max_visible:
        return list(range(1, total_pages + 1))

    visible_pages = []
    visible_pages.append(1)
    if page > 3:
        visible_pages.append('...')

    start = max(2, page - 1)
    end = min(total_pages - 1, page + 1)
    visible_pages.extend(range(start, end + 1))

    if page < total_pages - 2:
        visible_pages.append('...')
        visible_pages.append(total_pages)

    return visible_pages