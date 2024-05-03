import json
import requests
import redis

from authlib.integrations.flask_client import OAuth
from flask import Flask, abort, redirect, render_template, session, url_for, request
from flask_session import Session
from dateutil.relativedelta import *
from dateutil.easter import *
from dateutil.rrule import *
from dateutil.parser import *
from datetime import *
import pytz

app = Flask(__name__)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = True

appConf = {
    "OAUTH2_CLIENT_ID": "",
    "OAUTH2_CLIENT_SECRET": "",
    "OAUTH2_META_URL": "https://accounts.google.com/.well-known/openid-configuration",
    "FLASK_SECRET": "",
    "FLASK_PORT": 5000
}

app.secret_key = appConf.get("FLASK_SECRET")

oauth = OAuth(app)
# List of google scopes - https://developers.google.com/identity/protocols/oauth2/scopes
oauth.register(
    "myApp",
    client_id=appConf.get("OAUTH2_CLIENT_ID"),
    client_secret=appConf.get("OAUTH2_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email https://www.googleapis.com/auth/user.birthday.read https://www.googleapis.com/auth/user.gender.read https://www.googleapis.com/auth/calendar",
    },
    server_metadata_url=f'{appConf.get("OAUTH2_META_URL")}',
)

Session(app)


@app.route("/")
def home():
    session_state = manage_session_login()
    if session_state == 1:
        return render_template("renew_login.html")
    if session_state == 2:
        return render_template("welcome.html")
    # If session_state == 0 continue as normal: user is logged in and auth session is not expired
    return redirect("/hours")
    

@app.route("/hours")
def hours():
    session_state = manage_session_login()
    if session_state == 1:
        return render_template("renew_login.html")
    if session_state == 2:
        return render_template("welcome.html")
    # If session_state == 0 continue as normal: user is logged in and auth session is not expired

    calendars = get_calendars(session.get("user"))
    events = get_all_events(session.get("user"))
    hours = {}

    for calendar in calendars["items"]:
        # Just for test calendar for now, remove the if statement
        # if calendar["summary"] == "My Test Calendar":
            classic_color = calendar["backgroundColor"]
            modern_color = get_modern_color(calendar["colorId"], classic_color)

            hours[calendar["id"]] = {"summary": calendar["summary"], "classic_color": classic_color, "modern_color": modern_color, "week": 0, "month": 0, "prev_month": 0, "year": 0}
            
            pages = events[calendar["id"]]

            for page in pages:
                for event in page["items"]:
                    try:
                        event_start = parse(event["start"]["dateTime"])
                        event_end = parse(event["end"]["dateTime"])
                    except:
                        continue

                    duration_in_hours = round(get_duration(event) / 3600.0, 2)

                    # Account for timezont of user's event
                    today = datetime.today()
                    today = today.replace(tzinfo=event_start.tzinfo).astimezone(tz=event_start.tzinfo)

                    # Previous monday
                    start_of_week = today + relativedelta(weekday=MO(-1), hour=0, minute=0, second=0)
                    # Next monday, but not today
                    end_of_week = today + relativedelta(days=+1, weekday=MO(+1), hour=0, minute=0, second=0)

                    start_of_month = today + relativedelta(day=1, hour=0, minute=0, second=0)
                    end_of_month = today + relativedelta(months=+1, day=1, hour=0, minute=0, second=0)

                    start_of_prev_month = today + relativedelta(months=-1, day=1, hour=0, minute=0, second=0)
                    end_of_prev_month = today + relativedelta(day=1, hour=0, minute=0, second=0)

                    start_of_year = today + relativedelta(month=1, day=1, hour=0, minute=0, second=0)
                    end_of_year = today + relativedelta(years=+1, month=1, day=1, hour=0, minute=0, second=0)

                    # Could make it work for every month or every year with a switch case dictionary like {"jan": 0} and iterating through it maybe, adding it all to hours

                    # During current week
                    if event_start > start_of_week and event_end < end_of_week:
                        hours[calendar["id"]]["week"] += duration_in_hours
                    
                    # During current month up to the end of current week
                    if event_start > start_of_month and event_start < end_of_month and event_end < end_of_week:
                        hours[calendar["id"]]["month"] += duration_in_hours

                    # During previous month
                    if event_start > start_of_prev_month and event_start < end_of_prev_month and event_end < end_of_week:
                        hours[calendar["id"]]["prev_month"] += duration_in_hours

                    # During current year up to the end of current week
                    if event_start > start_of_year and event_start < end_of_year and event_end < end_of_week:
                        hours[calendar["id"]]["year"] += duration_in_hours

    print(session.get("user")["default_colors_state"])
    return render_template("hours.html", hours=hours, default_colors_state=session.get("user")["default_colors_state"])


@app.route("/change_default_colors")
def chage_default_colors():
    default_colors_state = session.get("user")["default_colors_state"]
    if default_colors_state == "modern":
        session["user"]["default_colors_state"] = "classic"
    elif default_colors_state == "classic":
        session["user"]["default_colors_state"] = "modern"
    return redirect("/hours")


@app.route("/callback")
def callback():
    # Fetch access token and id token using authorization code
    token = oauth.myApp.authorize_access_token()

    # Can be "classic" or "modern". Set as modern on login
    token["default_colors_state"] = "modern"
    session["user"] = token
    return redirect(url_for("home"))


@app.route("/login")
def login():
    if "user" in session:
        abort(404)
    return oauth.myApp.authorize_redirect(redirect_uri=url_for("callback", _external=True))


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=appConf.get(
        "FLASK_PORT"), debug=True)


def get_calendars(token):
    calendars_url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
    calendars = requests.get(calendars_url, headers={
        "Authorization": f"Bearer {token['access_token']}"
    }).json()

    return calendars


def get_colors(token):
    colors_url = "https://www.googleapis.com/calendar/v3/colors"
    colors = requests.get(colors_url, headers={
        "Authorization": f"Bearer {token['access_token']}"
    }).json()

    return colors


# Gets all events for all calendars in a dictionary where keys are calendar ids
def get_all_events(token):
    calendars = get_calendars(token)
    events = {}

    today = datetime.today()
    time_min = today + relativedelta(years=-1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    time_max = today + relativedelta(days=+1, weekday=MO(+2), hour=0, minute=0, second=0, microsecond=0)

    time_min_str = time_min.isoformat("T") + "Z"
    time_max_str = time_max.isoformat("T") + "Z"
    max_results = "2500"
    fields = "nextPageToken,summary,items(start/dateTime,end/dateTime,recurringEventId,summary)"
    
    for calendar in calendars["items"]:
        calendar_events_url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar['id']}/events?singleEvents={'True'}&orderBy={'startTime'}&maxResults={max_results}&fields={fields}&timeMin={time_min_str}&timeMax={time_max_str}"
        events[calendar["id"]] = []

        while True:
            page_of_events = requests.get(calendar_events_url, headers={
                "Authorization": f"Bearer {token['access_token']}",
            }).json()
            events[calendar["id"]].append(page_of_events)

            if page_of_events.get("nextPageToken"):
                calendar_events_url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar['id']}/events?singleEvents={'True'}&orderBy={'startTime'}&maxResults={max_results}&fields={fields}&timeMin={time_min_str}&timeMax={time_max_str}&pageToken={page_of_events['nextPageToken']}"
            else:
                break

    return events


# Parses a Google Calendar event and returns duration of that event in seconds
def get_duration(event):
    start = event["start"]["dateTime"]
    end = event["end"]["dateTime"]

    start_datetime = parse(start)
    end_datetime = parse(end)

    delta = relativedelta(end_datetime, start_datetime)
    duration_in_seconds = delta.days*3600*24 + delta.hours*3600 + delta.minutes*60 + delta.seconds

    return duration_in_seconds

def get_modern_color(id, background_color):
    MODERN_COLORS = {
        "1": "#795548",
        "2": "#E67C73",
        "3": "#D50000",
        "4": "#F4511E",
        "5": "#EF6C00",
        "6": "#F09300",
        "7": "#009688",
        "8": "#0B8043",
        "9": "#7CB342",
        "10": "#C0CA33",
        "11": "#E4C441",
        "12": "#F6BF26",
        "13": "#33B679",
        "14": "#039BE5",
        "15": "#4285F4",
        "16": "#3F51B5",
        "17": "#7986CB",
        "18": "#B39DDB",
        "19": "#616161",
        "20": "#A79B8E",
        "21": "#AD1457",
        "22": "#D81B60",
        "23": "#8E24AA",
        "24": "#9E69AF",
    }

    classic_colors = {}
    colors = get_colors(session.get("user"))
    for color in colors["calendar"]:
        classic_colors[color] = colors["calendar"][color]["background"].upper()

    # If color is a custom color
    if (background_color.upper() not in MODERN_COLORS.values()) and (background_color.upper() not in classic_colors.values()):
        return background_color
    
    return MODERN_COLORS[id]

def manage_session_login():
    if "user" in session:
        if "error" in get_calendars(session.get("user")):
            session.pop("user", None)
            return 1
        
    if "user" not in session:
        return 2
    
    return 0