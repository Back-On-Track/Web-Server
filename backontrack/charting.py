import datetime

def get_charts_data(courses):
    ################################
    ##########BEGIN PIE CHART#######
    all_durationStudied_types = {
        'STUDY': 0,
        'HOMEWORK': 0,
        'PROJECT': 0,
        'LAB': 0,
        'OTHER': 0
    }
    for course in courses:
        for event in course["events"]:
            if event["type"] == 0: all_durationStudied_types['STUDY'] += event["durationStudied"]
            if event["type"] == 1: all_durationStudied_types['HOMEWORK'] += event["durationStudied"]
            if event["type"] == 2: all_durationStudied_types['PROJECT'] += event["durationStudied"]
            if event["type"] == 3: all_durationStudied_types['LAB'] += event["durationStudied"]
            if event["type"] == 4: all_durationStudied_types['OTHER'] += event["durationStudied"]
    ##########FINISH PIE CHART######
    ################################

    ################################
    ############BEGIN LINE CHART####
    # get all course events dates
    all_events = {} # date: durationStudied
    for course in courses:
        for event in course["events"]:
            if event["type"] <= 4:
                if all_events.has_key(event["date"]):
                    value = all_events[event["date"]]
                    all_events[event["date"]] = (value[0] + event["durationStudied"], value[1] + event["duration"])
                else:
                    all_events[event["date"]] = (event["durationStudied"], event["duration"])

    sorted_date_keys = all_events.keys()
    line_chart_data = []
    if len(all_events) != 0:
        sorted_date_keys.sort(key=lambda x: datetime.datetime.strptime(x, '%m-%d-%Y'))

        #loop from min to max key and consolidate duplicates
        mindate = datetime.datetime.strptime(sorted_date_keys[0], '%m-%d-%Y')
        maxdate = datetime.datetime.strptime(sorted_date_keys[-1], '%m-%d-%Y')
        day_count = (maxdate - mindate).days + 1
        for single_date in (mindate + datetime.timedelta(n) for n in range(day_count)):
            datestr = single_date.strftime("%m-%d-%Y")
            if not all_events.has_key(datestr):
                all_events[datestr] = (0, 0)

        #4- convert dictionary to array in sorted order
        sorted_date_keys = all_events.keys()
        sorted_date_keys.sort(key=lambda x: datetime.datetime.strptime(x, '%m-%d-%Y'))
        
        for date in sorted_date_keys:
            value = all_events[date][0]
            line_chart_data.append({
                'date': date,
                'value': value
            })
    
    ##########FINISH LINE CHART#####
    ################################
    ################################
    ############BEGIN BAR CHART#####

    bar_chart_data = []
    if len(sorted_date_keys) != 0:
        for date in sorted_date_keys:
            studied = all_events[date][0]
            planned = all_events[date][1]
            # { Date: "2016-06-14", Categories: [{ Name: "Planned", Value: 321 }, { Name: "Studied", Value: 524 }] }
            bar_chart_data.append({ 
                'Date': date[:date.rfind('-')],
                'Categories': [
                    {'Name': 'Planned', 'Value': planned},
                    {'Name': 'Studied', 'Value': studied},
                ]
            })
    ################################
    ################################
    ################################
    return all_durationStudied_types, line_chart_data, bar_chart_data