from django.db import models


class AoiManager(models.Manager):
    def get_by_id(self, id):
        try:
            return self.get(id=id)
        except Exception as e:
            return None

    def get_by_client_id(self, client_id):
        try:
            return self.get(client_id=client_id)
        except Exception as e:
            return None

    # def get_by_plot_id(self, plot_id):
    #     try:
    #         return self.get(plot_id=plot_id)
    #     except Exception as e:
    #         return None

    def create_aoi(self, client, params):
        coordinates = params.get('coordinates', None)
        if not coordinates:
            raise ValueError('Coordinates should be in form of [[x1, y1], [x2, y2], [xn, yn]]')
        try:
            aoi = self.create(
                client=client,
                plot=params.get('plot', ''),
                client_aoi_id=params.get('client_aoi_id', ''),
                status=params.get('status', ''),
                name=params.get('name', ''),
                coordinates=params.get('coordinates', None),
                raw_coordinates=params.get('raw_coordinates', None),
                description=params.get('descriptions', ''),
                date_planted=params.get('date_planted', ''),
                variant=params.get('variant', ''),
            )
        except Exception as e:
            return e
        return aoi

    def update_aoi(self, params):
        try:
            id = params.get('id', '')
            aoi = self.get_by_id(id=id)
            aoi.name = params.get('name', '')
            aoi.client_aoi_id = params.get('client_aoi_id', '')
            aoi.descriptions = params.get('description', '')
            aoi.variant = params.get('variant', '')
            aoi.status = params.get('status', '')
            aoi.client = params.get('client', '')
            aoi.save()
        except Exception as e:
            return e
        return True


class AlertManager(models.Manager):
    def get_by_id(self, id):
        try:
            return self.get(id=id)
        except Exception as e:
            return None

    def create_alert(self, params):

        try:
            alert = self.create(
                alert_date=params['alert_date'],
                file_path=params['file_path'],
                type=params['type'],
                plot=params['plot'],
                status=params['status'],
                notes=params['notes'],
                area=params['area'],
            )
        except Exception as e:
            return e
        return alert


class PlotManager(models.Manager):
    def get_by_id(self, id):
        try:
            return self.get(id=id)
        except Exception as e:
            return None

    def get_by_client_id(self, client_id):
        try:
            return self.get(client_id=client_id)
        except Exception as e:
            return None

    def create_plot(self, client, params):
        file = params.get('file', None)
        if not file:
            raise ValueError('Json File Should Exists')
        try:
            print('inside of plan manager   and file name is  -> ' + file)
            True

        except Exception as e:
            return e
        return True


class ClientManager(models.Manager):
    def get_by_id(self, id):
        try:
            return self.get(id=id)
        except Exception as e:
            return None

    def create_client(self, params):
        try:
            client = self.create(
                name=params.get('name', ''),
                status='ACTIVE',
            )
        except Exception as e:
            return e
        return client


class AssetManager(models.Manager):
    def create_asset(self, aoi, params):
        if not params.get('type', None):
            raise ValueError('Type not defined')
        if not params.get('date', None):
            raise ValueError('Date not defined')
        # if not params.get('storage_url', ''):
        #     raise ValueError('Storage url not defined')
        if not params.get('planet_item_id', None):
            raise ValueError('Planet asset id not defined')
        note = params.get('note', {})
        usability_score = params.get('usability_score', 1.1)

        try:
            asset = self.create(
                aoi=aoi,
                type=params['type'],
                date=params['date'],
                storage_url=params['storage_url'],
                planet_item_id=params['planet_item_id'],
                usability_score=usability_score,
                note=note
            )
        except Exception as e:
            return e
        return asset
