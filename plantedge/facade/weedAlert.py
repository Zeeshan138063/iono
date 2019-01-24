import pandas as pd
from datetime import date

from plantedge.core.athena import Athena
from plantedge.core.gaia import Gaia
from plantedge.models import *
import os
import shutil
import numpy as np
from numpy import genfromtxt
from osgeo import gdal, ogr
from json import dumps
import shapefile
import glob
from django.conf import settings


class WeedAlert():
    def __init__(self):
        self.MEDIA_ROOT = getattr(settings, "MEDIA_ROOT", None)
        self.ALERT_MEDIA_ROOT = self.MEDIA_ROOT+'alerts/'
        if not os.path.exists(self.ALERT_MEDIA_ROOT):
            os.makedirs(self.ALERT_MEDIA_ROOT)


    def generate_weed_alerts(self, params):
        """
        # A ==> Query to get assets that qualifies below conditions
        # 1 Asset represents plant that is <12 months old,
        # 2 and flag for monitoring Weed is True
        # 3 and Mean NDVI is 10% above Red Threshold

        input params = {
        filepath : 'path to asset'
        preparation_stat: 'prep_id'
        }
        """

        try:
            print('start of Generate weed alert')
            filepath = params['filepath']
            BORDER = 3
            MAX_TOLERANCE = 3
            ASSET_UPLOAD_TO_S3 = False

            preparation_stat = params['preparationstat']
            plot = Plots.objects.get(id=preparation_stat.plot_id_consol)

            if plot.weed_enable == 'Y' and preparation_stat.age_at_obs_months < 12:
                red_threshold = self.get_red_threshold(preparation_stat)

                if red_threshold and str(red_threshold[0]) != 'nan':
                    red_threshold = red_threshold[0]
                    # now updating the red_threshold with adding 10% more for comparision
                    red_threshold += red_threshold * .10

                    prep_stat_ndvi = preparation_stat.ndvi

                    if prep_stat_ndvi > red_threshold:

                        csv_file_path = glob.glob(filepath + 'ndvi_dump.csv')[0]

                        ndvi_array = genfromtxt(csv_file_path, delimiter=',')  # Read cssv into numpy array
                        max_x = ndvi_array.shape[0]
                        max_y = ndvi_array.shape[1]
                        weed_alert_array = np.zeros((max_x, max_y))

                        for index_x in range(0, max_x):
                            for index_y in range(0, max_y):
                                x_start = max(0, index_x - BORDER)
                                x_end = min(max_x, index_x + BORDER)
                                y_start = max(0, index_y - BORDER)
                                y_end = min(max_y, index_y + BORDER)

                                above_threshold_count = 0

                                for x in range(x_start, x_end):
                                    for y in range(y_start, y_end):
                                        if ndvi_array[x, y] > red_threshold:
                                            above_threshold_count += 1

                                if above_threshold_count >= MAX_TOLERANCE:
                                    weed_alert_array[x_start:x_end, y_start, y_end] = 1

                        ds = gdal.Open(glob.glob(filepath + '*_AnalyticMS_clip.tif')[0])
                        band_4_array = np.array(ds.GetRasterBand(4).ReadAsArray())
                        params['weed_alert_array'] = weed_alert_array
                        weed_alert_channel_array = np.add(band_4_array, weed_alert_array)

                        ds.GetRasterBand(4).WriteArray(weed_alert_channel_array)
                        weed_alert_channel_band = ds.GetRasterBand(4)
                        params['weed_alert_channel_band'] = weed_alert_channel_band
                        print('weed_alert_channel_array calculated successfully')

                        if self.polygonize_weedAlertChannel(params):
                            # if the  polygonize is successful then upload asset to the S3
                            print('polygonize is successful')

                            params['type'] = 'Weed'
                            params['status'] = 'Active'
                            self.populate_alert_table(params)
                            print('successfully weed alert generated')

                            storage_url = self.upload_asset_s3(params)
                            ASSET_UPLOAD_TO_S3 = True
                            params['storage_url'] = storage_url
                            print('successfully upload to s3')

                            return True

            if ASSET_UPLOAD_TO_S3 == False:
                storage_url = self.upload_asset_s3(params)
                return True

        except:
            if ASSET_UPLOAD_TO_S3 == False:
                storage_url = self.upload_asset_s3(params)

            return False

    '''
    Populate Alert Model
    '''

    def populate_alert_table(self, params):
        '''
        if percentage of '1' pixels is
        more than 10% of total number of valid pixels
        then ==>  Create Alert in  Alert Model
        '''
        try:
            # pixels_ratio = params['pixels_ratio']
            # print('pixels_ratio', str(pixels_ratio))
            filepath = params['filepath']


            udm_filename = glob.glob(filepath + '*udm_clip.tif')[0]
            weed_alert_array = params['weed_alert_array']
            athena = Athena()
            '''
            Create an Weed Alert in the Alerts data base
            if percentage of '1' pixels is more than 10%
            of total number of valid pixels (as per the udm)
            '''
            is_qualify_create_alert = athena.qualify_create_alert(udm_filename, weed_alert_array)
            if is_qualify_create_alert:
                # fill this parameters
                geojson_file_path=params['geojson_file']
                type=params['type']
                aoi = Aoi.objects.get(id=params['aoi_id'])
                plot=Plots.objects.get(id=aoi.plot.id)
                area = aoi.coordinates
                status=params['status']
                # Create  into Alert table

                Alert.objects.create(alert_date=date.today(), file_path=geojson_file_path,type=type,plot=plot,status =status, notes='',area= area)
                return 1
        except:
            return 'No path for asset '

    def get_red_threshold(self, preparation_stat):
        try:
            max_indices = []

            # Get the latest Record from Threshold table
            latest_record = Thresholds.objects.latest('date_generated')

            quantile_df = pd.read_json(latest_record.quantile_df, keep_default_dates=False)

            quantiles = [0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99]
            quantile_df.index = quantiles

            all_preparation_stat = preparation_stat
            all_asset_in_plot = Aoi.objects.all()

            columns = all_preparation_stat.__dict__
            # if columns('_state'):
            #     columns.__delitem__('_state')
            # if columns('id'):
            #     columns.__delitem__('id')

            columns = columns.keys()

            petaks = pd.DataFrame([[getattr(all_preparation_stat, j) for j in columns]], columns=columns)

            adjust = False
            # (no need for NDWI now)
            veg_indices = ['ndvi']
            # veg_indices = ['ndvi', 'ndvi_80', 'ndvi_95', 'evi']

            # all AOI are here selected from DB
            for plot_id in all_asset_in_plot:
                plot_id = plot_id.id
                if not petaks.loc[petaks['plot_id'] == plot_id].empty:

                    for veg_index in veg_indices:

                        df = petaks.loc[
                            petaks['plot_id'] == plot_id, ['date', 'planted_date', 'variant', 'age_at_obs_months',
                                                           veg_index]]

                        if adjust:
                            for i, row in df.iterrows():
                                df.at[i, veg_index] *= max_indices.at[row['date'], f"{veg_index}_adj"]
                            df.dropna()

                        df = df.set_index('date')

                        # df['rolling_max'] = df[veg_index].rolling('60d', min_periods=1).mean()



                        variant = df['variant'].iloc[0]
                        planed_date = df['planted_date'].iloc[0]
                        min_age = df.age_at_obs_months.min()
                        max_age = df.age_at_obs_months.max()

                        # plot growing stage threshold


                        threshold_high = self.get_threshold(veg_index=veg_index, variant=variant, threshold=0.90,
                                                            quantile_df=quantile_df, ages=df['age_at_obs_months'])

                        # df_temp = df.loc[(df['age_at_obs_months'] <= 12), ['threshold_low', 'threshold_high']]

                        # plot mature stage threshold
                        if adjust:
                            threshold_high = self.get_threshold(veg_index=veg_index, variant=variant,
                                                                threshold=0.90,
                                                                quantile_df=quantile_df,
                                                                ages=df['age_at_obs_months'])

            return threshold_high
        except:
            return False

    def get_threshold(self, variant, quantile_df, threshold, ages, veg_index):
        threshold_values = []
        for age in ages:
            if age >= 1 and age <= 2:
                threshold_values = np.append(threshold_values, quantile_df.at[threshold, f"{veg_index}_{variant}_1_2"])
            elif age >= 3 and age <= 4:
                threshold_values = np.append(threshold_values, quantile_df.at[threshold, f"{veg_index}_{variant}_3_4"])
            elif age >= 5 and age <= 6:
                threshold_values = np.append(threshold_values, quantile_df.at[threshold, f"{veg_index}_{variant}_5_6"])
            elif age >= 7 and age <= 9:
                threshold_values = np.append(threshold_values, quantile_df.at[threshold, f"{veg_index}_{variant}_7_9"])
            elif age >= 10 and age <= 12:
                threshold_values = np.append(threshold_values,
                                             quantile_df.at[threshold, f"{veg_index}_{variant}_10_12"])
            elif age >= 13 and age <= 24:
                threshold_values = np.append(threshold_values,
                                             quantile_df.at[threshold, f"{veg_index}_{variant}_13_24"])
            elif age >= 25 and age <= 48:
                threshold_values = np.append(threshold_values,
                                             quantile_df.at[threshold, f"{veg_index}_{variant}_25_48"])
            else:
                threshold_values = np.append(threshold_values, np.nan)
        return threshold_values

    def polygonize_weedAlertChannel(self, params):
        try:
            weed_alert_channel_band = params['weed_alert_channel_band']
            filepath = params['filepath']

        except:
            return 'weed_alert_channel_band or Filepath not found in Ploginized'

        try:
            c = str.split(filepath, 'storage/')
            filepath = self.ALERT_MEDIA_ROOT
            item_id = str.split(c[1], '/')[0]



            # reading weed alert channel file and getting fetching last band 4
            srcband = weed_alert_channel_band
            # polygonizing the selected band and saving it as a shapefile
            file_name  =item_id+ "_polygonized_weed_alert_channel"
            dst_layername = filepath +file_name  # give it dynamic name accorting to assets
            drv = ogr.GetDriverByName("ESRI Shapefile")
            dst_ds = drv.CreateDataSource(dst_layername + ".shp")
            dst_layer = dst_ds.CreateLayer(dst_layername, srs=None)
            newField = ogr.FieldDefn('MYFLD', ogr.OFTInteger)
            dst_layer.CreateField(newField)
            gdal.Polygonize(srcband, None, dst_layer, 0, [], callback=None)
            dst_ds.Destroy()
            src_ds = None
            # reading the shapefile and converting it into geojson

            reader = shapefile.Reader(
                glob.glob(filepath + file_name+'.shp')[0])  # read with above given dynamic name
            fields = reader.fields[1:]
            field_names = [field[0] for field in fields]
            buffer = []
            for sr in reader.shapeRecords():
                atr = dict(zip(field_names, sr.record))
                geom = sr.shape.__geo_interface__
                buffer.append(dict(type="Feature", \
                                   geometry=geom, properties=atr))
            # writing the geojson file
            geojson = open(filepath + file_name+".json",
                           "w")  # give it dynamic name and place according to assets
            geojson.write(dumps({"type": "FeatureCollection", \
                                 "features": buffer}, indent=2) + "\n")
            geojson.close()
            # delete  .shp .shx .dbf files that used in polygonized process
            files = glob.glob(filepath + '*_polygonized_weed_alert_channel.*')
            for file in files:
                extension = str.split(file,'.')[1]
                if extension !='json':
                    os.unlink(file)
                else:
                    geojson_file = file
                    # geojson_file = str.split(geojson_file, './polygonized_weed_alert_json/')
                    params['geojson_file'] = geojson_file

            return 1
        except:
            return 0

    def upload_asset_s3(self, params):
        try:
            filepath = params['filepath']
            gaia = Gaia()
            # uploading asset to s3
            storage_url = gaia.store_asset_to_s3(filepath)
            asset = params['asset']
            asset.storage_url = storage_url
            asset.save()
            # Remove the local copy of data
            shutil.rmtree(filepath)
            print('successfully download to amazon s3')
            return storage_url
        except:
            return 'Error On Uploading Asset TO s3'
