import os
import sqlite3
from flask import Flask, g, request, make_response, jsonify
from flasgger import Swagger
from schemas import FoodSchema, FoodPatchSchema


# wonderful code found here: http://flask.pocoo.org/docs/0.12/tutorial/setup/#tutorial-setup
# https://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask
# https://docs.python.org/3/library/sqlite3.html#sqlite3.Row

app = Flask(__name__)   # create the application instance
app.config.from_object(__name__)    # load config from this file , super_simple_flask_app.py
Swagger(app)

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
def create_data(table, fields=(), values=()):
    db = get_db()
    cur = db.cursor()
    query = 'INSERT INTO %s (%s) VALUES (%s)' % (
        table,
        ', '.join(fields),
        ', '.join(['?'] * len(values))
    )
    cur.execute(query, values)
    db.commit()
    food_id = cur.lastrowid
    cur.close()
    return food_id


def read_data(table, food_id=None):
    db = get_db()
    query = f'SELECT * FROM {table}'

    if food_id:
        query = f'{query} WHERE id = {food_id}'

    cur = db.execute(query)
    results = cur.fetchall()
    cur.close()
    return results


def update_data(table, new_food_type, food_id):
    db = get_db()
    cur = db.cursor()
    query = f"UPDATE {table} SET food_type = '{new_food_type}' where id = {food_id}"

    cur.execute(query)
    db.commit()

    updated_row = read_data(table=table, food_id=food_id)
    return updated_row[0]


def delete_data(table, food_id):
    db = get_db()
    cur = db.cursor()
    query = f"DELETE FROM {table} where id = {food_id}"

    cur.execute(query)
    db.commit()

    return {'message': f"Deleted row with id: {food_id}"}


@app.errorhandler(404)
def not_found():
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.errorhandler(400)
def bad_request():
    return make_response(jsonify({'error': 'Bad Request'}), 400)


# ENDPOINTS
@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/foods', methods=['GET'])
def get_foods():
    """
    Get a list of foods in inventory
    ---
    tags:
      - Awesome Food API
    responses:
      200:
        description: List of Foods
        schema:
          properties:
            name:
              type: string
              description: Name of food
            food_type:
              type: string
              description: How you categorize the food
    :return:
    """

    foods = read_data(table='foods')

    result = FoodSchema(many=True).dump(foods).data     # all the foods

    return make_response(jsonify(result), 200)  # SUCCESS


@app.route('/foods', methods=['POST'])
def add_foods():
    """
    Add food to inventory
    ---
    tags:
      - Awesome Food API
    parameters:
      - name: name
        in: query
        type: string
        required: true
        description: Name of food
      - name: food_type
        in: query
        type: string
        required: true
        description: Type of food it is

    responses:
      201:
        description: Food Created
        schema:
          properties:
            id:
              type: integer
              description: ID
            name:
              type: string
              description: Name of food
            food_type:
              type: string
              description: Type of food it is
      400:
        description: Bad Request
      422:
        description: Unprocessable Entity
    :return:
    """

    body = request.json

    if not body:
        return bad_request()  # BAD REQUEST -- killing me small, I got nothing!

    result, error = FoodSchema().load(body)

    if error:
        return make_response(jsonify(error), 422)   # UNPROCESSABLE ENTITY -- I hear what you are saying, but no

    # cleared in schema check, now to post!
    new_row_id = create_data(table='foods', fields=('name', 'food_type'),
                             values=(result['name'],
                                result['food_type']))

    result['id'] = new_row_id       # gimme the id from the db

    return make_response(jsonify(result), 201)  # CREATED


@app.route('/foods/<int:food_id>', methods=['GET'])
def get_food(food_id):
    """Find particular food in inventory
    ---
    tags:
      - Awesome Food API
    parameters:
      - name: food_id
        in: path
        type: integer
        required: true
        description: Food id
    responses:
      200:
        description: Food Found
        schema:
          properties:
            id:
              type: integer
              description: food id
            name:
              type: string
              description: Name of food
            food_type:
              type: string
              description: How you categorize the food
      404:
        description: Food not found
    :return:
    """
    food = read_data(table='foods', food_id=food_id)  # list of 1 item

    if not food:
        return not_found()  # NOT FOUND

    result = FoodSchema().dump(food[0]).data

    return make_response(jsonify(result), 200)  # SUCCESS


@app.route('/foods/<int:food_id>', methods=['PATCH'])
def update_food(food_id):
    """Update food type of a food in inventory
    ---
    tags:
      - Awesome Food API
    parameters:
      - name: food_id
        in: path
        type: integer
        required: true
        description: Food id
      - name: food_type
        in: query
        type: string
        required: true
        description: Type of food it is
    responses:
      200:
        description: Food Updated
        schema:
          properties:
            id:
              type: integer
              description: food id
            name:
              type: string
              description: Name of food
            food_type:
              type: string
              description: How you categorize the food
      400:
        description: Bad Request
      404:
        description: Food not found
      422:
        description: Unprocessable Entity
    :return:
    """
    food = read_data(table='foods', food_id=food_id)[0]  # list of 1 item

    if not food:
        return not_found()  # NOT FOUND

    body = request.json

    if not body:
        return bad_request()  # BAD REQUEST -- killing me small, I got nothing!

    result, error = FoodPatchSchema().load(body)

    if error:
        return make_response(jsonify(error))

    new_row = update_data(table='foods', new_food_type=result['food_type'], food_id=food_id)

    result = FoodSchema().dump(new_row).data

    return make_response(jsonify(result), 200)  # SUCCESS


@app.route('/foods/<int:food_id>', methods=['DELETE'])
def delete_food(food_id):
    """Delete food in inventory
    ---
    tags:
      - Awesome Food API
    parameters:
      - name: food_id
        in: path
        type: integer
        required: true
        description: Food id
    responses:
      200:
        description: Food Deleted
      404:
        description: Food not found
    :return:
    """
    food = read_data(table='foods', food_id=food_id)  # list of 1 item

    if not food:
        return not_found()  # NOT FOUND

    deleted = delete_data(table='foods', food_id=food_id)

    return make_response(jsonify(deleted), 200)  # SUCCESS


# API DOCS: http://localhost:5000/apidocs/

app.run(debug=True)
