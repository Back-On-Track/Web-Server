# -*- coding: utf-8 -*-

from django.conf.urls import patterns

urlpatterns = patterns('',
    (r'^get_chart', 'backontrack.views.get_chart'),
    (r'^export_data', 'backontrack.views.export_data'),
    (r'^export_for_chart', 'backontrack.views.export_for_chart'),
    (r'^get_schedule', 'backontrack.views.get_schedule'),
    (r'^course_charts', 'backontrack.views.course_charts'),
    (r'', 'backontrack.views.index'),
)
