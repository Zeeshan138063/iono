from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from datetime import datetime
from datetime import date
from datetime import time
from datetime import timedelta
import json
import numpy
import time
from plantedge.core.athena import Athena
from plantedge.core.gaia import Gaia
from plantedge.facade.preparation import Preparation
from plantedge.facade.vegetationIndex import *
from plantedge.models import *

outputdata = {}
outputdata['features'] = []


@api_view(['POST'])
def plotToAois(request):

    try:

        f_vegetation_Index = VegetationIndex()
        plot = Plots.objects.get(id=request.data['id'])
        file = plot.file
        AOIs = []


        client = Client.objects.get(id=plot.client_id)
        with open(file.path) as json_file:
            data = json.load(json_file)


        for p in data['features']:

            coordinates = p['geometry']['coordinates'][0]
            raw_coordinates=coordinates

            client_aoi_id = plot.client_plot_ID

            params = {
                'coordinates': coordinates,
                'name': plot.name,
                'client_aoi_id': client_aoi_id,
                'raw_coordinates': raw_coordinates,
                'descriptions': plot.description,
                'plot': plot,
                'date_planted': plot.date_planted,
                'variant': plot.variant,
                'status': plot.status,
            }
            aoi_created=Aoi.objects.create_aoi(client=client, params=params)
            AOIs.append(aoi_created.pk)
        # AOIs = serializers.serialize('json', AOIs)
        starting_date = datetime.strptime('Jan 1 2017  1:33PM', '%b %d %Y %I:%M%p')


        for aoi_created in AOIs:
            aoi_created = Aoi.objects.get(id=aoi_created)
            params = {
            'aoi_id': aoi_created.id,
            'start_date': max(starting_date.date(), aoi_created.date_planted),
            'end_date': date.today(),
            'plot_id': plot.id,
            }

            f_vegetation_Index.manage_index_creation(params)
            print()
            print()
            time.sleep(10)


        return Response('OK')

    except:
        return Response('Error on saving AOI')