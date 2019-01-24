import glob
import json
import numpy as np
import os

from celery import Celery, task
from django.core.files.storage import FileSystemStorage


from plantedge.core.athena import Athena
from plantedge.core.gaia import Gaia
from plantedge.core.theia import Theia
from plantedge.models import *
from plantedge.celerypy import celery_app

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
            cloud_cover = params.get('cloud_cover', 0.1)
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
                'end':  end_date
            },
            'cloud_threshold': cloud_cover
        }
        available_planet_assets = self.gaia.find_available_asset([aoi.coordinates], filter_params)
        if available_planet_assets.get('features'):
            for ass in available_planet_assets.get('features'):
                properties = ass.get('properties')
                date = properties.get('acquired').split('T')[0]
                payload = {
                    'aoi_id': aoi_id,
                    'planet_item_id': ass.get('id'),
                    'date': date
                }
                activate_clipped_asset.apply_async((payload,), countdown=1)
                print('Queued :' + date + '  -> ' + ass.get('id'))
        else:
            print('No available_planet_assets!')

@celery_app.task(name='vegetationIndex.activate_clipped_asset')
def activate_clipped_asset(params):
    '''
    First step is to activate the planet's item and prepare the folder to download the item later
    '''
    gaia = Gaia()
    try:
        aoi_id = params['aoi_id']
        planet_item_id = params['planet_item_id']
        date = params['date']
    except Exception as e:
        return 'AOI, Date, & Planet Item ID must be given'

    aoi = Aoi.objects.get_by_id(aoi_id)
    if not aoi:
        return 'AOI not found.'

    planet_item_details = {
        'item_id': planet_item_id,
        'item_type': 'PSScene4Band',
        'asset_type': 'analytic'
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

@celery_app.task(name='vegetationIndex.get_clipped_asset')
def get_clipped_asset(params, asset_activation):
    '''
    Second step is to download the item to the desired path
    '''
    gaia = Gaia()
    filepath = params['filepath']
    success = gaia.get_clipped_asset(asset_activation, filepath)
    if success == 0:
        get_clipped_asset.apply_async((params, asset_activation), countdown=20)
        return False
    elif success == 1:
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

    mean_ndvi = np.ma.array(data = ndvi, mask = clip_udm).mean()
    mean_ndwi = np.ma.array(data = ndwi, mask = clip_udm).mean()
    mean_bai = np.ma.array(data = bai, mask = clip_udm).mean()
    mean_rvi = np.ma.array(data = rvi, mask = clip_udm).mean()
    mean_gndvi = np.ma.array(data = gndvi, mask = clip_udm).mean()
    mean_msavi = np.ma.array(data = msavi, mask = clip_udm).mean()
    mean_dirt = np.ma.array(data = dirt, mask = clip_udm).mean()
    mean_evi = np.ma.array(data = evi, mask = clip_udm).mean()

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
        'bands' : bands_arr,
        'profile' : file_profile,
        'filepath' : filepath,
        'filename' : 'output-analytics.tif'
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

    storage_url = gaia.store_asset_to_s3(filepath)

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

    return asset.id

#
# if __name__ == '__main__':
#     a = VegetationIndex()
#     params = {
#         'aoi_id': 23,
#         'start_date': '2018-02-01',
#         'end_date': '2018-12-31',
#     }
#     a.manage_index_creation(params)

