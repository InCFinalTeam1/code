from flask import *
from DB.clientDB import *
from DB.categoryDB import *

blueprint = Blueprint('influ', __name__, template_folder='templates', url_prefix='/influ')

# 메인 화면
@blueprint.route('/flu')
def influ():
    current_app.logger.info("홈 페이지 접속")
    auth_userservice_url = current_app.config['AUTH_USERSERVICE_URL']
    print(f"BACK AUTH_USERSERVICE_URL: {auth_userservice_url}")  
    clients = clientDao().get_all_clients()
    return render_template('influ.html',clients=clients, auth_userservice_url=auth_userservice_url)

@blueprint.route('/influ_search')    
def influ_search():
    current_app.logger.info("인플루언서 검색")
    query = request.args.get('query', '')

    if query:
        clients = clientDao().search_client_by_query(query)
    else:
        clients = clientDao().get_all_clients()

    return render_template('influ.html',clients=clients)

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