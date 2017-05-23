# -*- coding: utf-8 -*-

from django.conf.urls import patterns

urlpatterns = patterns('',
    (r'^getchart', 'backontrack.views.getchart'),
    (r'^export_data', 'backontrack.views.export_data'),
    (r'^export_for_chart', 'backontrack.views.export_for_chart'),
    (r'^get_schedule', 'backontrack.views.get_schedule'),
    (r'', 'backontrack.views.index'),
)
