# -*- coding: utf-8 -*-
from django.http import HttpResponse
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

def render_charts_to_file(courses):
    html_page = render_charts(courses)

    N=10
    filename = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(N))
    with open(os.path.join(os.path.dirname(__file__), filename+'.html'), 'w') as f:
        f.write(html_page)

    return filename

###############################################################
#########################START ROUTES##########################

# route for getting schedule with all classes for the current quarter
def get_schedule(request):
    s = requests.Session()
    username = request.GET.get('username')
    password = request.GET.get('password')
    termCode = '201703'
    termName = 'Spring 2017'

    params = (
        ('service', 'https://my.ucdavis.edu/schedulebuilder/index.cfm?sb'),
    )

    a = s.get('https://cas.ucdavis.edu/cas/login', params=params)

    x = a.text
    search = 'name="execution" value="'
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
    
    start_date = ''
    end_date = ''
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
          start_date = data[4]
          end_date = data[5]
        courses["courses"][crn] = course
        #############################

        b = get_main_data(a)
        course["identifier"] = b['Results']['DATA'][0][22] + ' ' + b['Results']['DATA'][0][3] # e.g: ECS + ' ' + 175
        course["title"] = b['Results']['DATA'][0][24]
        course["units"] = b['Results']['DATA'][0][7]
        #############################

        b = get_second_query(a)
        course["instructor"] = b['QUERY']['DATA'][0][1]+' '+b['QUERY']['DATA'][0][2]
        #############################



    courses['quarter'] = {
        'title': termName,
        'start_date': start_date,
        'end_date': end_date
    }
    retString = json.dumps(courses)

    return HttpResponse(retString)

# route for retrieving charts, simply reads html files and serves it
def get_chart(request):
    filename = request.GET.get('filename')
    filename = os.path.join(os.path.dirname(__file__), filename+".html")

    data = None
    with open(filename, 'r') as myfile:
        data=myfile.read().replace('\n', '')
    return HttpResponse(data)

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
        'url': tinyurl.create_one('http://192.241.206.161/get_chart?filename='+filename)
    }
    return HttpResponse(json.dumps(response))

def course_charts(request):
    course_identifier = request.GET.get('identifier')

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

    ## create array
    
    html_page = render_charts([{"events": avg_of_all_events_array}]) # 1 course object

    return HttpResponse(html_page)

def index(request):
    collection = get_users_collection()
    users_cursor = collection.find({})

    all_identifiers = {}
    for user in users_cursor:
        for course in user["courses"]:
            all_identifiers[course["identifier"]] = True

    context = {
        'IDENTIFIERS': all_identifiers.keys(),
    }

    html_page = render(os.path.join(os.path.dirname(__file__), 'courses.j2'), context)

    return HttpResponse(html_page)