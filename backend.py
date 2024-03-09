from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Response,
    Query,
    Form,
    File,
    UploadFile,
    Depends
)
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import pytz
import os
import logging
from typing import List
import requests
import pandas as pd
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
# from log import get_logger
import json
from uuid import uuid4
from datetime import datetime as dtime
import random

app = FastAPI()
# cange to your desired location
home_path = "~/moodmap-backend"

# Allow requests from all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

with open(f"{home_path}/time_mapping.json", "r") as f:
    TIME_MAPPING = json.load(f)
        
DAY_MAPPING = {"M": "monday", "T": "tuesday", "W": "wednesday", "R": "thursday", "F": "friday"}

with open(f"{home_path}/202302.json", "r") as f:
    DATA = json.load(f)

class UserRegisterRequest(BaseModel):
    username: str
    age: int
    email: str
    current_degree: str
    major: str
    institute: str


class StudyData(BaseModel):
    username: str
    class_code: str
    
    
class DailyDetailsRequest(BaseModel):
    username: str
    bullying: int
    depression: int
    relationship: int
    sleep_quality: int
    social_support: int

@app.get("/")
def read_root(request: Request):
    return "Hello"


def get_class_timings(data, courses, time_mapping, day_mapping):
    class_mapping = []
    for course_id in courses:
        course_parts = course_id.split(" ")
        url = f"https://c4citk6s9k.execute-api.us-east-1.amazonaws.com/test/data/course?courseID={course_parts[0].lower()}%20{course_parts[1]}"
        response = requests.get(url)

        avg_gpa = response.json()['raw'][0]['GPA']

        ls = data['courses'][course_id][1]['A'][1][0]
        start, end = time_mapping[str(ls[0])].split("-")

        start = start.strip()
        end = end.strip()


        days = ls[1]

        for d in days:
            class_mapping.append({"day": day_mapping[d], "start": start, "end": end, "schedule_name": course_id, "comments": f"Average GPA of this class is {avg_gpa}"})
        
    return class_mapping
    
    
@app.get("/all_classes/")
def get_class_schedule(classes: str):
    classes = classes.upper().replace("-", " ")
    class_schedule = get_class_timings(DATA, classes.split(","), TIME_MAPPING, DAY_MAPPING)
    # schedule_html = schedule_df.to_html(index=False)
    return class_schedule


# def create_schedule_dataframe(data):
#     # Create a list of all 30-minute intervals for the entire week
#     start_time = datetime.strptime('12:00 AM', '%I:%M %p')
#     end_time = datetime.strptime('11:59 PM', '%I:%M %p')
#     time_interval = timedelta(minutes=30)
#     time_slots = []
#     current_time = start_time
#     while current_time <= end_time:
#         time_slots.append(current_time.strftime('%I:%M %p'))
#         current_time += time_interval

#     # Create an empty DataFrame
#     days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
#     schedule_df = pd.DataFrame(index=time_slots, columns=days_of_week)

#     # Fill in the DataFrame with course schedule
#     for course in data:
#         day = course['day'].capitalize()
#         start_time = datetime.strptime(course['start'], '%I:%M %p')
#         end_time = datetime.strptime(course['end'], '%I:%M %p')

#         # Adjust start time to 1:30 PM if necessary
#         if start_time.minute != 0 and start_time.minute != 30:
#             start_time = start_time.replace(hour=start_time.hour, minute=30)
#         elif start_time.minute == 0:
#             start_time = start_time.replace(minute=30)

#         # Adjust end time to 2:00 PM if necessary
#         if end_time.minute != 0 and end_time.minute != 30:
#             end_time = end_time.replace(hour=end_time.hour + 1, minute=0)
#         elif end_time.minute == 30:
#             end_time = end_time.replace(hour=end_time.hour + 1, minute=0)

#         # Convert adjusted times back to string format
#         start_time_str = start_time.strftime('%I:%M %p')
#         end_time_str = end_time.strftime('%I:%M %p')

#         course_id = course['schedule_name']

#         # Calculate row indices for the start and end times
#         start_index = time_slots.index(start_time_str)
#         end_index = time_slots.index(end_time_str)

#         # Fill in the schedule for the course
#         for i in range(start_index, end_index):
#             schedule_df.loc[time_slots[i], day] = course_id

#     return schedule_df


@app.get("/all_classes/")
def get_class_schedule(classes: str):
    classes = classes.upper().replace("-", " ")
    class_schedule = get_class_timings(DATA, classes.split(","), TIME_MAPPING, DAY_MAPPING)
    # schedule_html = schedule_df.to_html(index=False)
    return class_schedule

def add_sleep(data, comment=""):
    for d in DAY_MAPPING.values():
        data.append({"day": d, "start": "12:00 am", "end": "8:00 am", "schedule_name": "sleep", "comments": comment})
    return data


def save_db(db, name):
    count = len(os.listdir(name)) + 1
    db.to_parquet(f"{name}/{count}.parquet")
    
    
@app.post("/user_register/")
def user_register(user_data: UserRegisterRequest):
    user_db = pd.DataFrame(columns=['username', 'age', 'email', 'current_degree', 'major', 'institute'])
    user_db.loc[0, :] = user_data.dict()
    save_db(user_db, "user")
    return {"username": user_data.dict()['username']}



@app.post("/add_data/")
def add_data(data: DailyDetailsRequest):
    # Append data to daily_details_db
    daily_details_db = pd.DataFrame(columns=['username', 'sleep_quality', 'bullying', 'depression', 'relationship', 'social_support'])
    daily_details_db.loc[0, :] = data.dict()
    # Append data to Parquet file
    save_db(daily_details_db, "details")
    return {"message": "Data added successfully"}


@app.get("/user_data/")
def get_user_data():
    user_db = pd.read_parquet("user")
    return user_db.to_dict(orient="records")

@app.get("/details_data/")
def get_daily_details_data():
    daily_details_db = pd.read_parquet("details")
    return daily_details_db.to_dict(orient="records")


@app.post("/store_class_info")
def get_class_info(data: StudyData):
    class_db = pd.DataFrame(columns=['username', 'class_code'])
    
    class_db.loc[0, :] = data.dict()
    save_db(class_db, "class_data")
    return {"message": "Data added successfully"}

def get_class_details_data(username):
    try:
        daily_details_db = pd.read_parquet("class_data")
        all_classes = daily_details_db[daily_details_db["username"] == username]["class_code"].tolist()
        return all_classes
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Data file not found")
    except KeyError:
        raise HTTPException(status_code=500, detail="Invalid data format or missing columns")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/class_data/{name}")
def read_class_details_data(name: str):
    # uuid = get_uuid_from_uname(name)
    class_details = get_class_details_data(name)
    if class_details:
        return class_details
    else:
        raise HTTPException(status_code=404, detail="Username not found")

# @app.get("/display_classes/")
# def get_class_schedule(uuid):
#     all_classes = get_class_details_data(uuid)
#     data = get_class_timings(DATA, all_classes, TIME_MAPPING, DAY_MAPPING)
#     data = add_sleep(data)
#     df = create_schedule_dataframe(data).astype("str")
#     return df

# def generate_html_calendar(data):
#     days = list(data.keys())
#     timeslots = list(data[days[0]].keys())

#     # Open the HTML document
#     html_output = "<!DOCTYPE html>\n<html>\n<head>\n<title>Weekly Calendar</title>\n"
#     html_output += "<style>table {border-collapse: collapse;} th, td {border: 1px solid black; padding: 8px;}</style>\n"
#     html_output += "</head>\n<body>\n"
#     html_output += "<table>\n"

#     # Table header
#     html_output += "<tr>\n<th>Time</th>\n"
#     for day in days:
#         html_output += f"<th>{day}</th>\n"
#     html_output += "</tr>\n"

#     # Table data
#     for timeslot in timeslots:
#         html_output += "<tr>\n"
#         html_output += f"<td>{timeslot}</td>\n"
#         for day in days:
#             activity = data[day][timeslot]
#             html_output += f"<td>{activity}</td>\n"
#         html_output += "</tr>\n"

#     # Close the HTML document
#     html_output += "</table>\n</body>\n</html>"

#     return html_output




# def get_uuid_from_uname(uname):
#     user_db = pd.read_parquet("user")
#     uuids = user_db[user_db.name == uname]["uuid"].tolist()
#     print(uuids)
#     if uuids:
#         return uuids[0]
#     else:
#         return None

# @app.get("/display_classes/{name}", response_class=HTMLResponse)
# def render_calendar(response: Response, name: str):
#     # uuid = get_uuid_from_uname(name)
#     all_classes = get_class_details_data(name)
#     data = get_class_timings(DATA, all_classes, TIME_MAPPING, DAY_MAPPING)
#     data = add_sleep(data)
#     df = create_schedule_dataframe(data)
    
    
    
#     html_content = generate_html_calendar(df.to_dict())
#     return HTMLResponse(content=html_content)



def create_prompt(user):
    all_classes = read_class_details_data(user)
    all_engagements = get_class_timings(DATA, all_classes, TIME_MAPPING, DAY_MAPPING)
    todays_engagement = []
    # print(all_engagements)
    
    utc_now = dtime.utcnow()
    ny_timezone = pytz.timezone('America/New_York')
    ny_time = utc_now.replace(tzinfo=pytz.utc).astimezone(ny_timezone)

    for eng in all_engagements:
        
        if eng['day'].lower() == ny_time.strftime("%A").lower():
            del eng['day']
            todays_engagement.append(eng)
            
    daily_details_db = pd.read_parquet("details")
    status = daily_details_db[daily_details_db.username == user].iloc[-1].to_dict()
    
    mapper = {0: "poor", 1: "ok", 2: "great"}
    
    # stress_level = "high" # add a predictive model
    # I am feeling {stress_level} stress today day,
    sleep_quality = mapper[status['sleep_quality']]
    depression = mapper[status['depression']]
    social_support = mapper[status['social_support']]
    hobby = random.choice(['Reading', 'doodling', 'Gardening', 'Photography ', 'Hiking', 'walking in nature', 'Crafting', 'Playing board games ', 'card games', 'hanging out with friends', 'Listening to music ', 'listening to podcasts', 'Yoga', 'meditation'])
    
    # all_engagements = add_sleep(all_engagements, comment)
    prompt = f'''
    generate a time schedule for today based on below information, If today is a week end then plan some thing fun based on my mood
    I current time is {ny_time}, below are the things I have to do today, 
    {todays_engagement}
    I had {sleep_quality} last night
    
    My mentatl state is {depression},
    People trat me very {social_support}
    my hobby is {hobby} that helps me relax
    make a tabular with below shcema schedule from right with 30 mins breakdown which time I am supposed to do what
    Time|Activity|Comments
    <row1 time>|<row1 acitivty>|<row 1 comments>
    
    '''.strip()
   
    
    return prompt
    
def filter_result(generated_text):
    lines = generated_text.strip().split("\n")
    schedule_lines = [l.strip("|").split("|") for l in lines[2:]]
    schedule_df = pd.DataFrame(schedule_lines, columns=["Time", "Task", "Comments"])
    return schedule_df


def generate(user: str):
    api_key = "" # insert your api here from google gemini
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {
                "parts": [
                    {"text": create_prompt(user)}
                ]
            }
        ]
    }
     # Send POST request
    response = requests.post(url, headers=headers, data=json.dumps(data))

    # Check for successful response (status code 200)
    if response.status_code == 200:

        response_json = response.json()

        generated_text = response_json["candidates"][0]["content"]["parts"][0]["text"]

        return generated_text

    else:
        print(f"Error: {response.status_code}")

@app.get("/get_schedule/{name}")
def get_schedule(name: str):
    schedule_raw = generate(name)
    df = filter_result(schedule_raw)
    return df


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="164.52.210.166", port=8809)
    
    
    

