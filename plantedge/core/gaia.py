import boto3
import json
import os

import botocore
import rasterio
import requests
import shutil
import time
import zipfile

from django.conf import settings
from xml.dom import minidom


class Gaia():
    '''
    Responsible for generating asset
    '''

    def __init__(self):
        self.__PLANET_API_KEY = getattr(settings, "PLANET_API_KEY", None)
        self._AWS_STORAGE_BUCKET_NAME = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
        self._ACCESS_KEY = getattr(settings, "AWS_ACCESS_KEY_ID", None)
        self._SECRET_KEY = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
        self.__PLANET_AUTH = (self.__PLANET_API_KEY, '')

    def read_band(self, filename):
        '''
        Receive planet's 4band tif file
        Return rasterio object, error message
        '''
        src = rasterio.open(filename)
        return src, None

    def write_band_to_tiff(self, params):
        '''
        Write analysis information into tiff file.

        params:
            - bands: list of value to be writteb
            - profile: information of the desired rasterio files (how many channel, size, etc)
            - filepath & filename: optional; specify the desired output file

        Return: None if success or error message when failed
        '''
        bands = params.get('bands')
        if not bands:
            return 'No Bands Data Found'

        profile = params.get('profile')
        if not profile:
            return 'No Profile Data Found'

        filepath = params.get('filepath')
        if not filepath:
            filepath = ''

        filename = params.get('filename')
        if not filename:
            filename = 'output.tiff'

        with rasterio.open(filepath + filename, 'w', **profile) as dst:
            for i, v in enumerate(bands):
                dst.write(v, (i + 1))

    def parse_xml(self, filename):
        '''
        Receive planet's metadata file (xml)
        '''
        xmldoc = minidom.parse(filename)
        if not xmldoc:
            return None, 'Metadata XML not found'
        return xmldoc, None

    def find_available_asset(self, coordinates, filter_params, item_types):
        '''
        Find list of available asset on planet given the coordinates and filter_parameters
        The found assets need to be activated before download

        Input Parameters:
            - coordinates: Coordinates list of desired AOI
            - filter_params: Constraint of the search. Consisting of:
                - date
                - cloud_threshold
        '''
        filter_config = []

        geometry_filter = {
            "type": "GeometryFilter",
            "field_name": "geometry",
            "config": {
                "type": "Polygon",
                "coordinates": coordinates
            }
        }
        filter_config.append(geometry_filter)

        if filter_params.get('date_filter'):
            date_params = filter_params.get('date_filter')
            date_range_filter = {
                "type": "DateRangeFilter",
                "field_name": "acquired",
                "config": {
                    "gte": date_params.get('start'),
                    "lte": date_params.get('end')
                }
            }
            filter_config.append(date_range_filter)

        if filter_params.get('cloud_threshold'):
            cloud_cover_filter = {
                "type": "RangeFilter",
                "field_name": "cloud_cover",
                "config": {
                    "lte": filter_params.get('cloud_threshold')
                }
            }
            filter_config.append(cloud_cover_filter)

        payload = {
            "interval": "day",
            # "item_types": ["PSScene4Band"],
            "item_types": [item_types],
            "filter": {
                "type": "AndFilter",
                "config": filter_config
            }
        }

        r = requests.post(
            'https://api.planet.com/data/v1/quick-search',
            auth=self.__PLANET_AUTH,
            json=payload
        )
        return r.json()

    def activate_download_udm(self, params):
        '''
        Request Planet to Active UDM only
        Input : filepath where to store asset
        item_id to be download
        '''
        try:
            item_id = params['planet_item_id']
            item_type = "REOrthoTile"
            asset_type = "udm"
            aoi_id = params['aoi_id']


            # create a dir
            filepath = './storage/' + str(aoi_id) + '-'+'udms' + '/'
            if not os.path.exists(filepath):
                os.makedirs(filepath)

            # setup auth
            session = requests.Session()
            session.auth = self.__PLANET_AUTH

            # request an item
            item = \
                session.get(
                    ("https://api.planet.com/data/v1/item-types/" +
                     "{}/items/{}/assets/").format(item_type, item_id))

            if str(item.status_code) == '429':
                return None
            if str(item.status_code) in ['200', '201', '202', '204']:

                # extract the activation url from the item for the desired asset
                item_activation_url = item.json()[asset_type]["_links"]["activate"]

                # request activation
                response = session.post(item_activation_url)

                if str(response.status_code) in ['200', '201', '202', '204']:
                    print('successfully activated')

                    # Let's check on our asset  the udm asset is active,
                    if item.json()[asset_type]["status"] == 'active':
                        # When an asset is active the direct link to download
                        activated_asset_download_link = item.json()[asset_type]["location"]

                        # download the udm to a corresponding folder
                        try:

                            udm = session.get(activated_asset_download_link)
                            output_filename = filepath + str(item_id)+'_'+'udm_clip.tif'
                            with open(output_filename, 'wb') as fd:
                                for chunk in udm.iter_content(chunk_size=128):
                                    fd.write(chunk)
                            print('Done')
                        except:
                            return 0
                    return 1
        except:
            return 0



    def asset_type_to_extension(self,asset_type):
        if (asset_type=='udm'):
            return '_udm_clip.tif'
        elif (asset_type=='analytic_xml'):
            return '_AnalyticMS_metadata_clip.xml'
        else:
            return '_AnalyticMS_clip.tif'

    def activate_clipped_asset(self, aoi_json):
        '''
        Request Planet to generate clipped asset according to AOI
        '''
        url = 'https://api.planet.com/compute/ops/clips/v1'
        auth = self.__PLANET_AUTH
        headers = {
            'Content-Type': 'application/json',
        }
        r = requests.post(url, headers=headers, data=aoi_json, auth=auth)

        if str(r.status_code) == '429':
            return None

        asset_activation = r.json()
        return asset_activation

    def get_clipped_asset(self, asset_activation, output_path):
        '''
        Download clipped asset that have been activated from Planet.

        If the clipped asset is ready: download to the output_path and return 1

        If the clipped asset is not ready: return 0

        if something went wront return -1
        '''
        if not asset_activation.get('_links', None):
            print('asset_activation not valid')
            shutil.rmtree(output_path)
            return -1

        url = asset_activation['_links']['_self']
        auth = self.__PLANET_AUTH
        headers = {
            'Content-Type': 'application/json',
        }

        r = requests.get(url, auth=auth)
        if str(r.status_code) == '429':
            return 0

        clip_state = r.json()
        if clip_state['state'] == 'failed':
            print('get_clipped_asset fail')
            shutil.rmtree(output_path)
            return -1
        elif clip_state['state'] == 'running':
            print(clip_state.get('state'))
            return 0
        elif not clip_state.get('_links'):
            print('get_clipped_asset fail.')
            shutil.rmtree(output_path)
            return -1
        try:
            clip_download_link = clip_state['_links']['results'][0]
            r = requests.get(clip_download_link, auth=auth)

            output_filename = output_path + 'out.zip'
            with open(output_filename, 'wb') as fd:
                for chunk in r.iter_content(chunk_size=128):
                    fd.write(chunk)
        except:
            return -1

        try:
            z = zipfile.ZipFile(output_filename, 'r')
            print('zip file inside gaia', str(z))
            z.extractall(output_path)
            print('z.extractall(output_path) ', str(z))
            z.close()
        except Exception as e:
            print('File is not a zip!')
            shutil.rmtree(output_path)
            return -1

        return 1

    def zip_asset(self, filepath, filename):
        with zipfile.ZipFile(filepath + filename, 'w', zipfile.ZIP_DEFLATED) as z:
            for directory, _, files in os.walk(filepath):
                for f in files:
                    if not f.endswith('.zip'):
                        z.write(os.path.join(directory, f), os.path.relpath(os.path.join(directory, f), filepath),
                                compress_type=zipfile.ZIP_DEFLATED)

    def store_asset_to_s3(self, filepath):
        try:
            filename = str(filepath.split('/')[-2]) + '.zip'
            self.zip_asset(filepath, filename)

            boto = boto3.client('s3', aws_access_key_id=self._ACCESS_KEY, aws_secret_access_key=self._SECRET_KEY)
            # bucket_name = 'plantedge-storage'
            bucket_name = self._AWS_STORAGE_BUCKET_NAME
            boto.upload_file(filepath + filename, bucket_name, filename)

            # shutil.rmtree(filepath)
            return 'https://s3-ap-southeast-1.amazonaws.com/' + bucket_name + '/' + filename
        except:
            return 'failed to upload on amazon s3'

    def create_squared_coordinates(self, coordinates):
        corner_coordinates = self.__get_corner_coordinates(coordinates)
        if not corner_coordinates:
            print('COORDINATE NOT VALID')
            return None

        return [[
            [corner_coordinates.get('min_x'), corner_coordinates.get('min_y'), ],
            [corner_coordinates.get('min_x'), corner_coordinates.get('max_y'), ],
            [corner_coordinates.get('max_x'), corner_coordinates.get('max_y'), ],
            [corner_coordinates.get('max_x'), corner_coordinates.get('min_y'), ],
            [corner_coordinates.get('min_x'), corner_coordinates.get('min_y'), ]
        ]]

    def create_aoi_json(self, coordinates, item_details):
        if not (item_details.get('item_id') and item_details.get('item_type') and item_details.get('asset_type')):
            print('ITEM DETAILS NOT VALID')
            return None

        return json.dumps({
            'aoi': {
                'type': 'Polygon',
                'coordinates': coordinates
            },
            'targets': [{
                'item_id': item_details.get('item_id'),
                'item_type': item_details.get('item_type'),
                'asset_type': item_details.get('asset_type')
            }]
        })

    def __get_corner_coordinates(self, coordinates):
        min_x = None
        min_y = None
        max_x = None
        max_y = None

        for c in coordinates:
            if (not min_x) or (c[0] < min_x):
                min_x = c[0]
            if (not max_x) or (c[0] > max_x):
                max_x = c[0]
            if (not min_y) or (c[1] < min_y):
                min_y = c[1]
            if (not max_y) or (c[1] > max_y):
                max_y = c[1]

        if not (min_x and min_y and max_x and max_y):
            return None

        return {
            'min_x': min_x,
            'max_x': max_x,
            'min_y': min_y,
            'max_y': max_y
        }

    def is_aoi_inside(self, border, aoi):
        corner_coordinates = self.get_corner_coordinates(border)
        if not corner_coordinates:
            return False

        min_x = corner_coordinates.get('min_x')
        max_x = corner_coordinates.get('max_x')
        min_y = corner_coordinates.get('min_y')
        max_y = corner_coordinates.get('max_y')

        for coordinate in aoi:
            x = coordinate[0]
            y = coordinate[1]

            if (x < min_x) or (x > max_x) or (y < min_y) or (y > max_y):
                return False

        return True

    def simplify_coordinates(self, coordinates):
        simplified_coordinates = []
        for i, v in enumerate(coordinates):
            if (i % 2 == 0) or (i == len(coordinates) - 1):
                simplified_coordinates.append(v)
        return simplified_coordinates

    def download_asset_from_s3(self,asset_name):
        try:
            # Amazon S3 client configurations
            AWS_ACCESS_KEY_ID = getattr(settings, "AWS_ACCESS_KEY_ID", None)
            AWS_SECRET_ACCESS_KEY = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
            BUCKET_NAME = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)

            # Boto client configurations
            s3 = boto3.resource('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

            file_names = str.split(asset_name, '/')
            KEY = file_names[4]  # asset name that is going to download from amazon s3


            dir_path = './zip_s3/'
            file_path = dir_path  + KEY  # where to sotre file
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            try:
                s3.Bucket(BUCKET_NAME).download_file(KEY, file_path)
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == "404":
                    print("The object does not exist.")
                else:
                    raise

            return file_path
        except:
            return False

