import os
import shutil
from django.contrib import admin
from easy_select2 import forms

from downloads3.models import Plot_S3_Links
from plantedge.core.gaia import Gaia
from .models import *
from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter

from easy_select2 import select2_modelform

from django import forms


# for login page
admin.site.site_header = 'Plantedge Administration'
# for Internal pages
admin.site.index_title = 'Welcome To Plantedge '

admin.site.site_title = "PLANTEDGE Admin Portal"

SubscriberForm = select2_modelform(Subscriber, attrs={'width': '250px'})


class PlotListFilter(admin.SimpleListFilter):
   parameter_name = 'id'
   title = 'Plot ID'
   template = 'admin/filters/plot_filters.html'

   def lookups(self, request, model_admin):
        return(
           ('', ''),
       )

   def queryset(self, request, queryset):
       print(queryset)
       if self.value() is not None  and  self.value()!='':
           uid = self.value()
           return queryset.filter(plot_id=uid)




class Plot_S3_LinksAdmin(admin.ModelAdmin):
    list_display = ('id', 'plot','creation_date','storage_url')
    list_filter = (PlotListFilter,  ('creation_date', DateRangeFilter),)
    actions = ['download_from_amazon']

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions




    def download_from_amazon(self, request, queryset):

        from django.http import HttpResponse
        gaia = Gaia()
        for s in queryset:
            print(str(s.id)+ str(s.plot)+ str(s.creation_date)+ str(s.storage_url))
            file = gaia.download_asset_from_s3(s.storage_url)
            fsock = open(file, "rb")
            response = HttpResponse(fsock, content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename='+file
            fsock.close()
            os.unlink(file)

        return response

    # override 'get_readonly_fields()' method of admin class to make read only fields after first edit
    def get_readonly_fields(self, request, obj=None):
        if obj:  # This is the case when obj is already created i.e. it's an edit
            return ['id','plot','creation_date','storage_url']
        else:
            return []

class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


class AoiAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'name')

    # override 'get_readonly_fields()' method of admin class to make read only fields after first edit
    def get_readonly_fields(self, request, obj=None):
        if obj:  # This is the case when obj is already created i.e. it's an edit
            return ['id','client','client_aoi_id','status','name','coordinates','raw_coordinates','plot',
                    'description','create_time','update_time','variant','date_planted']
        else:
            return []


class AssetAdmin(admin.ModelAdmin):
    list_display = ('id', 'aoi', 'date')


class PlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'file')
    # override 'get_readonly_fields()' method of admin class to make read only fields after first edit
    def get_readonly_fields(self, request, obj=None):
        if obj: #This is the case when obj is already created i.e. it's an edit
            return ['date_planted','file']
        else:
            return []


class AlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'alert_date','type','status')
    list_filter = ("alert_date",)


class PreparationStatAdmin(admin.ModelAdmin):
    list_display = ('id', 'plot_id', 'plot_id_consol')

class ThresholdsAdmin(admin.ModelAdmin):
    list_display = ('id', 'date_generated')

class SubscriberAdmin(admin.ModelAdmin):

    # form = SubscriberForm
    writer = ChainedManyToManyField(
        Subscriber,
        horizontal=True,
        verbose_name='client',
        chained_field="client",
        chained_model_field="client")
    list_display = ('id', 'name','client', 'email','plot_alert_json')


admin.site.register(Client, ClientAdmin)
admin.site.register(Aoi, AoiAdmin)
admin.site.register(Asset, AssetAdmin)
admin.site.register(Plots, PlotAdmin)
admin.site.register(Alert, AlertAdmin)
admin.site.register(Subscriber, SubscriberAdmin)
admin.site.register(PreparationStat, PreparationStatAdmin)
admin.site.register(Thresholds,ThresholdsAdmin)
admin.site.register(Plot_S3_Links, Plot_S3_LinksAdmin)