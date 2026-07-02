import random
import numpy as np
from scipy.stats import norm
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

app = FastAPI()

# Timezone configuration
TARGET_TIMEZONES = {
    "Tehran": "Asia/Tehran",
    "Baghdad": "Asia/Baghdad",
    "Riyadh": "Asia/Riyadh",
    "Jerusalem": "Asia/Jerusalem",
    "New York": "America/New_York",
    "Gaza": "Asia/Gaza",
}

SERVER_TIMEZONE = ZoneInfo("Asia/Tehran")

INTENSITY_LIMITS = {
    1: {"Like": (0, 30), "Comment": (0, 10), "Tweet": (0, 10),
        "Follow": (0, 10), "Retweet": (0, 20), "View": (0, 40), "quote": (0, 15)},

    2: {"Like": (40, 100), "Comment": (12, 30), "Tweet": (15, 35),
        "Follow": (20 , 60), "Retweet": (30, 60), "View": (60, 110), "quote": (20, 40)},

    3: {"Like": (110, 150),         
        "Comment": (40 , 70),      
        "Tweet": (35 , 60),        
        "Follow": (60 , 80),       
        "Retweet": (70, 90),       
        "View": (120, 200),         
        "quote": (45, 80)        
       }
}

ACTIVITIES = ["Like", "Comment", "Tweet", "Follow", "Retweet", "View", "quote"]

def generate_time_distribution(target_tz_str):
    utc_zone = ZoneInfo("UTC")
    target_zone = ZoneInfo(target_tz_str)
    base_date = datetime.now(tz=utc_zone).replace(hour=0, minute=0, second=0, microsecond=0)

    time_slots_target = []
    time_slots_server = []
    local_hours = []

    for minute_offset in range(24 * 60):
        utc_dt = base_date + timedelta(minutes=minute_offset)
        target_dt = utc_dt.astimezone(target_zone)
        server_dt = utc_dt.astimezone(SERVER_TIMEZONE)

        time_slots_target.append(target_dt.strftime("%H:%M"))
        time_slots_server.append(server_dt.strftime("%H:%M"))
        local_hours.append(target_dt.hour + target_dt.minute / 60)

    probabilities = np.zeros(len(time_slots_target))

    peak_a = norm(loc=21.5, scale=1.9)
    peak_b = norm(loc=12.5, scale=1.3)
    peak_c = norm(loc=9.0, scale=0.5)
    weight_a, weight_b, weight_c = 0.59, 0.3, 0.08

    peak_d = norm(loc=0.5, scale=1)
    weight_d = 0.03

    for i, hour in enumerate(local_hours):
        prob = (weight_a * peak_a.pdf(hour) + weight_b * peak_b.pdf(hour) + weight_c * peak_c.pdf(hour)
                + weight_d * peak_d.pdf(hour))
        if 2 <= hour < 6.5:
            prob *= 0.3
        probabilities[i] = prob

    probabilities /= np.sum(probabilities)
    return time_slots_server, probabilities

def select_times(n, time_slots, probabilities):
    if n == 0:
        return ["No action predicted"]
    return sorted(random.choices(time_slots, weights=probabilities, k=n))

def get_weekday_restrictions(location, current_date):
    # تعیین روز تعطیل و دو روز اول کاری هفته بر اساس موقعیت مکانی
    # بازگرداندن دیکشنری محدودیت‌ها

    if location == "Tehran":
        weekend_day = 4  # جمعه (Python: دوشنبه=0، پس جمعه=4)
        first_work_days = [5, 6]  # شنبه=5، یکشنبه=6
    elif location in ["Baghdad", "Riyadh"]:
        weekend_day = 5  # شنبه
        first_work_days = [6, 0]  # یکشنبه، دوشنبه
    else:
        weekend_day = 6
        first_work_days = [0, 1]

    weekday = current_date.weekday()

    restrictions = {
        "no_intensity_3": False,
        "no_intensity_1": False
    }

    if weekday == weekend_day:
        restrictions["no_intensity_1"] = True

    if weekday in first_work_days:
        restrictions["no_intensity_3"] = True

    return restrictions

def generate_daily_schedule(location, intensity_mode, **kwargs):
    tz_str = TARGET_TIMEZONES.get(location)
    if not tz_str:
        raise ValueError("Invalid location")

    target_zone = ZoneInfo(tz_str)
    current_date = datetime.now(tz=target_zone).date()

    restrictions = get_weekday_restrictions(location, current_date)

    # اعمال محدودیت‌ها بر اساس روز هفته
    if intensity_mode == 3 and restrictions["no_intensity_3"]:
        raise ValueError(f"Intensity mode 3 is not allowed on this day for location {location}")
    if intensity_mode == 1 and restrictions["no_intensity_1"]:
        raise ValueError(f"Intensity mode 1 is not allowed on this day for location {location}")

    time_slots_server, probabilities = generate_time_distribution(tz_str)
    result = {}

    if intensity_mode == 4:
        for activity in ACTIVITIES:
            interval_str = kwargs.get(f"{activity.lower()}_interval")
            try:
                count = int(interval_str)
            except (ValueError, TypeError):
                count = 0

            times = select_times(count, time_slots_server, probabilities) if count > 0 else ["No action predicted"]
            result[activity] = {"count": count, "times": times}
    else:
        limits = INTENSITY_LIMITS[intensity_mode]
        for activity in ACTIVITIES:
            low, high = limits[activity]
            count = random.randint(low, high)
            times = select_times(count, time_slots_server, probabilities)
            result[activity] = {"count": count, "times": times}

    return result

@app.get("/get_output_schedule")
def get_schedule(
    location: str = Query(...),
    intensity_mode: int = Query(...),
    like_interval: str = Query(None),
    comment_interval: str = Query(None),
    tweet_interval: str = Query(None),
    follow_interval: str = Query(None),
    retweet_interval: str = Query(None),
    view_interval: str = Query(None),
    quote_interval: str = Query(None),
):
    try:
        data = generate_daily_schedule(
            location,
            intensity_mode,
            like_interval=like_interval,
            comment_interval=comment_interval,
            tweet_interval=tweet_interval,
            follow_interval=follow_interval,
            retweet_interval=retweet_interval,
            view_interval=view_interval,
            quote_interval=quote_interval,
        )
        headers = {
            "content-length": str(len(json.dumps(data))),
            "content-type": "application/json",
            "date": datetime.now(ZoneInfo("GMT")).strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "server": "uvicorn"
        }
        return JSONResponse(content=data, headers=headers)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
