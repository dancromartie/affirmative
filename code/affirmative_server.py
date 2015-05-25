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
import os.path

from flask import Flask, request, url_for, render_template, json

webapp = Flask(
    __name__,
    static_url_path='/affirmative/static',
    static_folder="../static"
)

logging.basicConfig(
    filename='../logs/affirmative.log', 
    level=logging.DEBUG,
    format='%(asctime)-15s %(message)s'
)
logging.info("Im alive!")


# Anything that's not dumped after this long should get purged
RECORD_LIFETIME_DAYS = 30


def get_config_db_path():
    return "../data/" + webapp.config["INSTANCE"] + ".config.db"


def get_stats_db_path():
    return "../data/" + webapp.config["INSTANCE"] + ".stats.db"


def execute_insert_disk(db_path, query, params, many=False):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    if many:
        # Params needs to be a list of tuples in this case
        cursor.executemany(query, params)
    else:
        # Params needs to be one tuple in this case
        cursor.execute(query, params)
    conn.commit()
    conn.close()


def execute_schema_build_stuff(db_path, query):
    conn = sqlite3.connect(db_path)
    conn.execute(query, ())
    conn.commit()
    conn.close()


def query_to_dicts(db_path, query, params):
    try:
        dict_results = []
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row
        query_results = cursor.execute(query, params)
        for r in query_results:
            dict_results.append(dict(r))
        return dict_results
    finally:
        conn.close()


def build_tables(config_db_path, stats_db_path):
    instance_exists = os.path.isfile(config_db_path) or os.path.isfile(stats_db_path)
    if instance_exists:
        logging.info(
            "Instance with that name already exists.  Delete db if you wanted a new one."
        )
    
    else:

        execute_schema_build_stuff(stats_db_path, """
            CREATE TABLE events (time integer, name text, data text)
        """)

        execute_schema_build_stuff(stats_db_path, """
            CREATE INDEX idx_event_time_name ON events (time, name)
        """)

        execute_schema_build_stuff(stats_db_path, """
            CREATE TABLE check_history 
            (time integer, key text, num_required integer,
                num_observed integer)
        """)

        execute_schema_build_stuff(config_db_path, "DROP TABLE IF EXISTS event_config")
        execute_schema_build_stuff(config_db_path, """
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


@webapp.route("/affirmative/store", methods=["POST"])
def store_event():
    logging.info("request data is %s", request.data)
    payload = json.loads(request.data)
    events = payload["events"]
    logging.info(events)
    to_write = []
    query = """
        INSERT INTO events (time, name, data)
        VALUES (?,?,?)
    """

    for e in events:
        to_write.append((time.time(), e["name"], e["data"]))

    execute_insert_disk(get_stats_db_path(), query, to_write, many=True)

    # Delete old rows every couple hundred/thousand of events you receive
    rando = random.randint(1, 300)
    if rando == 17:
        delete_old_rows()
    return "cool"


@webapp.route("/affirmative/check_all", methods=["GET"])
def check_all_web():
    return json.dumps(check_all())


def check_all():
    statuses = {}
    for conf in get_event_config():
        do_check(conf["key"])
    return statuses


# TODO make this a POST, but it's easier to debug as a GET right now...
@webapp.route("/affirmative/do_minutely_cron_dont_touch_this", methods=["GET"])
def do_minutely_cron():
    check_all()
    return "yay"


@webapp.route("/affirmative/get_check_history", methods=["GET"])
def get_check_history_web():
    return json.dumps(get_check_history())

@webapp.route("/affirmative/do_check/<key>", methods=["GET"])
def do_check_web(key):
    return json.dumps(do_check(key))


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


def do_check(key):
    query = "SELECT * FROM event_config WHERE key = ?"
    first_result = None
    query_results = query_to_dicts(get_config_db_path(), query, (key,))
    if len(query_results) == 0:
        return {"error": "no event configuration for that key"}
    else:
        assert len(query_results) == 1
        first_result = query_results[0]
        should_check_now = is_time_to_check(datetime.datetime.now(), first_result)
        if not should_check_now:
            return {"message": "not time for check yet"}
        name = first_result["name"]
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
        results = query_to_dicts(get_stats_db_path(), query, (epoch_cutoff, name))
        if len(results) == 0:
            count = 0
        else:
            count = results[0]["count"]
        met_required = count >= num_required
        result = {
            "count": count,
            "num_required": num_required,
            "met_required": met_required,
            "time": now_epoch
        }
        insert_query = """
            INSERT INTO check_history (time, key, num_required, num_observed)
            VALUES (?, ?, ?, ?)
        """
        data = (now_epoch, key, num_required, count)
        execute_insert_disk(get_stats_db_path(), insert_query, data)
        return result


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
    execute_insert_disk(
        get_stats_db_path(),
        "DELETE FROM events WHERE time < ?", 
        (few_days_ago_str,)
    )


@webapp.route("/affirmative/events/<name>", methods=["GET"])
def get_events(name):
    query = """
        SELECT * FROM events
        WHERE name = ?
        ORDER BY time DESC
        LIMIT 10000
    """
    results = query_to_dicts(get_stats_db_path(), query, (name,))
    return json.dumps(results)


def get_check_history():
    query = """
        SELECT * FROM check_history ORDER BY time
    """
    results = query_to_dicts(get_stats_db_path(), query, ())
    by_name = {}
    for result in results:
        if result["key"] not in by_name:
            by_name[result["key"]] = []
        by_name[result["key"]].append(result)
    return by_name


@webapp.route("/affirmative/manage_events", methods=["GET"])
def render_manage_events():
    return render_template("manage_events.html")


@webapp.route("/affirmative/view_events", methods=["GET"])
def render_view_events():
    return render_template("view_events.html")


@webapp.route("/affirmative/about", methods=["GET"])
def render_about():
    return render_template("about.html")


@webapp.route("/affirmative/trigger", methods=["GET"])
def render_trigger():
    return render_template("trigger.html")


@webapp.route("/affirmative/get_event_config", methods=["GET"])
def get_event_config_web():
    return json.dumps(get_event_config())


def get_event_config():
    event_config = []
    query = "SELECT * FROM event_config"
    results = query_to_dicts(get_config_db_path(), query, ())
    return results


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


@webapp.route("/affirmative/register_event", methods=["POST"])
def register_event():
    event_name = request.form["event_name"]
    key_components = [
        letter for letter in string.ascii_letters] + [str(d) for d in range(1, 10)
    ]
    key = "".join([random.choice(key_components) for i in range(6)])
    insert_query = """
        INSERT INTO event_config (name, key, num_required, lookback_string, cron_minutes, 
            cron_hours, cron_days_of_month, cron_months, cron_days_of_week
        )
        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    data = (event_name, key, 0, "1000d", 1, 1, 1, 1, 1)
    execute_insert_disk(get_config_db_path(), insert_query, data)
    return "yay"


@webapp.route("/affirmative/update_event_config", methods=["POST"])
def update_event_config():
    key = request.form["key"]

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

    update_query = """
        UPDATE event_config SET num_required = ?, lookback_string = ?, cron_minutes = ?,
        cron_hours = ?, cron_days_of_month = ?, cron_months = ?, cron_days_of_week = ?
        WHERE key = ?
    """
    data = (
        num_required, lookback_string, cron_minutes,
        cron_hours, cron_days_of_month, cron_months, cron_days_of_week, key
    )
    execute_insert_disk(get_config_db_path(), update_query, data)

    return "yay"


@webapp.route("/affirmative/unregister_event", methods=["POST"])
def unregister_event():
    key = request.form["key_to_delete"]
    execute_insert_disk(get_config_db_path(), "DELETE FROM event_config WHERE key = ?", (key,))
    return "yay"


def build_app(debug, instance):
    # When you tell gunicorn check:webapp, you're really pointing it to a 'wsgi callable'
    # You can also give it a function that returns a callable, such as this one
    # We can put whatever options we want here.
    logging.info("instance is %s" % instance)
    logging.info("using debug=%s" % debug)
    webapp.config["DEBUG"] = debug
    webapp.config["INSTANCE"] = instance

    build_tables(config_db_path=get_config_db_path(), stats_db_path=get_stats_db_path())
    logging.info("got here")

    return webapp


