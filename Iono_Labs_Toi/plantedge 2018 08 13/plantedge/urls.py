from django.conf.urls import url

from django.views.generic import TemplateView

from plantedge import views



urlpatterns = [

    # url(r'^createPlot/$', name='create_plot'),
    # url(r'createPlot', views.createPlot),

    url(r'createPlot', views.plotToAois),
    # url(r'createPlots', createPlot, name='create_plot'),

]