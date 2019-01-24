from django.shortcuts import render

# Create your views here.
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view

from datetime import datetime
from datetime import date
from datetime import time
from datetime import timedelta



from plantedge.models import *

import json

outputdata = {}
outputdata['features'] = []


@api_view(['POST'])
def plotToAois(request):

    try:

        plot = Plots.objects.get(id=request.data['id'])

        file = plot.file
        # with open('/home/zeeshan/Downloads/feat.geojson') as json_file:
        creation_dateTime = datetime.now(),
        # creation_dateTime = '2018-08-31 19:28:21.67124+05',
        message = 'oneclout'
        status = 'ACTIVE',
        name='zeeshan'
        descriptions=message
        client = Client.objects.get(id=plot.client_id)
        # plot_id = Plots.objects.get(id=plot.client_plot_ID)

        with open(file.path) as json_file:
            data = json.load(json_file)
        for p in data['features']:

            coordinates = p['geometry']['coordinates']
            raw_coordinates=coordinates

            client_aoi_id='10'

            params = {
                'coordinates':coordinates,
                'name': name,
                'client_aoi_id': client_aoi_id,
                 'raw_coordinates':raw_coordinates,
                'descriptions': descriptions,
                'plot' :plot,
            }
            Aoi.objects.create_aoi(client=client, params=params)


        return Response('Ok', status=status.HTTP_200_OK)
    except :
        return Response('Error on saving AOI', status=status.HTTP_400_BAD_REQUEST)