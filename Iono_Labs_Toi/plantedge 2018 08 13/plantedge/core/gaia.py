import boto3
import json
import os
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

    def find_available_asset(self, coordinates, filter_params):
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
            "item_types": ["PSScene4Band"],
            "filter": {
                "type": "AndFilter",
                "config": filter_config
            }
        }

        r = requests.post(
            'https://api.planet.com/data/v1/quick-search',
            auth= self.__PLANET_AUTH,
            json=payload
        )
        return r.json()

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

        clip_download_link = clip_state['_links']['results'][0]
        r = requests.get(clip_download_link, auth=auth)

        output_filename = output_path + 'out.zip'
        with open(output_filename, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)

        try:
            z = zipfile.ZipFile(output_filename, 'r')
            z.extractall(output_path)
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
                        z.write(os.path.join(directory, f), os.path.relpath(os.path.join(directory,f), filepath), compress_type = zipfile.ZIP_DEFLATED)

    def store_asset_to_s3(self, filepath):
        filename = str(filepath.split('/')[-2]) + '.zip'
        self.zip_asset(filepath, filename)

        boto = boto3.client('s3')
        bucket_name = 'plantedge-storage'
        boto.upload_file(filepath + filename, bucket_name, filename)

        shutil.rmtree(filepath)

        return 'https://s3-ap-southeast-1.amazonaws.com/' + bucket_name + '/' + filename

    def create_squared_coordinates(self, coordinates):
        corner_coordinates = self.__get_corner_coordinates(coordinates)
        if not corner_coordinates:
            print('COORDINATE NOT VALID')
            return None

        return [[
            [corner_coordinates.get('min_x'), corner_coordinates.get('min_y'),],
            [corner_coordinates.get('min_x'), corner_coordinates.get('max_y'),],
            [corner_coordinates.get('max_x'), corner_coordinates.get('max_y'),],
            [corner_coordinates.get('max_x'), corner_coordinates.get('min_y'),],
            [corner_coordinates.get('min_x'), corner_coordinates.get('min_y'),]
        ]]

    def create_aoi_json(self, coordinates, item_details):
        if not(item_details.get('item_id') and item_details.get('item_type') and item_details.get('asset_type')):
            print('ITEM DETAILS NOT VALID')
            return None

        return json.dumps({
            'aoi' : {
                'type': 'Polygon',
                'coordinates': coordinates
            },
            'targets':[{
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
            'min_x' : min_x,
            'max_x' : max_x,
            'min_y' : min_y,
            'max_y' : max_y
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
        for i,v in enumerate(coordinates):
            if (i % 2 == 0 ) or (i == len(coordinates) -1):
                simplified_coordinates.append(v)
        return simplified_coordinates

