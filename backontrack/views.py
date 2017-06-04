# -*- coding: utf-8 -*-
from django.http import HttpResponse
from datetime import datetime, timedelta
import calendar
import tinyurl
import jinja2
import os
import requests
import re
import json
import random
import string
from charting import get_charts_data
from database_helpers import get_users_collection

DATE_FORMAT = "%B, %d %Y %H:%M:%S"

########### helper functions for get_schedule
def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start+len(needle))
        n -= 1
    return start

def get_first_query(json_string):
    i1 = json_string.index('"QUERY')
    i2 = json_string.index('}]}",')+3
    b = "{"+json_string[i1:i2]
    b=b.replace('\\"',"\"")

    return json.loads(b)

def get_second_query(json_string):
    i1 = find_nth(json_string,'"QUERY',3)
    i2 = find_nth(json_string,'}]}",',2)+3
    b = "{"+json_string[i1:i2]
    b = b.replace('\\"',"\"")

    return json.loads(b)

def get_main_data(json_string):
    b = json_string[:json_string.find(',"{\\"QUERY')]+"]]}}"
    return json.loads(b)

def add_hours_to_date(dateString, hours):
    date = datetime.strptime(dateString, DATE_FORMAT)
    dateOffsetted = date + timedelta(hours=hours)
    return datetime.strftime(dateOffsetted, DATE_FORMAT)

def get_hours_and_minutes_from_date(dateString):
    date = datetime.strptime(dateString, DATE_FORMAT)
    return datetime.strftime(date,"%H%M")

def get_week_day_from_date(dateString):
    date = datetime.strptime(dateString, DATE_FORMAT).date()
    day_name = calendar.day_name[date.weekday()]
    day_name_short_map = {
        "Monday": "M",
        "Tuesday": "T",
        "Wednesday": "W",
        "Thursday": "R",
        "Friday": "F",
        "Saturday": "S",
        "Sunday": "Su"
    }
    return day_name_short_map[day_name]
#############

# function for rendering jinja2 templates
def render(tpl_path, context):
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(context)

def render_charts(courses):
    ALL_DURATIONSTUDIED_TYPES, LINECHART_DATA, BARCHART_DATA = get_charts_data(courses)

    context = {
        'ALL_DURATIONSTUDIED_TYPES': ALL_DURATIONSTUDIED_TYPES,
        "LINECHART_DATA": json.dumps(LINECHART_DATA),
        "BARCHART_DATA": json.dumps(BARCHART_DATA)
    }

    html_page = render(os.path.join(os.path.dirname(__file__), 'chart.j2'), context)

    return html_page

def render_charts_for_aggregate(courses):
    ALL_DURATIONSTUDIED_TYPES, LINECHART_DATA, BARCHART_DATA = get_charts_data(courses)
    
    beg_of_quarter = datetime.strptime("April, 1 2017 00:00:00", DATE_FORMAT).date()
    LINECHART_DATA_INDEXED = []
    for elem in LINECHART_DATA:
        elemdate = datetime.strptime(elem['date'],'%m-%d-%Y').date()
        print (elemdate - beg_of_quarter).days
        LINECHART_DATA_INDEXED.append({
            'index': (elemdate - beg_of_quarter).days,
            'value': elem['value']
        })


    BARCHART_DATA_INDEXED = []
    for elem in BARCHART_DATA:
        print 'hiiii'
        print elem['date']
        elemdate = datetime.strptime(elem['date'],'%m-%d-%Y').date()
        print elemdate
        print (elemdate - beg_of_quarter).days
        BARCHART_DATA_INDEXED.append({
            'index': (elemdate - beg_of_quarter).days,
            'categories': elem['categories']
        })

    context = {
        'ALL_DURATIONSTUDIED_TYPES': ALL_DURATIONSTUDIED_TYPES,
        "LINECHART_DATA": json.dumps(LINECHART_DATA_INDEXED),
        "BARCHART_DATA": json.dumps(BARCHART_DATA_INDEXED)
    }

    html_page = render(os.path.join(os.path.dirname(__file__), 'chart_for_aggregate.j2'), context)

    return html_page


def render_charts_to_file(courses):
    html_page = render_charts(courses)

    N=10
    filename = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(N))
    with open(os.path.join(os.path.dirname(__file__), '..', 'static', filename+'.html'), 'w') as f:
        f.write(html_page)

    return filename

###############################################################
#########################START ROUTES##########################

# route for getting schedule with all classes for the current quarter
def get_schedule(request):
    s = requests.Session()
    username = json.loads(request.body)['username']
    password = json.loads(request.body)['password']

    termCode = '201703'
    termName = 'Spring 2017'

    params = (
        ('service', 'https://my.ucdavis.edu/schedulebuilder/index.cfm?sb'),
    )

    search = 'name="execution" value="'
    x = s.get('https://cas.ucdavis.edu/cas/login', params=params).text
    x = x[len(search)+x.find(search):]
    execution = x[:x.find('"')]

    ######################



    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    data = [
      ('username', username),
      ('password', password),
      ('execution', execution),
      ('_eventId', 'submit'),
      ('submit', 'LOGIN'),
    ]

    s.post('https://cas.ucdavis.edu/cas/login?service=https%3A%2F%2Fmy%2Eucdavis%2Eedu%2Fschedulebuilder%2Findex%2Ecfm%3Fsb',
            headers=headers,
            data=data,
            allow_redirects=True)


    a = s.get('https://my.ucdavis.edu/schedulebuilder/index.cfm?termCode='+termCode+'&helpTour=', allow_redirects=True)
    a = a.text

    crns = []
    for index in [m.start() for m in re.finditer('CourseDetails.t[0-9]+.REGISTRATION_STATUS = "Registered"', a)]:
      line = a[index:a.index('\n',index)]
      crns.append(line[line.index('.t')+2:line.index('.R')])
    print crns
    #CourseDetails.t69943.REGISTRATION_STATUS = "Registered";
    courses = {
        "courses": {},
        "quarter": {}
    }
    
    quarter_start_date = datetime.strptime("January, 1 2050 00:00:00", DATE_FORMAT).date()

    quarter_end_date = datetime.strptime("January, 1 1990 00:00:00", DATE_FORMAT).date()
    for crn in crns:
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }

        data = [
          ('sortBy', ''),
          ('showMe', ''),
          ('runMe', '1'),
          ('clearMe', '1'),
          ('termCode', termCode),
          ('expandFilters', ''),
          ('course_number', crn),
        ]

        a = s.post('https://my.ucdavis.edu/schedulebuilder/course_search/course_search_results.cfm', headers=headers, data=data)
        a = a.text
        # print "a=", a
        #############################

        b = get_first_query(a)
        data_list = b['QUERY']['DATA']
        course = {'classes': {}}
        for data in data_list:
            course['classes'][data[7]] = { #Lecture Discussion
                'begin_time': data[2],
                'end_time': data[3],
                'start_date': data[4],
                'end_date': data[5],
                'week_days': data[16]
            }
            current_start_date = datetime.strptime(course['classes'][data[7]]['start_date'], DATE_FORMAT).date()
            if current_start_date < quarter_start_date:
                quarter_start_date = current_start_date

            current_end_date = datetime.strptime(course['classes'][data[7]]['end_date'], DATE_FORMAT).date()
            if current_end_date > quarter_end_date:
                quarter_end_date = current_end_date
        # end for
        courses["courses"][crn] = course
        #############################

        b = get_main_data(a)
        course["identifier"] = b['Results']['DATA'][0][22] + ' ' + b['Results']['DATA'][0][3] # e.g: ECS + ' ' + 175

        final_start_date = b['Results']['DATA'][0][11]
        if final_start_date is not None:
            final_end_date = add_hours_to_date(final_start_date, 2)
            course['final'] = {
                'start_date': final_start_date,
                'end_date': final_end_date,
                'begin_time': get_hours_and_minutes_from_date(final_start_date),
                'end_time': get_hours_and_minutes_from_date(final_end_date),
                'week_days': get_week_day_from_date(final_start_date)
            }
            

        course["title"] = b['Results']['DATA'][0][24]
        course["units"] = b['Results']['DATA'][0][7]
        #############################

        b = get_second_query(a)
        course["instructor"] = b['QUERY']['DATA'][0][1]+' '+b['QUERY']['DATA'][0][2]
        #############################

        if course.has_key("final"):
            current_final_date = datetime.strptime(course["final"]["end_date"], DATE_FORMAT).date()
            if current_final_date > quarter_end_date:
                quarter_end_date = current_final_date

            course['classes']['Final'] = course['final']
            course.pop('final', None)
    # end for crn in crns

    courses['quarter'] = {
        'title': termName,
        'start_date': datetime.strftime(quarter_start_date, DATE_FORMAT),
        'end_date': datetime.strftime(quarter_end_date, DATE_FORMAT)
    }
    retString = json.dumps(courses)
    return HttpResponse(retString)

# route for exporting data to database
def export_data(request):
    collection = get_users_collection()

    UID = request.GET.get('UID')

    courses = []
    quarters = json.loads(request.body)["quarters"]

    for quarter in quarters:
        courses += quarter["courses"]

    userData = {
        "UID": UID,
        "courses": courses
    }
    
    collection.update({"UID": UID}, userData, upsert=True)
    return HttpResponse({"success": True})


# route for exporting data and saving it as an html file with the charts
def export_for_chart(request):
    quarters = json.loads(request.body)["quarters"]
    the_quarter = None
    for quarter in quarters:
        if quarter["current"]:
            the_quarter = quarter
            break

    courses = the_quarter['courses']
    filename = render_charts_to_file(courses)
    response = {
        'url': tinyurl.create_one('https://ibackontrack.com/static/'+filename+'.html')
    }
    return HttpResponse(json.dumps(response))


def get_avg_of_all_events_array_for_course(course_identifier):
    collection = get_users_collection()
    sum_of_all_events_dict = {}
    users_cursor = collection.find({'courses': {'$elemMatch': {'identifier': course_identifier}}})
    length = users_cursor.count()
    for user in users_cursor:
        user_courses = user["courses"]
        for course in user_courses:
            if course["identifier"] != course_identifier: continue

            for event in course["events"]:
                if sum_of_all_events_dict.has_key(event["date"]):
                    sum_of_all_events_dict[event["date"]]["durationStudied"] += event["durationStudied"]
                    sum_of_all_events_dict[event["date"]]["duration"] += event["duration"]
                else:
                    sum_of_all_events_dict[event["date"]] = event.copy()


    avg_of_all_events_array = []
    ## divide by length
    for date in sum_of_all_events_dict.keys():
        avg_of_all_events_array.append(sum_of_all_events_dict[date])
        avg_of_all_events_array[-1]["duration"] /= length
        avg_of_all_events_array[-1]["durationStudied"] /= length

    return avg_of_all_events_array

def course_charts(request):
    course_identifier = request.GET.get('identifier')
    avg_of_all_events_array = get_avg_of_all_events_array_for_course(course_identifier)
    html_page = render_charts_for_aggregate([{"events": avg_of_all_events_array}]) # 1 course object

    return HttpResponse(html_page)

def index(request):
    collection = get_users_collection()
    users_cursor = collection.find({})

    all_identifiers = {}
    for user in users_cursor:
        for course in user["courses"]:
            all_identifiers[course["identifier"]] = True

    # filter out the courses that dont have any events
    nonEmptyCourseIdentifiers = []
    for course_identifier in all_identifiers.keys():
        avg_of_all_events_array = get_avg_of_all_events_array_for_course(course_identifier)
        totalDurationStudied = sum([x["durationStudied"] for x in avg_of_all_events_array])
        nonEmptyCourseIdentifiers += [course_identifier] if totalDurationStudied != 0 else []

    context = {
        'IDENTIFIERS': nonEmptyCourseIdentifiers,
    }

    html_page = render(os.path.join(os.path.dirname(__file__), 'courses.j2'), context)

    return HttpResponse(html_page)