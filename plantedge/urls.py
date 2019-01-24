from django.conf.urls import url

from django.views.generic import TemplateView

from plantedge import views
from plantedge.facade.analysis import start_analysis_cron

from django.conf.urls import include, url

from plantedge.facade.vegetationIndex import update_subscriber
from plantedge.facade.weeklyEmailCron import send_email_cron

urlpatterns = [

    # url(r'^createPlot/$', name='create_plot'),
    # url(r'createPlot', views.createPlot),

    url(r'createPlot', views.plotToAois),
    url(r'^chaining/', include('smart_selects.urls')),

    # url(r'update_subscriber', update_subscriber),



    url(r'send_email_cron', send_email_cron, name='create_plot'),

]