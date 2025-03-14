from flask import * 
from DB.userDB import *
from DB.clientDB import *
from DB.productDB import *
from DB.categoryDB import *
from DB.s3 import *
from DB.data_stream import *

blueprint = Blueprint('admin', __name__, url_prefix='/admin' ,template_folder='templates')

# 고객사 관리
@blueprint.route('/manage_client')
def manage_client():
    current_app.logger.info("admin 페이지 접속")
    clients = clientDao().get_all_clients()
    return render_template('manage_client.html',clients=clients)

# 고객사 추가
@blueprint.route('/add_client', methods=['GET', 'POST'])
def add_client():

    name = request.form['name']
    
    clientDao().insert_client(name)

    clients = clientDao().get_all_clients()

    return render_template('manage_client.html',clients=clients)

# 고객사 제거
@blueprint.route('/delete_client/<client_id>',methods=['POST'])
def delete_client(client_id):
    clientDao().delete_client(client_id)
    products = ProductDao().get_all_products()
    for product in products:
        if client_id == product['client_id']:
            ProductDao().delete_product(product['product_id'])

    clients = clientDao().get_all_clients()
    return render_template('manage_client.html', clients=clients)

# 사용자 관리
@blueprint.route('/manage_user')
def manage_user():
    users = UserDao().get_all_users()
    return render_template('manage_user.html',users=users)

# 상품 관리
@blueprint.route('/manage_product')
def manage_product():
    products = ProductDao().get_all_products()
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
    client_id = request.form['client_id']
    category_id = request.form['category_id']
    image = request.files['image'] 

    image_url = upload_file_to_s3(image, name)
    
    ProductDao().insert_product(name,price,description,client_id,category_id,image_url)
    salesdataDao().insert_data(name)
    clients = clientDao().get_all_clients()
    categories = categoryDao().get_all_categories()
    products = ProductDao().get_all_products()

    return render_template('manage_product.html',products=products,clients=clients,categories=categories)

# 상품 관리
@blueprint.route('/update_product/<product_id>',methods=['POST'])
def update_product(product_id):
    product_id = request.form['name']
    price = request.form['price']
    description = request.form['description']
    client_id = request.form['client_id']
    category_id = request.form['category_id']
    image = request.files['image'] 
    
    ProductDao().update_product(product_id,price,description,client_id,category_id,image)
    products = ProductDao().get_all_products()
    clients = clientDao().get_all_clients()
    categories = categoryDao().get_all_categories()
    return render_template('manage_product.html',products=products,clients=clients,categories=categories)

# 상품 관리
@blueprint.route('/delete_product/<product_id>',methods=['POST'])
def delete_product(product_id):
    ProductDao().delete_product(product_id)
    salesdataDao().delete_product(product_id)
    products = ProductDao().get_all_products()
    clients = clientDao().get_all_clients()
    categories = categoryDao().get_all_categories()
    delete_object(product_id)
    return render_template('manage_product.html',products=products,clients=clients,categories=categories)

@blueprint.route('/manage_order')
def manage_order():
    return render_template('manage_order.html')