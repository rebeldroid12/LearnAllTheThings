import os
import sqlite3
from flask import Flask, request, g, jsonify, make_response


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


@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/employees', methods=['GET', 'POST'])
def employees():

    if request.method == 'GET':
        db = get_db()
        cur = db.execute('select * from employees;')
        employees = cur.fetchall()

        result = []

        # data returned as Row object, must access data as it were a dictionary
        for employee in employees:
            data = {
              'name': employee['name'],
              'department': employee['department'],
              'salary': employee['salary']
            }
            result.append(data)

        return make_response(jsonify(result), 200)      # SUCCESS

    elif request.method == 'POST':
        body = request.json

        if not body:
            return bad_request()    # BAD REQUEST

        else:
            result = {
                'name': body['name'],
                'department': body['department'],
                'salary': body['salary']
            }

            new_row_id = insert(table='employees', fields=('name', 'department', 'salary'),
                                values=(result['name'],
                                result['department'],
                                result['salary']))

            result['id'] = new_row_id

        return make_response(jsonify(result), 201)      # CREATED


@app.route('/employees/<int:id>', methods=['GET'])
def get_employees(id):
    db = get_db()
    cur = db.execute('select * from employees where id = {}'.format(id))
    employee = cur.fetchone()   # not a list, just one row that is form of list

    if employee:
        result = {
            'name': employee['name'],
            'department': employee['department'],
            'salary': employee['salary']
        }
        return make_response(jsonify(result), 200)      # SUCCESS

    else:
        return not_found()      # NOT FOUND
