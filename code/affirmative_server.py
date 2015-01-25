from math import sin, cos, radians, acos
import time
import datetime
from datetime import date, timedelta
import logging
import re
import sqlite3
import sys
import random
import string
import copy

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
table_creation_string = "CREATE TABLE events (time integer, env text, name text, data text)"
db_cursor.execute(table_creation_string)
db_cursor.execute("CREATE INDEX idx_event_time_name ON events (time, env, name)")
db_conn.commit()

disk_conn = sqlite3.connect("../data/affirmative.db")
disk_cursor = disk_conn.cursor()
disk_cursor.row_factory = sqlite3.Row

RECORD_LIFETIME_DAYS = 2

event_config = []
check_history = {}

def build_event_config_tables():
    disk_cursor.execute("DROP TABLE IF EXISTS event_config")
    disk_cursor.execute("""
        CREATE TABLE event_config (
            name text, 
            key text, 
            num_required integer, 
            lookback_string integer, 
            cron_minutes text,
            cron_hours text,
            cron_days_of_month text,
            cron_months text,
            cron_days_of_week text
        )
    """)
    disk_conn.commit()

@webapp.route("/affirmative/store", methods=["POST"])
def store_event():
    logging.info("request data is ", request.data)
    payload = json.loads(request.data)
    events = payload["events"]
    logging.info(events)
    to_write = []
    query = """
        INSERT INTO events (env, time, name, data)
        VALUES (?,?,?,?)
    """

    for e in events:
        to_write.append((e["env"], time.time(), e["name"], e["data"]))

    db_cursor.executemany(query, to_write)
    db_conn.commit()

    # Delete old rows every couple hundred/thousand of events you receive
    rando = random.randint(1, 300)
    if rando == 17:
        delete_old_rows()
    return "cool"


@webapp.route("/affirmative/get_status_of_all", methods=["GET"])
def get_status_of_all_web():
    return json.dumps(get_status_of_all())


def get_status_of_all():
    statuses = {}
    for conf in event_config:
        statuses[conf["name"]] = do_check(conf["name"])
    return statuses


# TODO make this a POST, but it's easier to debug as a GET right now...
@webapp.route("/affirmative/do_minutely_cron_dont_touch_this", methods=["GET"])
def do_minutely_cron():
    global check_history
    statuses = get_status_of_all()
    for name in statuses:
        if name not in check_history:
            check_history[name] = []
        if "met_required" in statuses[name]:
            check_history[name].append(statuses[name])
    return "yay"


@webapp.route("/affirmative/get_check_history", methods=["GET"])
def get_check_history_web():
    return json.dumps(check_history)

@webapp.route("/affirmative/do_check/<name>", methods=["GET"])
def do_check_web(name):
    return json.dumps(do_check(name))


def passes_cron_criteria(num, cron_expression):
    if str(num) == cron_expression:
        return True
    if cron_expression == "*":
        return True
    if "," in cron_expression:
        splitup = cron_expression.split(",")
        for x in splitup:
            if x == str(num):
                return True
    if "-" in cron_expression:
        splitup = cron_expression.split("-")
        if num <= int(splitup[1]) and num >= int(splitup[0]):
            return True
    if "/" in cron_expression:
        splitup = cron_expression.split("/")
        if num % int(splitup[0]) == 0:
            return True
    return False


def is_time_to_check(datetime_obj, config_record):
    if not passes_cron_criteria(datetime_obj.minute, config_record["cron_minutes"]):
        return False
    if not passes_cron_criteria(datetime_obj.hour, config_record["cron_hours"]):
        return False
    if not passes_cron_criteria(datetime_obj.day, config_record["cron_days_of_month"]):
        return False
    if not passes_cron_criteria(datetime_obj.month, config_record["cron_months"]):
        return False
    if not passes_cron_criteria(datetime_obj.weekday(), config_record["cron_days_of_week"]):
        return False
    return True


def do_check(name):
    query = "SELECT * FROM event_config WHERE name = ?"
    disk_cursor.execute(query, (name,))
    first_result = disk_cursor.fetchone()
    if first_result is None:
        return {"error": "no event configuration for that name"}
    else:
        should_check_now = is_time_to_check(datetime.datetime.now(), first_result)
        if not should_check_now:
            return {"message": "not time for check yet"}
        lookback_string = first_result["lookback_string"]
        num_required = first_result["num_required"]
        now_epoch = time.time()
        epoch_delta = epoch_delta_from_lookback_string(lookback_string)
        epoch_cutoff = now_epoch - epoch_delta
        query = """
            SELECT count(1) as count, name
            FROM events 
            WHERE time > ?
            AND name = ?
        """
        db_cursor.execute(query, (epoch_cutoff, name))
        first_result = db_cursor.fetchone()
        if first_result is None:
            count = 0
        else:
            count = first_result["count"]
        met_required = count >= num_required
        return {"count": count, "met_required": met_required, "time": now_epoch}


def epoch_delta_from_lookback_string(lookback_string):
    if lookback_string[-1:] == "m":
        seconds = int(lookback_string[:-1]) * 60
    elif lookback_string[-1:] == "h":
        seconds = int(lookback_string[:-1]) * 60 * 60
    elif lookback_string[-1:] == "d":
        seconds = int(lookback_string[:-1]) * 60 * 60 * 24
    else:
        sys.exit("lookback string conversion failed on %s" % lookback_string)
    return seconds


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


@webapp.route("/affirmative/get_all_stats", methods=["GET"])
def get_all_stats_web():
    return json.dumps(get_all_stats())


def get_all_stats():
    stats_by_name = {}
    stats_to_return = []
    event_config_copy = copy.deepcopy(event_config)
    query = "SELECT count(1) as count, name FROM events WHERE env='prod' GROUP BY name"
    results = db_cursor.execute(query, ())
    for r in results:
        stats_by_name[r["name"]] = dict(r)
    for conf in event_config_copy:
        if conf["name"] in stats_by_name: 
            to_append = stats_by_name[conf["name"]]
        else:
            to_append = {"name": conf["name"], "count": 0}

        to_append.update(conf)
        stats_to_return.append(to_append)
    return stats_to_return
    

@webapp.route("/affirmative/manage_events", methods=["GET"])
def render_manage_events():
    return render_template("manage_events.html")


@webapp.route("/affirmative/view_events", methods=["GET"])
def render_view_events():
    update_event_config()
    return render_template("view_events.html")


@webapp.route("/affirmative/get_event_config", methods=["GET"])
def get_event_config_web():
    update_event_config()
    return json.dumps(get_event_config())


def get_event_config():
    event_config = []
    query = "SELECT * FROM event_config"
    results = disk_cursor.execute(query, ())
    for result in results:
        event_config.append(dict(result))
    return event_config


def is_valid_cron_number(s):
    # TODO, woops, you treated them all like 0-59, but days of week have a different valid range...
    if not s.isdigit():
        return False
    d = int(s)
    if d > 59 or d < 0:
        return False
    return True


def invalid_slashy_cron_thing_message(s):
    splitup = s.split("/")
    if len(splitup) != 2:
        return "Slashy thing must have two components."
    if splitup[0] != "*":
        return "First part of slashy thing must be an asterisk."
    if not is_valid_cron_number(splitup[1]):
        return "Number after slash must be a valid cron number."
    elif int(splitup[1]) == 1 or int(splitup[1]) == 0:
        return "0 or 1 are not valid numbers after a slash.  You can express it in another way."
    return ""


def invalid_hypheny_cron_thing_message(s):
    splitup = s.split("-")
    if len(splitup) != 2:
        return "Hypheny thing must have two components"
    if not is_valid_cron_number(splitup[0]) or not is_valid_cron_number(splitup[1]):
        return "Both components of hypheny thing must be valid cron numbers."
    if int(splitup[0]) >= int(splitup[1]):
        return "First number in hyphyeny thing must be less than second."
    return ""


def invalid_comma_sep_cron_thing_message(s):
    splitup = s.split(",")
    seen_already = {}
    max_so_far = -1
    for num in splitup:
        if not is_valid_cron_number(num):
            return "All parts of comma separated expression must be valid cron numbrs."
        if num in seen_already:
            return "Cannot repeat numbers in comma separated expression."
        if int(num) <= max_so_far:
            return "Each number in a comma separated expression must be bigger than previous."
        else:
            max_so_far = int(num)
        seen_already[num] = 1
    return ""


def invalid_cron_string_message(s):
    if " " in s:
        return "Cannot have whitespace in cron expression."
    if not re.match("^[0-9*,/\-]+$", s):
        return "Invalid characters detected in cron expression."
    if "/" in s:
        if invalid_slashy_cron_thing_message(s):
            return invalid_slashy_cron_thing_message(s)
        else:
            return ""
    if "-" in s:
        if invalid_hypheny_cron_thing_message(s):
            return invalid_hypheny_cron_thing_message(s)
        else:
            return ""
    if "," in s:
        if invalid_comma_sep_cron_thing_message(s):
            return invalid_comma_sep_cron_thing_message(s)
        else:
            return ""
    if s.isdigit():
        if not is_valid_cron_number(s):
            return "Lone cron number must be in valid range."
        else:
            return ""
    if s == "*":
        return ""
    return "Cron expression has unknown problem.  Check formatting."


def invalid_lookback_string_message(s):
    if not re.match("^[0-9]+(m|h|d)$", s):
        return "Lookback string must be digits followed by m, h, or d."
    return ""


def invalid_num_required_message(s):
    if not s.isdigit():
        return "Num required must be a digit."
    elif int(s) < 0:
        return "Num required must be positive"
    return ""


@webapp.route("/affirmative/register_or_update_event", methods=["POST"])
def register_or_update_event():
    event_name = request.form["name"]

    lookback_string = request.form["lookback_string"]
    if invalid_lookback_string_message(lookback_string):
        return invalid_lookback_string_message(lookback_string)

    num_required_string = request.form["num_required"]
    if invalid_num_required_message(num_required_string):
        return invalid_num_required_message(num_required_string)

    num_required = int(num_required_string)

    cron_minutes = request.form["cron_minutes"]
    cron_hours = request.form["cron_hours"]
    cron_days_of_month = request.form["cron_days_of_month"]
    cron_months = request.form["cron_months"]
    cron_days_of_week = request.form["cron_days_of_week"]

    to_validate = [cron_minutes, cron_hours, cron_days_of_month, cron_months, cron_days_of_week]

    # The message functions return "" if everything is good, and a message if something is wrong
    for val in to_validate:
        if invalid_cron_string_message(val):
            return invalid_cron_string_message(val)

    already_exists_query = """SELECT name FROM event_config WHERE name = ? """
    disk_cursor.execute(already_exists_query, (event_name,))
    first_result = disk_cursor.fetchone()
    if first_result is None:
        insert_query = """
            INSERT INTO event_config (
                name, key, num_required, lookback_string, cron_minutes,
                cron_hours, cron_days_of_month, cron_months, cron_days_of_week
            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        key_components = [
            letter for letter in string.ascii_letters] + [str(d) for d in range(1, 10)
        ]
        key = "".join([random.choice(key_components) for i in range(6)])
        data = (
            event_name, key, num_required, lookback_string, cron_minutes,
            cron_hours, cron_days_of_month, cron_months, cron_days_of_week
        )
        disk_cursor.execute(insert_query, data)
        disk_conn.commit()
    else:
        update_query = """
            UPDATE event_config SET num_required = ?, lookback_string = ?, cron_minutes = ?,
            cron_hours = ?, cron_days_of_month = ?, cron_months = ?, cron_days_of_week = ?
            WHERE name = ?
        """
        data = (
            num_required, lookback_string, cron_minutes,
            cron_hours, cron_days_of_month, cron_months, cron_days_of_week, event_name
        )
        disk_cursor.execute(update_query, data)

        disk_conn.commit()

    update_event_config()
    return "yay"


@webapp.route("/affirmative/unregister_event", methods=["POST"])
def unregister_event():
    name = request.form["name_to_delete"]
    disk_cursor.execute("DELETE FROM event_config WHERE name = ?", (name,))
    disk_conn.commit()
    update_event_config()
    return "yay"


def update_event_config():
    global event_config
    event_config = []
    query = "SELECT * FROM event_config"
    results = disk_cursor.execute(query, ())
    for r in results:
        event_config.append(dict(r))


def build_app(debug):
    # When you tell gunicorn check:webapp, you're really pointing it to a 'wsgi callable'
    # You can also give it a function that returns a callable, such as this one
    # We can put whatever options we want here.
    logging.info("using debug=%s" % debug)
    webapp.config["DEBUG"] = debug
    update_event_config()
    return webapp

