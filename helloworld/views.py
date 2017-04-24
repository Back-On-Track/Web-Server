# -*- coding: utf-8 -*-
from django.http import HttpResponse
import requests
import re
import json

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

def index(request):
    s = requests.Session()
    username = request.GET.get('username')
    password = request.GET.get('password')
    termCode = '201703'

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
    courses = {}
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

        #############################

        b = get_first_query(a)
        data_list = b['QUERY']['DATA']
        course = {}
        for data in data_list:
          course[data[7]] = { #Lecture Discussion
            'begin_time': data[2],
            'end_time': data[3],
            'week_days': data[16]
          }
        courses[crn] = course
        #############################

        b = get_main_data(a)
        course["identifier"] = b['Results']['DATA'][0][3]
        course["title"] = b['Results']['DATA'][0][24]
        course["units"] = b['Results']['DATA'][0][7]
        #############################

        b = get_second_query(a)
        course["instructor"] = b['QUERY']['DATA'][0][1]+' '+b['QUERY']['DATA'][0][2]
        #############################




    retString = json.dumps(courses)

    return HttpResponse(retString)