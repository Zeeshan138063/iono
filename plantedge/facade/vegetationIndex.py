import glob
import json
import os
import shutil
import time
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta

import numpy as np
import pandas as pd
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.db.models.signals import m2m_changed

from downloads3.models import Plot_S3_Links
from plantedge.celerypy import celery_app
from plantedge.core.athena import Athena
from plantedge.core.gaia import Gaia
from plantedge.core.theia import Theia
from plantedge.facade.preparation import Preparation
from plantedge.models import *


class VegetationIndex:
    '''
    Product level interface that communicate with models and core modules
    Responsible for product logic to construct vegetation indexes (NDVI, NDWI, BAI, etc) from AOI
    '''

    def __init__(self):

        self.gaia = Gaia()
        self.athena = Athena()
        self.theia = Theia()
        self.fs = FileSystemStorage()
        self.PLANET_API_KEY = getattr(settings, "PLANET_API_KEY", None)

    def manage_index_creation(self, params):
        '''
        Main logic of vegetation index asset creation.
        Given the desired AOI and date to analyze, creating parallel tasks to generate asset.

        Params Input:
            1. aoi_id
            2. start_date
            3. end_date
            4. cloud_cover threshold

        Steps:
            1. Simplify AOI
            2. Find available planet's item for given input params
            3. Queue tasks to activate planet's item
        '''
        try:

            aoi_id = params['aoi_id']
            start_date = str(params['start_date']) + 'T00:00:00.000Z'
            end_date = str(params['end_date']) + 'T00:00:00.000Z'
            # API search on the relevant coordinates, but allow 50% cloud cover
            cloud_cover = params.get('cloud_cover', 0.5)
        except Exception as e:
            return (None, 'AOI, Start Date, & Planet Item ID must be given')

        aoi = Aoi.objects.get_by_id(aoi_id)
        if not aoi:
            return (None, 'AOI not found.')
        elif len(aoi.coordinates) > 110:
            print('simplyfying coordinates for AOI: ' + str(aoi.id))
            coordinates = aoi.coordinates
            while len(coordinates) > 110:
                coordinates = self.gaia.simplify_coordinates(coordinates)
            aoi.coordinates = coordinates
            aoi.save()

        filter_params = {
            'date_filter': {
                'start': start_date,
                'end': end_date
            },
            'cloud_threshold': cloud_cover
        }
        available_planet_assets = self.gaia.find_available_asset([aoi.coordinates], filter_params,
                                                                 item_types='PSScene4Band')
        if available_planet_assets.get('features'):
            for ass in available_planet_assets.get('features'):
                properties = ass.get('properties')
                date = properties.get('acquired').split('T')[0]
                print('ass.get', ass.get('id'))
                payload = {
                    'aoi_id': aoi_id,
                    'planet_item_id': ass.get('id'),
                    'date': date,
                    'PLANET_API_KEY': self.PLANET_API_KEY,
                    'item_type': "PSScene4Band",
                    'asset_type': "udm",
                    'pixels_usability_test_pass': 0

                }
                activate_clipped_asset.apply_async((payload,), countdown=1)
                print('Queued :' + date + '  -> ' + ass.get('id'))
        else:
            print('No available_planet_assets!')

    def check_update_asset(self):

        today = datetime.now().date()
        start_date = str((today - timedelta(weeks=1))) + 'T00:00:00.000Z'
        end_date = str(today) + 'T00:00:00.000Z'
        # API search on the relevant coordinates, but allow 50% cloud cover
        cloud_cover = 0.5

        filter_params = {
            'date_filter': {
                'start': start_date,
                'end': end_date
            },
            'cloud_threshold': cloud_cover
        }

        # since A  represents 'Active' Aoi
        active_aois = Aoi.objects.filter(status='D')
        for active_aoi in active_aois:
            aoi_id = active_aoi.id

            available_planet_assets = self.gaia.find_available_asset([active_aoi.coordinates], filter_params,
                                                                     item_types='PSScene4Band')
            if available_planet_assets.get('features'):
                already_download_assets = Asset.objects.filter(aoi__plot_id=active_aoi.id)
                for ass in available_planet_assets.get('features'):
                    if already_download_assets:
                        for already_download_asset in already_download_assets:
                            '''
                             here check if the already_download_asset.planet_item_id is not equal to the newly searched
                             item_id then download that asset and process as regular flow

                             otherwise download that asset and process
                            '''
                            if ass.get('id') != already_download_asset.planet_item_id:
                                self.start_download_updated_asset(aoi_id, ass)
                    else:
                        self.start_download_updated_asset(aoi_id, ass)

    def start_download_updated_asset(self, aoi_id, ass):
        properties = ass.get('properties')
        date = properties.get('acquired').split('T')[0]
        print('ass.get', ass.get('id'))
        payload = {
            'aoi_id': aoi_id,
            'planet_item_id': ass.get('id'),
            'date': date,
            'PLANET_API_KEY': self.PLANET_API_KEY,
            'item_type': "PSScene4Band",
            'asset_type': "udm",
            'pixels_usability_test_pass': 0

        }
        activate_clipped_asset.apply_async((payload,), countdown=1)
        print('Queued :' + date + '  -> ' + ass.get('id'))


# Cron Job
def check_update_asset_cron():
    print('check_update_asset is running ')

    today = datetime.now().date()
    start_date = str((today - timedelta(weeks=1))) + 'T00:00:00.000Z'
    end_date = str(today) + 'T00:00:00.000Z'
    # API search on the relevant coordinates, but allow 50% cloud cover
    cloud_cover = 0.5

    filter_params = {
        'date_filter': {
            'start': start_date,
            'end': end_date
        },
        'cloud_threshold': cloud_cover
    }
    gaia = Gaia()

    # since A  represents 'Active' Aoi
    active_aois = Aoi.objects.filter(status='A')
    for active_aoi in active_aois:
        aoi_id = active_aoi.id

        available_planet_assets = gaia.find_available_asset([active_aoi.coordinates], filter_params,
                                                            item_types='PSScene4Band')
        if available_planet_assets.get('features'):
            already_download_assets = Asset.objects.filter(aoi__id=active_aoi.id)
            for ass in available_planet_assets.get('features'):
                if already_download_assets:
                    for already_download_asset in already_download_assets:
                        '''
                         here check if the already_download_asset.planet_item_id is not equal to the newly searched
                         item_id then download that asset and process as regular flow

                         otherwise download that asset and process
                        '''
                        if ass.get('id') != already_download_asset.planet_item_id:
                            start_download_updated_asset(aoi_id, ass)
                else:
                    start_download_updated_asset(aoi_id, ass)


def start_download_updated_asset(aoi_id, ass):
    print('inside fo start_download new asset')
    properties = ass.get('properties')
    date = properties.get('acquired').split('T')[0]
    print('ass.get', ass.get('id'))
    payload = {
        'aoi_id': aoi_id,
        'planet_item_id': ass.get('id'),
        'date': date,
        'item_type': "PSScene4Band",
        'asset_type': "udm",
        'pixels_usability_test_pass': 0

    }
    activate_clipped_asset.apply_async((payload,), countdown=1)
    print('Queued :' + date + '  -> ' + ass.get('id'))


def file_write_cron():
    # file = open('./storage/testfile.txt', 'a')
    # file.write(str(datetime.now().time()) + '\n')
    # file.close()
    print("testing")
    return


@celery_app.task(name='vegetationIndex.activate_clipped_asset')
def activate_clipped_asset(params):
    """
    Download only the UDM for the assets
	Extract the relevant part of the UDM to our JSON
	Check to see if <2% of the pixels are unsuable.
	If <2% - download clip using the Clips API (as per now) and proceed as normal
	If >= 2%, skip
    """

    gaia = Gaia()
    try:
        aoi_id = params['aoi_id']
        planet_item_id = params['planet_item_id']
        aoi = Aoi.objects.get_by_id(aoi_id)
        item_type = params['item_type']
        asset_type = params['asset_type']


    except Exception as e:
        return 'AOI, Date, & Planet Item ID must be given'

    try:

        if not aoi:
            return 'AOI not found.'

        planet_item_details = {
            'item_id': planet_item_id,
            'item_type': item_type,
            'asset_type': asset_type
        }

        aoi_json = gaia.create_aoi_json(
            [aoi.coordinates],
            planet_item_details
        )

        asset_activation = gaia.activate_clipped_asset(aoi_json)
        if not asset_activation:
            activate_clipped_asset.apply_async((params,), countdown=1)
            return False
        filepath = './storage/' + str(aoi_id) + '-' + str(planet_item_id) + '/'
        if not os.path.exists(filepath):
            os.makedirs(filepath)
        params['filepath'] = filepath

        get_clipped_asset.delay(params, asset_activation)

        return True
    except:
        return False


@celery_app.task(name='vegetationIndex.get_clipped_asset')
def get_clipped_asset(params, asset_activation):
    '''
    Second step is to download the item to the desired path
    '''
    gaia = Gaia()
    filepath = params['filepath']
    print('filepath ', str(filepath))
    success = gaia.get_clipped_asset(asset_activation, filepath)
    if success == 0:
        get_clipped_asset.apply_async((params, asset_activation), countdown=20)
        return False
    elif success == 1:

        if params['pixels_usability_test_pass'] == 0:
            udm_filename = glob.glob(filepath + '*udm_clip.tif')[0]
            athena = Athena()
            is_cloudy_udm = athena.is_cloudy_udm(udm_filename)
            if is_cloudy_udm > 0:
                # remove that asset and end the process for this asset
                shutil.rmtree(filepath)
                print('Fail cloud test ')
                return  # if udm is > 2 % cloudy then skip processing
            else:
                # remove the current content <croped UDM>and download the remaining asset
                # and then Start the analysis Process

                print('Successfully pass the Cloudy Test')
                params['pixels_usability_test_pass'] = 1
                params['pixels_ratio'] = is_cloudy_udm

                # Gather directory contents
                contents = [os.path.join(filepath, i) for i in os.listdir(filepath)]
                # Iterate and remove each item in the appropriate manner
                [os.remove(i) if os.path.isfile(i) or os.path.islink(i) else shutil.rmtree(i) for i in contents]

                # Update the params['asset_type'] to  analytic
                params['asset_type'] = 'analytic'
                activate_clipped_asset.apply_async((params,), countdown=1)

        elif params['pixels_usability_test_pass'] == 1:
            generate_analytic_assets.delay(params)
        return True
    else:
        return False


@celery_app.task(name='vegetationIndex.generate_analytic_assets')
def generate_analytic_assets(params):
    '''
    Third step is to do calculation, generate the asset, store it S3 and our DB
     '''
    gaia = Gaia()
    theia = Theia()
    athena = Athena()

    date = params['date']
    aoi_id = params['aoi_id']
    filepath = params['filepath']
    planet_item_id = params['planet_item_id']

    aoi = Aoi.objects.get_by_id(aoi_id)

    udm_filename = glob.glob(filepath + '*udm_clip.tif')[0]
    raw_filename = glob.glob(filepath + '*_AnalyticMS_clip.tif')[0]
    metadata = glob.glob(filepath + '*_AnalyticMS_metadata_clip.xml')[0]

    udm, err = gaia.read_band(udm_filename)
    metadata_xml, err = gaia.parse_xml(metadata)
    band_file, err = gaia.read_band(raw_filename)
    clip_udm = athena.create_unusable_clip_mask(band_file, udm)

    is_hazy = athena.is_hazy(band_file, metadata_xml, clip_udm)

    ndvi, err = athena.calculate_NDVI(band_file, metadata_xml)
    ndwi, err = athena.calculate_NDWI(band_file, metadata_xml)
    bai, err = athena.calculate_BAI(band_file, metadata_xml)
    rvi, err = athena.calculate_RVI(band_file, metadata_xml)
    gndvi, err = athena.calculate_GNDVI(band_file, metadata_xml)
    msavi, err = athena.calculate_MSAVI(band_file, metadata_xml)
    dirt, err = athena.calculate_DIRT(band_file, metadata_xml)
    evi, err = athena.calculate_EVI(band_file, metadata_xml)
    usability_score = athena.calculate_usability_score(udm)

    ndvi = np.where(clip_udm, -1, ndvi)
    ndwi = np.where(clip_udm, -1, ndwi)
    bai = np.where(clip_udm, -1, bai)
    rvi = np.where(clip_udm, -1, rvi)
    gndvi = np.where(clip_udm, -1, gndvi)
    msavi = np.where(clip_udm, -1, msavi)
    dirt = np.where(clip_udm, -1, dirt)
    evi = np.where(clip_udm, -1, evi)

    mean_ndvi = np.ma.array(data=ndvi, mask=clip_udm).mean()
    mean_ndwi = np.ma.array(data=ndwi, mask=clip_udm).mean()
    mean_bai = np.ma.array(data=bai, mask=clip_udm).mean()
    mean_rvi = np.ma.array(data=rvi, mask=clip_udm).mean()
    mean_gndvi = np.ma.array(data=gndvi, mask=clip_udm).mean()
    mean_msavi = np.ma.array(data=msavi, mask=clip_udm).mean()
    mean_dirt = np.ma.array(data=dirt, mask=clip_udm).mean()
    mean_evi = np.ma.array(data=evi, mask=clip_udm).mean()

    print('-----')
    print(date)
    print("ndvi : " + str(mean_ndvi))
    print("ndwi : " + str(mean_ndwi))
    print("bai : " + str(mean_bai))
    print("rvi : " + str(mean_rvi))
    print("gndvi : " + str(mean_gndvi))
    print("msavi : " + str(mean_msavi))
    print("dirt : " + str(mean_dirt))
    print("evi : " + str(mean_evi))
    print('-----')

    bands_arr = (ndvi, ndwi, bai, rvi, gndvi, msavi, dirt, evi)
    file_profile = band_file.profile
    file_profile['count'] = len(bands_arr)
    file_profile['dtype'] = 'float64'
    gaia.write_band_to_tiff({
        'bands': bands_arr,
        'profile': file_profile,
        'filepath': filepath,
        'filename': 'output-analytics.tif'
    })

    theia.create_cmap_asset(ndvi, filepath, 'output-cmap-ndvi')
    theia.create_cmap_asset(ndwi, filepath, 'output-cmap-ndwi', cmap_name='NDWI')
    theia.create_cmap_asset(bai, filepath, 'output-cmap-bai')
    theia.create_cmap_asset(rvi, filepath, 'output-cmap-rvi', cmap_name='RVI', vmin=-3, vmax=3)
    theia.create_cmap_asset(gndvi, filepath, 'output-cmap-gndvi')
    theia.create_cmap_asset(msavi, filepath, 'output-cmap-msavi', cmap_name='MSAVI')
    theia.create_cmap_asset(dirt, filepath, 'output-cmap-dirt', cmap_name='DIRT')
    theia.create_cmap_asset(evi, filepath, 'output-cmap-evi')

    ## Dump to csv; pls remove if not needed. The size is huge
    np.savetxt(filepath + "ndvi_dump.csv", ndvi, delimiter=",")
    np.savetxt(filepath + "ndwi_dump.csv", ndwi, delimiter=",")
    np.savetxt(filepath + "bai_dump.csv", bai, delimiter=",")
    np.savetxt(filepath + "rvi_dump.csv", rvi, delimiter=",")
    np.savetxt(filepath + "gndvi_dump.csv", gndvi, delimiter=",")
    np.savetxt(filepath + "msavi_dump.csv", msavi, delimiter=",")
    np.savetxt(filepath + "dirt_dump.csv", dirt, delimiter=",")
    np.savetxt(filepath + "evi_dump.csv", evi, delimiter=",")
    ##

    storage_url = ''
    asset = Asset.objects.create_asset(aoi, {
        'type': 'ANALYTIC',
        'date': date,
        'storage_url': storage_url,
        'planet_item_id': planet_item_id,
        'usability_score': usability_score,
        'note': json.dumps({
            'mean_ndvi': mean_ndvi,
            'mean_ndwi': mean_ndwi,
            'mean_bai': mean_bai,
            'mean_rvi': mean_rvi,
            'mean_gndvi': mean_gndvi,
            'mean_msavi': mean_msavi,
            'haze': is_hazy
        })
    })

    params['asset'] = asset
    preparation = Preparation()
    preparation.preparation_analysis(params)

    return asset.id


@celery_app.task(name='vegetationIndex.add')
def add(x, y):
    return x + y


@celery_app.task(name='vegetationIndex.tsum')
def tsum(numbers):
    print('sum ' + str(sum(numbers)))
    return sum(numbers)


@receiver(post_save, sender=Aoi)
def create_user_report(sender, instance, created, **kwargs):
    print('AOI created id ' + str(instance.id))


@receiver(post_save, sender=Plots)
def plotToAois(sender, instance, **kwargs):
    plot = instance
    client = Client.objects.get(id=plot.client_id)
    update_subscriber(plot)

    # if the Plot object edited/updated
    if Aoi.objects.filter(plot_id=instance.id).exists():

        aois = Aoi.objects.filter(plot_id=instance.id)
        for aoi in aois:
            params = {
                'name': plot.name,
                'client_aoi_id': plot.client_plot_ID,
                'description': plot.description,
                'variant': plot.variant,
                'client': client,
                'status': plot.status,
                'id': aoi.id,

            }
            Aoi.objects.update_aoi(params)
        return

    else:
        file = plot.file
        AOIs = []

        with open(file.path) as json_file:
            data = json.load(json_file)

        for p in data['features']:
            coordinates = p['geometry']['coordinates'][0]
            raw_coordinates = coordinates
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
            aoi_created = Aoi.objects.create_aoi(client=client, params=params)
            print('aoi_created.id  ', aoi_created.id)
            AOIs.append(aoi_created.pk)
        first_index = AOIs[0]
        last_index = AOIs[-1]
        print('instance.id inside of post_save signal', str(instance.id))
        transaction.on_commit(lambda: handle_save_task.apply_async(args=(instance.pk, first_index, last_index,)))


@celery_app.task(name='vegetationIndex.handle_save_task')
def handle_save_task(plot, first_index, last_index):
    print('inside of Post save celery' + str(plot))

    try:
        if first_index == 0 and last_index == 0:
            return True

        f_vegetation_Index = VegetationIndex()

        starting_date = datetime.strptime('Jan 1 2017  1:33PM', '%b %d %Y %I:%M%p')
        aois_created = Aoi.objects.filter(id__in=[first_index, last_index])

        for aoi_created in aois_created:
            print('AOI are ', str(aoi_created.id))
            print('AOI ', str(aoi_created))
            params = {
                'aoi_id': aoi_created.id,
                'start_date': max(starting_date.date(), aoi_created.date_planted),
                'end_date': date.today(),
                'plot_id': plot,
            }

            f_vegetation_Index.manage_index_creation(params)
            print()
            print()
            time.sleep(10)

        return True
    except:
        return False


@receiver(m2m_changed, sender=Subscriber.plot.through)
def subscriber_post_save(sender, instance, **kwargs):
    subscriber = instance
    plot_alerts = []
    plots = subscriber.plot.all()
    for plot in plots:
        weed = plot.weed_enable
        forest = plot.forest_health_enable
        if weed == 'Y':
            weed = 'Weed'
        else:
            weed = ''

        if forest == 'Y':
            forest = 'Forest Health'
        else:
            forest = ''

        alerts = [weed, forest]
        payload = {
            'Plot_id ': plot.id,
            'Client plot ID': plot.client_plot_ID,
            'Alerts ': alerts
        }
        if weed == '' and forest == '':
            continue
        plot_alerts.append(payload)
    subscriber.plot_alert_json = json.dumps(plot_alerts)
    subscriber.save()


    # subscriber.save()



    # if Subscriber.objects.filter(id=instance.id).exists():
    #     return
    # else:


def update_subscriber(plot):
    subscribers = Subscriber.objects.all()
    if subscribers.first() is not None:

        weed = plot.weed_enable
        forest = plot.forest_health_enable
        if weed == 'Y':
            weed = 'Weed'
        else:
            weed = ''

        if forest == 'Y':
            forest = 'Forest Health'
        else:
            forest = ''

        alerts = [weed, forest]
        payload = {
            'Plot_id ': plot.id,
            'Client plot ID':plot.client_plot_ID,
            'Alerts ': alerts
        }

        for subscriber in subscribers:

            str_alert_json = subscriber.plot_alert_json
            list_alert_json = json.loads(str_alert_json)

            pd_alert_alerts = pd.read_json(str_alert_json, keep_default_dates=False)._get_values
            count = 0

            for plot_alert, l_alert_json in zip(pd_alert_alerts, list_alert_json):

                if plot.id == plot_alert[1]:
                    list_alert_json[count] = payload
                    subscriber.plot_alert_json = json.dumps(list_alert_json)
                    subscriber.save()
                    break
                count += 1
        return


@receiver(post_save, sender=Asset)
def populate_Plot_S3_Links(sender, instance, **kwargs):
    asset = instance
    if instance.storage_url:
        aoi = Aoi.objects.get(id=asset.aoi_id)
        plot = Plots.objects.get(id=aoi.plot_id)
        Plot_S3_Links.objects.create(plot=plot, storage_url=asset.storage_url)
    return
