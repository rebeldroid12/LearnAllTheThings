import os
import sqlite3
from flask import Flask, g, jsonify, make_response
import json

from apispec import APISpec
from flask import request, make_response, jsonify
from marshmallow import Schema, fields
# from app import app, get_db, insert, bad_request, not_found

from flask import jsonify
from flask.views import MethodView


# wonderful code found here: http://flask.pocoo.org/docs/0.12/tutorial/setup/#tutorial-setup
# https://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask
# https://docs.python.org/3/library/sqlite3.html#sqlite3.Row

app = Flask(__name__)   # create the application instance
app.config.from_object(__name__)    # load config from this file , super_simple_flask_app.py

DATABASE = os.path.join(app.root_path, 'testdb.db')


def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(DATABASE)
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')      # flask initdb


# http://flask.pocoo.org/snippets/37/ -- prepared statements
def insert(table, fields=(), values=()):
    db = get_db()
    cur = db.cursor()
    query = 'INSERT INTO %s (%s) VALUES (%s)' % (
        table,
        ', '.join(fields),
        ', '.join(['?'] * len(values))
    )
    cur.execute(query, values)
    db.commit()
    id = cur.lastrowid
    cur.close()
    return id


@app.errorhandler(404)
def not_found():
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.errorhandler(400)
def bad_request():
    return make_response(jsonify({'error': 'Bad Request'}), 400)


# Create an APISpec
spec = APISpec(
    title='Swagger Food Inventory',
    version='1.0.0',
    plugins=[
        'apispec.ext.flask',
        'apispec.ext.marshmallow',
    ],
)


class FoodSchema(Schema):
    name = fields.Str(required=True)
    food_type = fields.Str(required=True)


@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/foods', methods=['GET', 'POST'])
def foods():
    """Food Inventory
    ---
    get:
        description: Get a list of foods in inventory
        responses:
            200:
                description: Foods found
                schema: FoodSchema

    :return:
    """

    if request.method == 'GET':
        db = get_db()
        cur = db.execute('select * from foods;')
        foods = cur.fetchall()

        result = FoodSchema(many=True).dump(foods).data

        return make_response(jsonify(result), 200)  # SUCCESS

    elif request.method == 'POST':
        body = request.json

        if not body:
            return bad_request()  # BAD REQUEST

        else:
            result = FoodSchema().dump(body).data

            new_row_id = insert(table='foods', fields=('name', 'food_type'),
                                values=(result['name'],
                                        result['food_type']))

            result['id'] = new_row_id

        return make_response(jsonify(result), 201)  # CREATED


@app.route('/foods/<int:id>', methods=['GET'])
def get_foods(id):
    db = get_db()
    cur = db.execute('select * from foods where id = {}'.format(id))
    food = cur.fetchone()  # not a list, just one row that is form of list

    if food:
        result = FoodSchema().dump(food).data

        return make_response(jsonify(result), 200)  # SUCCESS

    else:
        return not_found()  # NOT FOUND


spec.definition('Foods', schema=FoodSchema)
with app.test_request_context():
    spec.add_path(view=foods)


# We're good to go! Save this to a file for now.
with open('swagger.json', 'w') as f:
    json.dump(spec.to_dict(), f)

#
# class SpecAPI(MethodView):
#
#     def get(self):
#         spec.add_path(view=foods)
#         body = spec.to_dict()
#         merged = {**body}
#
#         return jsonify(merged), 200
#
# from flask import Blueprint
# swagger = Blueprint('swagger', __name__, url_prefix="/swagger", static_folder="dist", template_folder="templates")
#
# spec_view = SpecAPI.as_view('spec_api')
# swagger.add_url_rule('/spec', view_func=spec_view, methods=['GET', ])
#


@app.route('/docs')
def docs():
    docs = {"info": {"title": "Swagger Food Inventory", "version": "1.0.0"}, "paths": {"/foods": {"get": {"description": "Get a list of foods in inventory", "responses": {"200": {"description": "Foods found", "schema": {"$ref": "#/definitions/Foods"}}}}}}, "tags": [], "swagger": "2.0", "definitions": {"Foods": {"type": "object", "properties": {"food_type": {"type": "string"}, "name": {"type": "string"}}, "required": ["food_type", "name"]}}, "parameters": {}}
    return jsonify(docs)
