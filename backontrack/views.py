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
import datetime
from pymongo import MongoClient


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
    ################################################################################################################################################



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


# function for rendering jinja2 templates
def render(tpl_path, context):
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(context)

# route for retrieving charts, simply reads html files and serves it
def get_chart(request):
    filename = request.GET.get('filename')
    filename = 'helloworld/'+filename+'.html'
    print 'filename='+filename
    data = None
    with open(filename, 'r') as myfile:
        data=myfile.read().replace('\n', '')
    return HttpResponse(data)

# route for exporting data to database
def export_data(request):
    client = MongoClient('mongodb://backontrack:1234567890aA@ds149481.mlab.com:49481/backontrack')
    db = client.backontrack
    collection = db.all_users
    UID = request.GET.get('UID')
    userData = {
        "UID": UID,
        "data": json.loads(request.body)
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

    ################################
    ################################
    ################################
    ##########BEGIN PIE CHART#######
    STUDY, HOMEWORK, PROJECT, LAB, OTHER = 0, 0, 0, 0, 0
    for course in courses:
        events = course["events"]
        for event in events:
            if event["type"] == 0: STUDY += event["durationStudied"]
            if event["type"] == 1: HOMEWORK += event["durationStudied"]
            if event["type"] == 2: PROJECT += event["durationStudied"]
            if event["type"] == 3: LAB += event["durationStudied"]
            if event["type"] == 4: OTHER += event["durationStudied"]
    print "FINISH PIE CHART"
    ##########FINISH PIE CHART######
    ################################
    ################################
    ################################
    


    ################################
    ################################
    ################################
    ############BEGIN LINE CHART####
    print "BEGIN LINE CHART"

    # get all course events dates
    allevents = {} # date: durationStudied
    for course in courses:
        for event in course["events"]:
            if event["type"] <= 4:
                if allevents.has_key(event["date"]):
                    value = allevents[event["date"]]
                    allevents[event["date"]] = (value[0] + event["durationStudied"], value[1] + event["duration"])
                else:
                    allevents[event["date"]] = (event["durationStudied"], event["duration"])
    sorteddatekeys = allevents.keys()
    if len(sorteddatekeys) == 0:
        LINECHART_DATA = []
    else:
        sorteddatekeys.sort(key=lambda x: datetime.datetime.strptime(x, '%m-%d-%Y'))

        #loop from min to max key and consolidate duplicates
        mindate = datetime.datetime.strptime(sorteddatekeys[0], '%m-%d-%Y')
        maxdate = datetime.datetime.strptime(sorteddatekeys[-1], '%m-%d-%Y')
        day_count = (maxdate - mindate).days + 1
        for single_date in (mindate + datetime.timedelta(n) for n in range(day_count)):
            datestr = single_date.strftime("%m-%d-%Y")
            if not allevents.has_key(datestr):
                allevents[datestr] = (0, 0)

        #4- convert dictionary to array in sorted order
        sorteddatekeys = allevents.keys() # no duplicates now
        sorteddatekeys.sort(key=lambda x: datetime.datetime.strptime(x, '%m-%d-%Y'))
        LINECHART_DATA = []
        for date in sorteddatekeys:
            value = allevents[date][0]
            LINECHART_DATA.append({
                'date': date,
                'value': value
            })
    
    print "FINISH LINE CHART"
    ##########FINISH LINE CHART#####
    ################################
    ################################
    ################################

    ################################
    ################################
    ################################
    ############BEGIN BAR CHART#####

    

    BARCHART_DATA = []
    if len(sorteddatekeys) == 0:
        BARCHART_DATA = []
    else:
        for date in sorteddatekeys:
            studied = allevents[date][0]
            planned = allevents[date][1]
            # { Date: "2016-06-14", Categories: [{ Name: "Planned", Value: 321 }, { Name: "Studied", Value: 524 }] }
            BARCHART_DATA.append({ 
                'Date': date[:date.rfind('-')],
                'Categories': [
                    {'Name': 'Planned', 'Value': planned},
                    {'Name': 'Studied', 'Value': studied},
                ]
            })

    ################################
    ################################
    ################################

    ##########RENDER
    context = {
        "STUDY": STUDY,
        "HOMEWORK": HOMEWORK,
        "PROJECT": PROJECT,
        "LAB": LAB,
        "OTHER": OTHER,

        "LINECHART_DATA": json.dumps(LINECHART_DATA),

        "BARCHART_DATA": json.dumps(BARCHART_DATA)
    }

    result = render(os.path.join(os.path.dirname(__file__), 'chart.j2'), context)


    N=10
    filename = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(N))
    with open(os.path.join(os.path.dirname(__file__), filename+'.html'), 'w') as f:
        f.write(result)

    response = json.dumps({
        'url': tinyurl.create_one('http://192.241.206.161/getchart?filename='+filename)
    })
    print 'DONE FUNCTION, response='+response
    return HttpResponse(response)