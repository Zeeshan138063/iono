# from django.db.models.signals import post_save
# from django.dispatch import receiver
#
# from django.shortcuts import render
#
# # # Create your views here.
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.decorators import api_view
#
# from datetime import datetime
# from datetime import date
# from datetime import time
# from datetime import timedelta
# from plantedge.models import *
#
# import json
# import numpy
# import time
#
# from plantedge.core.athena import Athena
# from plantedge.core.gaia import Gaia
# from plantedge.facade.preparation import Preparation
# from plantedge.facade.analysis import Analysis
# # from plantedge.facade.vegetationIndex import *
#
#
# @receiver(post_save, sender=Aoi)
# def create_user_report(sender, instance, created, **kwargs):
#     print('AOI created id '+ str(instance.id))
#
#
# @receiver(post_save, sender=Plots)
# def plotToAois(sender, instance, **kwargs):
#
#     try:
#         # analysis = Analysis()
#         # analysis.start_analysis()
#         gaia = Gaia()
#         # f_vegetation_Index = VegetationIndex()
#
#         plot = Plots.objects.get(id=instance.id)
#
#         file = plot.file
#
#         creation_dateTime = datetime.now()
#         message = 'oneclout'
#         status = 'ACTIVE',
#         name='zeeshan'
#         descriptions=message
#         client = Client.objects.get(id=plot.client_id)
#         # plot_id = Plots.objects.get(id=plot.client_plot_ID)
#
#         with open(file.path) as json_file:
#             data = json.load(json_file)
#         for p in data['features']:
#
#             coordinates = p['geometry']['coordinates'][0]
#             raw_coordinates=coordinates
#
#             client_aoi_id='10'
#
#             params = {
#                 'coordinates':coordinates,
#                 'name': name,
#                 'client_aoi_id': client_aoi_id,
#                  'raw_coordinates':raw_coordinates,
#                 'descriptions': descriptions,
#                 'plot' :plot,
#                 'date_planted':creation_dateTime,
#             }
#             aoi_created=Aoi.objects.create_aoi(client=client, params=params)
#
#             params = {
#                 'aoi_id': aoi_created.id,
#                 # 'aoi_id': 2,
#                 'start_date': '2018-02-01',
#                 'end_date': '2018-12-31',
#             }
#             # print('starting AOI: ' + str(aoi_created.id))
#             # f_vegetation_Index.manage_index_creation(params)
#             print()
#             print()
#             time.sleep(10)
#         return Response('OK')
#
#     except:
#         return Response('Error on saving AOI')
#
#
#
#
#
#
#
