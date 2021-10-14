from flask.globals import request
from flask.json import jsonify
import werkzeug
werkzeug.cached_property = werkzeug.utils.cached_property
import flask.scaffold
flask.helpers._endpoint_from_view_func = flask.scaffold._endpoint_from_view_func
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_restplus import Api, Resource, fields,Namespace
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import jwt
from functools import wraps
import datetime

# instantiate our flask application
app = Flask(__name__)

app.config['SECRET_KEY'] = "123456"
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/api_swaggerdb'
app.config['SQLALCHEMY_TRACK_MODIFICATION'] = False
app.config['JSON_SORT_KEYS'] = True

authorizations = {
    'Bearer Auth': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization'
    },
}

db = SQLAlchemy(app)
ma = Marshmallow(app)
api = Api(app, version='1.0', title='Product Restful api ', 
          description='this is product restful api with the below endpoint',security='Bearer Auth', authorizations=authorizations)
product_ns = Namespace('PRODUCTS', description='API')
auth_ns = Namespace('Authentication',description='API')

api.add_namespace(auth_ns, path='/user')
api.add_namespace(product_ns, path='/products')



# create User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.Integer)
    name = db.Column(db.String(50))
    email= db.Column(db.Text)
    password = db.Column(db.String(50))

    def __init__(self,public_id,name,email,password):
        self.public_id = public_id
        self.name = name
        self.email = email
        self.password = password

# create database model
class Product(db.Model):
    product_id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(80),nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float,nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    def __init__(self,name,description,price,quantity):
        self.name= name
        self.description = description
        self.price = price
        self.quantity = quantity

# create schema for tha mode

# generate api authentication token
def token_required(f):
   @wraps(f)
   def decorator(*args, **kwargs):

      token = None

      if 'Authorization' in request.headers:
         token = request.headers['Authorization']

      if not token:
         return jsonify({'message': 'a valid token is missing'})

      return f(*args, **kwargs)

   return decorator

class ProductSchema(ma.Schema):
    class Meta:

        fields = ('name','description','price','quantity')
        model = Product

# instantiate product schema
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)


# data expected by the server

model = api.model('Products',{
    'name': fields.String('Name of the product'),
    'description': fields.String('product description'),
    'price': fields.Float(0.00),
    'quantity': fields.Integer
})

# data server expected during user registration
register_detail = api.model('User',{
    'name': fields.String('Name of the user'),
    'email': fields.String('email of the user'),
    'password': fields.String('The password.', format='password')
})

# data server expected during user login
login_detail = api.model('User_login',{
    'email': fields.String('email of the user'),
    'password': fields.String('The password.', format='password')
})
# define the route

@product_ns.route('/products')
class Products(Resource):

    @token_required
    def get(self):

        products = Product.query.all()
        return jsonify(products_schema.dump(products))

    @api.expect(model)
    def post(self):

        name = request.json['name']
        description = request.json['description']
        price = request.json['price']
        quantity = request.json['quantity']

        product = Product(name,description,price,quantity)
        db.session.add(product)
        db.session.commit()
        return jsonify(product_schema.dump(product))

@product_ns.route('/product/<int:id>')
class Products(Resource):

    @token_required
    def get(self,id):
        product = Product.query.get(id)
        return jsonify(product_schema.dump(product))

    @token_required
    @api.expect(model)
    def put(self,id):
        product = Product.query.get(id)
        product.name = request.json['name']
        product.description = request.json['description']
        product.price = request.json['price']
        product.quantity = request.json['quantity']

        db.session.commit()
        return jsonify(product_schema.dump(product))


    @token_required
    def delete(self,id):
        product = Product.query.get(id)
        db.session.delete(product)
        db.session.commit()

        result = product_schema.dump(product)
        result['message'] = 'Sucessfully deleted'
        return jsonify(result)


# authentication route

# 1. register route

@auth_ns.route('/register', methods=['POST'])
class Authentication(Resource):

    @api.expect(register_detail)
    def post(self):

        public_id= str(uuid.uuid4())
        name = request.json['name']
        email = request.json['email']
        passowrd = request.json['password']

        #hashed_password = generate_password_hash(passowrd,method='sha256')
    
        new_user = User(public_id,name,email,passowrd) 
        db.session.add(new_user)  
        db.session.commit()    

        return jsonify({'message': 'registered successfully'})

@auth_ns.route('/login', methods=['POST'])
class Authentication(Resource):

    @api.expect(login_detail)
    def post(self):
        
        email = request.json['email']
        passowrd = request.json['password']

        user = User.query.filter_by(email=email).first()
        if(user):
            if user.password == passowrd:
                token = jwt.encode({'public_id': user.public_id, 'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])  
                return jsonify({'token' : token}) 
            return jsonify({
                'message':'Password does not match'
            })
    
        return jsonify({
            'message':'user does not exist'
        }) 



if __name__=="__main__":
    app.run(debug=True)