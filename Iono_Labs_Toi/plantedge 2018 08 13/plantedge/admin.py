from django.contrib import admin
from .models import *


class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


class AoiAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'name')


class AssetAdmin(admin.ModelAdmin):
    list_display = ('id', 'aoi', 'date')
class PlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'file')

admin.site.register(Client, ClientAdmin)
admin.site.register(Aoi, AoiAdmin)
admin.site.register(Asset, AssetAdmin)
admin.site.register(Plots, PlotAdmin)
