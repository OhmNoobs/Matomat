import json
import locale
import os
import platform
import sqlite3
import subprocess
import itertools
from datetime import datetime
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from werkzeug.utils import secure_filename

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
# Simply define the environment variable CASHIER_SETTINGS that points to a config file to be loaded.
app.config.from_envvar('CASHIER_SETTINGS', silent=True)
customer_number = 0

if platform.system() == 'Windows':
    locale.setlocale(locale.LC_ALL, 'de-DE')
elif platform.system() == 'Linux':
    locale.setlocale(locale.LC_ALL, 'de_DE')


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


@app.route('/')
def show_items():
    db = get_db()
    cur = db.execute('SELECT id, name, price, image_link, color FROM Products ORDER BY id DESC')
    items = cur.fetchall()
    return render_template('manage_items.html', items=items)


@app.route('/add/item', methods=['POST'])
def add_item():
    if not session.get('logged_in'):
        abort(401)
    price = evaluate_price(request.form['price'])
    color = request.form['color']
    filename = None
    # check if the post request has the file part
    if 'file' in request.files:
        file = request.files['file']
        # check if the file part contains a value and is allowed
        if file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            try:
                file.save(os.path.join(app.config['PATH_TO_ITEM_IMAGES'], filename))
            except FileNotFoundError:
                os.mkdir(os.path.join(app.root_path, 'static', 'images'))
                file.save(os.path.join(app.config['PATH_TO_ITEM_IMAGES'], filename))
            color = None
    db = get_db()
    db.execute('INSERT INTO Products (name, price, image_link, color) VALUES (?, ?, ?, ?)',
               [request.form['title'], price, filename, color])
    db.commit()
    flash('New item was successfully added.')
    return redirect(url_for('show_items'))


def evaluate_price(price: str):
    price = price.replace(',', '.')
    return float(price)


@app.route('/get/items')
def get_items():
    db = get_db()
    cur = db.execute('SELECT id, name, price, image_link, color FROM Products ORDER BY id DESC')
    rows = cur.fetchall()
    all_items = {}
    for row in rows:
        all_items[row[0]] = build_item(row)
    return json.dumps(all_items)


def build_item(row):
    item = {'title': row[1], 'price': row[2]}
    if row[3]:
        item['image_link'] = row[3]
    if row[4]:
        item['color'] = row[4]
    return item


@app.route('/get/item/<identifier>')
def get_item(identifier):
    try:
        int(identifier)
    except ValueError:
        abort(400)
    db = get_db()
    cur = db.execute('SELECT id, name, price, image_link, color FROM Products WHERE id = (?)', [identifier])
    item = cur.fetchone()
    if not item:
        abort(400)
    item_for_json = {'id': item[0], 'title': item[1], 'price': item[2]}
    if item[3]:
        item_for_json.update({'image_link': item[3]})
    if item[4]:
        item_for_json.update({'color': item[4]})
    return json.dumps(item_for_json)


@app.route('/delete/item/<identifier>/', methods=['DELETE'])
def delete_item(identifier):
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute('DELETE FROM Products WHERE id = (?)', [identifier])
    db.commit()
    return redirect(url_for('show_items'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_items'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_items'))


@app.route('/work')
def work_view():
    if not session.get('logged_in'):
        abort(401)
    global customer_number
    db = get_db()
    cur = db.execute('SELECT id, name, price, image_link, color FROM Products ORDER BY id DESC')
    items = cur.fetchall()
    customer_number += 1
    return render_template('work_view.html', items=items, customer=customer_number)


def print_receipt(data):
    if platform.system() == 'Windows':
        with open(app.config['PRINT_FILE']) as f:
            f.write(data)
        os.startfile(app.config['PRINT_FILE'], "print")
    elif platform.system() == 'Linux':
        print(data)
        lpr = subprocess.run(["/dev/usb/pl0"], stdin=subprocess.PIPE)
        lpr.stdin.write(str.encode(data))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def malformed_receipt(receipt):
    for possible_item in receipt:
        if 'sender' not in possible_item:
            return False
    return True


@app.route('/add/transaction', methods=['POST'])
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


@app.route('/add/credit', methods=['POST'])
def add_credit():
    pass


@app.route('/get/balance/<user_id>', methods=['POST'])
def get_balance(user_id):
    pass


if __name__ == '__main__':
    app.run()
