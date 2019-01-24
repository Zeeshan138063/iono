from fastai.plots import *
from IPython.display import Image, display
from osgeo import gdal
import rasterio
import csv
import numpy
from json import dumps, loads, JSONEncoder

from plantedge.facade.analysis import Analysis
from plantedge.models import *
from datetime import datetime

import boto3
import botocore

import shutil
import time
import zipfile

# from plantedge.celerypy import celery_app

# from celery import Celery, task
# from plantedge.celerypy import celery_app



from django.conf import settings
from xml.dom import minidom


class Preparation():
    '''
    Responsible for preparation of asset for analysis
    '''

    def __init__(self):
        self.__PLANET_API_KEY = getattr(settings, "PLANET_API_KEY", None)
        self._AWS_STORAGE_BUCKET_NAME = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
        self._ACCESS_KEY = getattr(settings, "AWS_ACCESS_KEY_ID", None)
        self._SECRET_KEY = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
        self._LOCAL_ASSETS_DIR = getattr(settings, "LOCAL_ASSETS_DIR", None)
        self._ANALYSIS_DIR_PATH = './' + self._LOCAL_ASSETS_DIR + '/'
        self.__PLANET_AUTH = (self.__PLANET_API_KEY, '')

    def get_assets_from_plot(self, plot_id):
        if plot_id is not None:
            aoi = Aoi.objects.filter(plot_id=plot_id)
            assets = Asset.objects.filter(aoi_id__in=aoi)
            return assets
        return 'failed to get Plot Id'

    # this encoder is used to dumps int64 type object
    class MyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, numpy.integer):
                return int(obj)
            elif isinstance(obj, numpy.floating):
                return float(obj)
            elif isinstance(obj, numpy.ndarray):
                return obj.tolist()
            else:
                return super(self.MyEncoder, self).default(obj)

    # @celery_app.task(name='preparation.preparation_analysis')
    def preparation_analysis(self, params):

        # Ad-Hoc Analysis Options
        analysis_type = "dirt"
        analysis_threshold = 0
        analysis_indicator = 0.95
        analysis_dict_list = []

        filepath = params['filepath']
        asset = params['asset']

        '''
         "plot_id" -> AOI id
         "plot_id_consol" -> Plot id
        '''

        plot_record = filepath
        plot_id = asset.aoi_id

        analysis_image_paths = []
        sat_raw_image_paths = []
        sat_raw_udm_paths = []
        sat_raw_metadata_paths = []

        # calculate indices and images
        # for plot_record in selected_plot_records:
        sat_raw_image_paths.append(glob(f'{plot_record}/*AnalyticMS_clip.tif')[0])
        sat_raw_udm_paths.append(glob(f'{plot_record}/*AnalyticMS_DN_udm_clip.tif')[0])
        sat_raw_metadata_paths.append(glob(f'{plot_record}/*AnalyticMS_metadata_clip.xml')[0])

        # calculate NDVI stats
        df = pd.read_csv(f'{plot_record}/ndvi_dump.csv', header=None)
        df = df.stack()
        df[(df < 0.1)] = np.nan
        ndvi_mean = df.mean()
        ndvi_95th_percentile = df.quantile(0.95)
        ndvi_80th_percentile = df.quantile(0.80)
        ndvi_std = df.std()
        ndvi_count = df.count()

        # calculate EVI stats
        df = pd.read_csv(f'{plot_record}/evi_dump.csv', header=None)
        df = df.stack()
        df[(df < 0.2)] = np.nan
        evi_mean = df.mean()
        evi_95th_percentile = df.quantile(0.95)
        evi_80th_percentile = df.quantile(0.80)
        evi_std = df.std()
        evi_count = df.count()

        # calculate GNDVI stats
        df = pd.read_csv(f'{plot_record}/gndvi_dump.csv', header=None)
        df = df.stack()
        df[(df < 0.2)] = np.nan
        gndvi_mean = df.mean()
        gndvi_95th_percentile = df.quantile(0.95)
        gndvi_80th_percentile = df.quantile(0.80)
        gndvi_std = df.std()
        gndvi_count = df.count()

        # calculate NDWI stats
        df = pd.read_csv(f'{plot_record}/ndwi_dump.csv', header=None)
        df = df.stack()
        df[(df < -0.7)] = np.nan
        ndwi_mean = df.mean()
        ndwi_95th_percentile = df.quantile(0.95)
        ndwi_80th_percentile = df.quantile(0.80)
        ndwi_20th_percentile = df.quantile(0.20)
        ndwi_5th_percentile = df.quantile(0.05)
        ndwi_std = df.std()
        ndwi_count = df.count()
        ndwi_high_count = df[(df > -0.7)].count()

        # calculate RVI stats
        df = pd.read_csv(f'{plot_record}/rvi_dump.csv', header=None)
        df = df.stack()
        df[(df < 1.5)] = np.nan
        rvi_mean = df.mean()
        rvi_95th_percentile = df.quantile(0.95)
        rvi_80th_percentile = df.quantile(0.80)
        rvi_std = df.std()
        rvi_count = df.count()

        # calculate DIRT stats
        df = pd.read_csv(f'{plot_record}/dirt_dump.csv', header=None)
        df = df.stack()
        df[(df < 0)] = np.nan
        dirt_mean = df.mean()
        dirt_95th_percentile = df.quantile(0.95)
        dirt_80th_percentile = df.quantile(0.80)
        dirt_std = df.std()
        dirt_count = df.count()

        # calculate Haze factor
        from xml.dom import minidom
        src = rasterio.open(sat_raw_image_paths[-1])
        udm = rasterio.open(sat_raw_udm_paths[-1])
        xmldoc = minidom.parse(sat_raw_metadata_paths[-1])
        nodes = xmldoc.getElementsByTagName("ps:bandSpecificMetadata")
        coeffs = {}
        for node in nodes:
            bn = node.getElementsByTagName("ps:bandNumber")[0].firstChild.data
            if bn in ['1', '2', '3', '4']:
                i = int(bn)
                value = node.getElementsByTagName("ps:reflectanceCoefficient")[0].firstChild.data
                coeffs[i] = float(value)
        b = src.read(1).flatten() * coeffs[1]
        g = src.read(2).flatten() * coeffs[2]
        r = src.read(3).flatten() * coeffs[3]
        arr = []
        for i, v in enumerate(r):
            x = min(r[i], g[i], b[i])
            if x > 0:
                arr.append(x)
        # mean_minrgb = np.ma.array(data = arr, mask = udm.flatten()).mean()
        minrgb_mean = np.mean(arr)  # haze indicator

        arr = np.asarray(arr)

        valid_pixels = np.count_nonzero(~np.isnan(arr))
        arr[(arr < 0.1)] = np.nan
        bad_pixels = np.count_nonzero(~np.isnan(arr))
        minrgb_fractionbad = bad_pixels / valid_pixels

        date_string = plot_record[(plot_record.find('-') + 1):(plot_record.find('-') + 1 + 8)]
        date_string = date_string[0:4] + "-" + date_string[4:6] + "-" + date_string[6:8]
        aoi = Aoi.objects.get(id=plot_id)

        # # get age of trees at observation
        a = time.strptime(date_string, '%Y-%m-%d')
        b = aoi.date_planted
        b = time.strptime(str(b), '%Y-%m-%d')
        a = time.mktime(a)
        b = time.mktime(b)
        age_at_obs_months = int(round((a - b) / (30.5 * 24 * 60 * 60)))

        stat = PreparationStat.objects.create(asset_id=asset,
                                              plot_record=plot_record,
                                              plot_id_consol=aoi.plot_id,
                                              date=date_string,
                                              variant=aoi.variant,
                                              planted_date=aoi.date_planted,
                                              plot_id=plot_id,
                                              age_at_obs_months=age_at_obs_months,
                                              min_rgb_haze_indicator=minrgb_mean,
                                              likely_haze=(1 if minrgb_mean > 0.09 else 0),
                                              min_rgb_bad_fraction=minrgb_fractionbad,
                                              likely_cloud=(1 if minrgb_fractionbad > 0.2 else 0),
                                              ndvi=ndvi_mean,
                                              ndvi_95=ndvi_95th_percentile,
                                              ndvi_80=ndvi_80th_percentile,
                                              ndvi_std=ndvi_std,
                                              ndvi_count=numpy.int64(ndvi_count),
                                              gndvi=gndvi_mean,
                                              gndvi_95=ndvi_95th_percentile,
                                              gndvi_80=gndvi_80th_percentile,
                                              gndvi_std=gndvi_std,
                                              gndvi_count=numpy.int64(gndvi_count),
                                              evi=evi_mean,
                                              evi_95=evi_95th_percentile,
                                              evi_80=evi_80th_percentile,
                                              evi_std=evi_std,
                                              evi_count=numpy.int64(evi_count),
                                              rvi=rvi_mean,
                                              rvi_95=rvi_95th_percentile,
                                              rvi_80=evi_80th_percentile,
                                              rvi_std=rvi_std,
                                              rvi_count=numpy.int64(rvi_count),
                                              dirt=dirt_mean,
                                              dirt_95=dirt_95th_percentile,
                                              dirt_std=dirt_std,
                                              dirt_count=numpy.int64(dirt_count),
                                              ndwi=ndwi_mean,
                                              ndwi_95=ndwi_95th_percentile,
                                              ndwi_80=ndwi_80th_percentile,
                                              ndwi_20=ndwi_20th_percentile,
                                              ndwi_05=ndwi_5th_percentile,
                                              ndwi_std=ndwi_std,
                                              ndwi_count=numpy.int64(ndwi_count),
                                              ndwi_high_count=numpy.int64(ndwi_high_count)
                                              )

        params['preparationstat'] = stat

        # here calling the create Graph feature

        analysis = Analysis()
        analysis.create_graph(params)



        return True



        # analysis_dict_list.append({"plot_record": plot_record,
        #                                          "plot_id": plot_id,
        #                                          # "plot_id_consol": plot_info_list.get(str(plot_id)).get('plot_id_consol'),
        #                                          "plot_id_consol": aoi.plot_id,
        #                                          "date": date_string,
        #                                          # "variant": plot_info_list.get(str(plot_id)).get('variant'),
        #                                          "variant": aoi.variant,
        #                                          # "planted_date": plot_info_list.get(str(plot_id)).get('planted_date'),
        #                                          "planted_date": aoi.date_planted.date(),
        #                                          "age_at_obs_months": age_at_obs_months,
        #                                          "min_rgb_haze_indicator": minrgb_mean,
        #                                          "likely_haze": (1 if minrgb_mean > 0.09 else 0),
        #                                          "min_rgb_bad_fraction": minrgb_fractionbad,
        #                                          "likely_cloud": (1 if minrgb_fractionbad > 0.2 else 0),
        #                                          "ndvi": ndvi_mean, "ndvi_95": ndvi_95th_percentile,
        #                                          "ndvi_80": ndvi_80th_percentile,
        #                                          "ndvi_std": ndvi_std,
        #                                          "ndvi_count": numpy.int64(ndvi_count),
        #                                          "gndvi": gndvi_mean, "gndvi_95": gndvi_95th_percentile,
        #                                          "gndvi_80": gndvi_80th_percentile,
        #                                          "gndvi_std": gndvi_std,
        #                                          "gndvi_count": numpy.int64(gndvi_count),
        #                                          "evi": evi_mean,
        #                                          "evi_95": evi_95th_percentile,
        #                                          "evi_80": evi_80th_percentile,
        #                                          "evi_std": evi_std,
        #                                          "evi_count": numpy.int64(evi_count),
        #                                          "rvi": rvi_mean,
        #                                          "rvi_95": rvi_95th_percentile,
        #                                          "rvi_80": rvi_80th_percentile,
        #                                          "rvi_std": rvi_std,
        #                                           "rvi_count": numpy.int64(rvi_count),
        #                                          "dirt": dirt_mean,
        #                                          "dirt_95": dirt_95th_percentile,
        #                                          "dirt_std": dirt_std,
        #                                          "dirt_count": numpy.int64(dirt_count),
        #                                          "ndwi": ndwi_mean,
        #                                           "ndwi_95": ndwi_95th_percentile,
        #                                          "ndwi_80": ndwi_80th_percentile,
        #                                          "ndwi_20": ndwi_20th_percentile,
        #                                          "ndwi_05": ndwi_5th_percentile,
        #                                          "ndwi_std": ndwi_std,
        #                                          "ndwi_count": numpy.int64(ndwi_count),
        #                                          "ndwi_high_count": numpy.int64(ndwi_high_count)})
        #
        # # plot_analysis.csv
        #
        #
        # with open(self._PLOT_ANALYSIS_CSV_PATH, 'w') as csvfile:  # Just use 'w' mode in 3.x , and wb for python 2
        #     w = csv.DictWriter(csvfile, analysis_dict_list[0].keys())
        #     w.writeheader()
        #     w.writerow(analysis_dict_list[0])





        # analysis_dict_list.append({"plot_record": plot_record,
        # asset.preparation_analysis =json.dumps({"plot_record": plot_record,
        #                            "plot_id": plot_id,
        #                            # "plot_id_consol": plot_info_list.get(str(plot_id)).get('plot_id_consol'),
        #                            "plot_id_consol": aoi.plot_id,
        #                            "date": date_string,
        #                            # "variant": plot_info_list.get(str(plot_id)).get('variant'),
        #                            "variant": aoi.variant,
        #                            # "planted_date": plot_info_list.get(str(plot_id)).get('planted_date'),
        #                            "planted_date":  aoi.date_planted,
        #                            "age_at_obs_months": age_at_obs_months,
        #                            "min_rgb_haze_indicator": minrgb_mean,
        #                            "likely_haze": (1 if minrgb_mean > 0.09 else 0),
        #                            "min_rgb_bad_fraction": minrgb_fractionbad,
        #                            "likely_cloud": (1 if minrgb_fractionbad > 0.2 else 0),
        #                            "ndvi": ndvi_mean, "ndvi_95": ndvi_95th_percentile,
        #                            "ndvi_80": ndvi_80th_percentile, "ndvi_std": ndvi_std, "ndvi_count": numpy.int64(ndvi_count),
        #                            "gndvi": gndvi_mean, "gndvi_95": gndvi_95th_percentile,
        #                            "gndvi_80": gndvi_80th_percentile, "gndvi_std": gndvi_std,
        #                            "gndvi_count": numpy.int64(gndvi_count),
        #                            "evi": evi_mean, "evi_95": evi_95th_percentile, "evi_80": evi_80th_percentile,
        #                            "evi_std": evi_std, "evi_count": numpy.int64(evi_count),
        #                            "rvi": rvi_mean, "rvi_95": rvi_95th_percentile, "rvi_80": rvi_80th_percentile,
        #                            "rvi_std": rvi_std, "rvi_count": numpy.int64(rvi_count),
        #                            "dirt": dirt_mean, "dirt_95": dirt_95th_percentile, "dirt_std": dirt_std,
        #                            "dirt_count": numpy.int64(dirt_count),
        #                            "ndwi": ndwi_mean, "ndwi_95": ndwi_95th_percentile,
        #                            "ndwi_80": ndwi_80th_percentile, "ndwi_20": ndwi_20th_percentile,
        #                            "ndwi_05": ndwi_5th_percentile, "ndwi_std": ndwi_std, "ndwi_count": numpy.int64(ndwi_count),
        #                            "ndwi_high_count": numpy.int64(ndwi_high_count)},cls=self.MyEncoder)


        # json.dumps({'value': numpy.int64(42)}, default=self.default)



        # asset.preparation_analysis = json.dumps(analysis_dict_list)
        # asset.save()
