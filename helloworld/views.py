# -*- coding: utf-8 -*-
from django.http import HttpResponse
import requests
import re
import json


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
        i1 = a.index('"QUERY')
        i2 = a.index('}]}",')+3
        a = "{"+a[i1:i2]
        a=a.replace('\\"',"\"")
        # print a
        a = json.loads(a)
        course = {}
        for data in a['QUERY']['DATA']:
          course[data[7]] = { #Lecture Discussion
            'begin_time': data[2],
            'end_time': data[3],
            'week_days': data[16]
          }
        courses[crn] = course



    retString = json.dumps(courses)

    return HttpResponse(retString)
