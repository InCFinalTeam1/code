from flask import * 
from DB.userDB import *
from DB.clientDB import *
from DB.productDB import *
from DB.categoryDB import *
from DB.s3 import *
from DB.data_stream import *

blueprint = Blueprint('client', __name__, template_folder='templates', url_prefix='/client')

# # 메인 화면
@blueprint.route('/clientpage')
def clientpage():
    auth_userservice_url = current_app.config['AUTH_USERSERVICE_URL']
    auth_analyze_url = current_app.config['AUTH_ANALYZE_URL']
    return render_template('clientpage.html',auth_userservice_url=auth_userservice_url,auth_analyze_url=auth_analyze_url)

# 메인 화면
# @blueprint.route('/analyze')
# def clientpage():
#     auth_analyze_url = current_app.config['auth_analyze_url']
#     return redirect(auth_analyze_url)

# 상품 관리
@blueprint.route('/manage_product')
def manage_product():
    client_id = session['login_info']['client_id']
    products = ProductDao().get_products_by_client(client_id)
    clients = clientDao().get_all_clients()
    categories = categoryDao().get_all_categories()

    # 판매량 추가
    for product in products:
        product['sales_amount'] = int(salesdataDao().get_quantity_by_id(product['product_id']))
    
    return render_template('manage_product.html', products=products, clients=clients, categories=categories)

# 상품 관리
@blueprint.route('/add_product', methods=['GET', 'POST'])
def add_product():
    name = request.form['name']
    price = request.form['price']
    description = request.form['description']
    client_id = session['login_info']['client_id']
    category_id = request.form['category_id']
    image = request.files['image'] 

    image_url = upload_file_to_s3(image, name)
    
    ProductDao().insert_product(name,price,description,client_id,category_id,image_url)
    salesdataDao().insert_data(name)
    clients = clientDao().get_all_clients()
    categories = categoryDao().get_all_categories()
    products = ProductDao().get_products_by_client(client_id)

    return render_template('manage_product.html',products=products,clients=clients,categories=categories)

# 상품 관리
@blueprint.route('/update_product/<product_id>',methods=['POST'])
def update_product(product_id):
    product_id = request.form['name']
    price = request.form['price']
    description = request.form['description']
    client_id = session['login_info']['client_id']
    category_id = request.form['category_id']
    image = request.files['image'] 
    
    ProductDao().update_product(product_id,price,description,client_id,category_id,image)
    products = ProductDao().get_products_by_client(client_id)
    clients = clientDao().get_all_clients()
    categories = categoryDao().get_all_categories()
    return render_template('manage_product.html',products=products,clients=clients,categories=categories)

# 상품 관리
@blueprint.route('/delete_product/<product_id>',methods=['POST'])
def delete_product(product_id):
    ProductDao().delete_product(product_id)
    salesdataDao().delete_product(product_id)
    client_id = session['login_info']['client_id']
    products = ProductDao().get_products_by_client(client_id)
    clients = clientDao().get_all_clients()
    categories = categoryDao().get_all_categories()
    delete_object(product_id)
    return render_template('manage_product.html',products=products,clients=clients,categories=categories)

@blueprint.route('/manage_order')
def manage_order():
    return render_template('manage_order.html')
