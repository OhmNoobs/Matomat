# -*- coding: utf-8 -*-
import json
import os
import sqlite3
import itertools
from flask import Flask, request, session, g, abort
from datetime import datetime


app = Flask(__name__)  # create the application instance :)
app.config.from_object(__name__)  # load config from this file, cashier.py
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'bmp', 'ico'}
# Load default config
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'matomat.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default',
    PATH_TO_ITEM_IMAGES=os.path.join(app.root_path, 'static', 'images'),
    ALLOWED_EXTENSIONS=ALLOWED_EXTENSIONS
))
# And override config from an environment variable...
# Simply define the environment variable MATOMAT_SETTINGS that points to a config file to be loaded.
app.config.from_envvar('MATOMAT_SETTINGS', silent=True)


@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')


def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    rv.execute('PRAGMA foreign_keys = ON;')
    rv.commit()
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


@app.route('/api')
def hello_humans():
    return "This is an API, not for HOOOOMANS!"


@app.route('/api/add/item', methods=['POST'])
def add_item():
    item_info = request.get_json(force=True)  # type: dict
    if not session.get('logged_in'):
        abort(401)
    if not item_info or 'price' not in item_info or 'title' not in item_info:
        abort(400)
    price = evaluate_price(item_info['price'])
    color = item_info['color']
    image = None
    if 'image' in item_info:
        image = item_info['image']
    db = get_db()
    cursor = db.cursor()
    cursor.execute('INSERT INTO Products (name, price, image, color) VALUES (?, ?, ?, ?)',
                   [item_info['title'], price, image, color])
    db.commit()
    return get_item(cursor.lastrowid)


def evaluate_price(price: str):
    if isinstance(price, str):
        price = price.replace(',', '.')
    return float(price)


@app.route('/api/get/items')
def get_items():
    db = get_db()
    cur = db.execute('SELECT id, name, price, image, color FROM Products ORDER BY id DESC')
    rows = cur.fetchall()
    all_items = []
    for row in rows:
        all_items.append(build_item(row))
    return json.dumps(all_items)


def build_item(row):
    item = {'id': row[0], 'title': row[1], 'price': row[2]}
    if row[3]:
        item['image'] = row[3]
    if row[4]:
        item['color'] = row[4]
    return item


@app.route('/api/get/item/<identifier>')
def get_item(identifier):
    try:
        int(identifier)
    except ValueError:
        abort(400)
    db = get_db()
    cur = db.execute('SELECT id, name, price, image, color FROM Products WHERE id = (?)', [identifier])
    item = cur.fetchone()
    if not item:
        abort(400)
    item_for_json = {'id': item[0], 'title': item[1], 'price': item[2]}
    if item[3]:
        item_for_json.update({'image': item[3]})
    if item[4]:
        item_for_json.update({'color': item[4]})
    return json.dumps(item_for_json)


@app.route('/api/delete/item/<identifier>/', methods=['DELETE'])
def delete_item(identifier):
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute('DELETE FROM Products WHERE id = (?)', [identifier])
    db.commit()
    return json.dumps('success')


@app.route('/api/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        credentials = request.get_json(force=True)  # type: dict
        if credentials['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif credentials['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:

            # expire_date = datetime.now()
            # expire_date = expire_date + datetime.timedelta(days=90)
            # response.set_cookie(key, guid, expires=expire_date)
            session['logged_in'] = True
            return json.dumps({'result': 'ok'})
    return json.dumps({'result': error})


@app.route('/api/logout')
def logout():
    session.pop('logged_in', None)
    return json.dumps('ok')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def malformed_receipt(receipt):
    for possible_item in receipt:
        if 'sender' not in possible_item:
            return False
    return True


@app.route('/api/add/transaction', methods=['POST'])
def add_transaction():
    receipt = request.get_json(force=True)  # type: dict

    if (not receipt) or malformed_receipt(receipt):
        abort(422)

    db = get_db()

    del receipt['sum']
    cur = db.execute('INSERT INTO Transactions ("from", "to", timestamp) VALUES (?, ?, ?)',
                     [int(receipt['sender']), int(receipt['receiver']), str(datetime.now())])
    transaction_id = cur.lastrowid
    db.commit()

    for item_id, value in receipt.items():
        for _ in itertools.repeat(None, value['amount']):
            db.execute('INSERT INTO Transaction_Products ("transaction", product) VALUES (?, ?)',
                       [int(transaction_id), int(item_id)])
    db.commit()
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@app.route('/api/update/item', methods=['PUT'])
def update_item_shorthand():
    item_info = request.get_json(force=True)  # type: dict
    if not session.get('logged_in'):
        abort(401)
    if not item_info or 'price' not in item_info or 'title' not in item_info:
        abort(400)
    return update_item(item_info['id'])


@app.route('/api/update/item/<identifier>', methods=['PUT'])
def update_item(identifier):
    item_info = request.get_json(force=True)  # type: dict
    if not session.get('logged_in'):
        abort(401)
    if not item_info or 'price' not in item_info or 'title' not in item_info or identifier != item_info['id']:
        abort(400)
    price = evaluate_price(item_info['price'])
    color = item_info['color']
    image = None
    if 'image' in item_info:
        image = item_info['image']
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE Products SET name = ?, price = ?, image = ?, color = ? WHERE id = ?',
                   [item_info['title'], price, image, color, identifier])
    db.commit()
    return get_item(identifier)


@app.route('/api/add/credit', methods=['POST'])
def add_credit():
    pass


@app.route('/api/get/balance/<user_id>', methods=['POST'])
def get_balance(user_id):
    pass
