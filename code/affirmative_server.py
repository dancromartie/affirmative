from math import sin, cos, radians, acos
import datetime
from datetime import date, timedelta
import logging
import re
import sqlite3
import sys
import random
import string

from flask import Flask, request, url_for, render_template, json

webapp = Flask(__name__)

logging.basicConfig(
    filename='../logs/affirmative.log', 
    level=logging.DEBUG,
    format='%(asctime)-15s %(message)s'
)
logging.info("Im alive!")

db_conn = sqlite3.connect(":memory:")
db_cursor = db_conn.cursor()
db_cursor.row_factory = sqlite3.Row

db_cursor.execute("DROP TABLE IF EXISTS events;")
db_conn.commit()
table_creation_string = "CREATE TABLE events (time text, env text, name text, data text)"
db_cursor.execute(table_creation_string)
db_cursor.execute("CREATE INDEX idx_event_time_name ON events (time, env, name)")
db_conn.commit()

disk_conn = sqlite3.connect("../data/affirmative.db")
disk_cursor = disk_conn.cursor()
disk_cursor.row_factory = sqlite3.Row

RECORD_LIFETIME_DAYS = 2

def build_event_config_tables():
    disk_cursor.execute("DROP TABLE IF EXISTS event_config")
    disk_cursor.execute("CREATE TABLE event_config (name, key, num_required, clear_every_hours)")
    disk_conn.commit()

@webapp.route("/affirmative/store", methods=["POST"])
def store_event():
    payload = json.loads(request.data)
    events = payload["events"]
    logging.info(events)
    to_write = []
    query = """
        INSERT INTO events (env, time, name, data)
        VALUES (?,?,?,?)
    """

    for e in events:
        to_write.append((e["env"], e["time"], e["name"], e["data"]))

    db_cursor.executemany(query, to_write)
    db_conn.commit()

    # Delete old rows every couple hundred/thousand of events you receive
    rando = random.randint(1, 300)
    if rando == 17:
        delete_old_rows()
    return "cool"


def get_few_days_ago_string():
    today = datetime.datetime.now()
    delta = datetime.timedelta(days=RECORD_LIFETIME_DAYS)
    few_days_ago = today - delta
    few_days_ago_str = few_days_ago.strftime("%Y-%m-%d")
    return few_days_ago_str


def delete_old_rows():
    logging.info("DELETING OLD ROWS")
    few_days_ago_str = get_few_days_ago_string()
    db_cursor.execute("DELETE FROM events WHERE time < ?", (few_days_ago_str,))
    db_conn.commit()


@webapp.route("/affirmative/get_events/<env>/<name>", methods=["GET"])
def get_events(env, name):
    to_return = []
    few_days_ago_str = get_few_days_ago_string()
    query = """
        SELECT * FROM events
        WHERE
        env = ? AND name = ? AND time > ?
        ORDER BY time DESC
        LIMIT 10000
    """
    results = db_cursor.execute(query, (env, name, few_days_ago_string))
    for result in results:
        to_return.append(dict(result))
    return json.dumps(to_return)


@webapp.route("/affirmative/manage_events", methods=["GET"])
def render_manage_events():
    return render_template("manage_events.html")


@webapp.route("/affirmative/get_event_config", methods=["GET"])
def get_event_config_web():
    return json.dumps(get_event_config())


def get_event_config():
    event_config = []
    query = "SELECT * FROM event_config"
    results = disk_cursor.execute(query, ())
    for result in results:
        event_config.append(dict(result))
    return event_config


@webapp.route("/affirmative/register_new_event", methods=["POST"])
def register_new_event():
    event_name = request.form["name"]
    num_required = int(request.form["num_required"])
    clear_every_hours = int(request.form["clear_every_hours"])
    query = """
        INSERT INTO event_config (name, key, num_required, clear_every_hours)
        VALUES
        (?, ?, ?, ?)
    """
    key_components = [letter for letter in string.ascii_letters] + [str(d) for d in range(1, 10)]
    key = "".join([random.choice(key_components) for i in range(6)])
    data = (event_name, key, num_required, clear_every_hours)
    disk_cursor.execute(query, data)
    disk_conn.commit()
    return "yay"


@webapp.route("/affirmative/unregister_event", methods=["POST"])
def unregister_event():
    name = request.form["event-name-to-delete"]
    disk_cursor.execute("DELETE FROM event_config WHERE name = ?", (name,))
    disk_conn.commit()
    return render_template("manage_events.html")


def build_app(debug):
    # When you tell gunicorn check:webapp, you're really pointing it to a 'wsgi callable'
    # You can also give it a function that returns a callable, such as this one
    # We can put whatever options we want here.
    logging.info("using debug=%s" % debug)
    webapp.config["DEBUG"] = debug
    return webapp

