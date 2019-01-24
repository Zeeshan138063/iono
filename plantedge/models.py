'''
Object entity that stored in databases.
For Other Object, check plantedge/class
'''
import json
# from plantedge.facade.vegetationIndex import *

from django.dispatch import receiver

from django.db.models.signals import post_save

# from plantedge.views import *


from django.db import models
from django.forms import ModelForm
from django.contrib.postgres.fields import JSONField, ArrayField
from simple_history.models import HistoricalRecords
from plantedge.core.modelManager import AoiManager, ClientManager, AssetManager, PlotManager, AlertManager

from smart_selects.db_fields import ChainedForeignKey, \
    ChainedManyToManyField, GroupedForeignKey


# from .core.modelManager import AoiManager

class Client(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    status = models.CharField(max_length=15)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    objects = ClientManager()

    def __str__(self):
        return '{id} <{name}>'.format(**self.__dict__)


class Plots(models.Model):
    id = models.AutoField(primary_key=True)
    client = models.ForeignKey(Client)
    client_plot_ID = models.CharField(max_length=50, blank=True, null=True)
    client_plot_description = models.TextField(blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    STATUS_CHOICES = (
        ('A', 'Active'),
        ('D', 'Disable'),
    )
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')
    description = models.TextField(blank=True, null=True)
    WEED_CHOICES = (
        ('Y', 'Yes'),
        ('N', 'No'),
    )
    weed_enable = models.CharField(max_length=1, choices=WEED_CHOICES, default='Y')
    # weed_enable= models.IntegerField(default=0)
    FOREST_CHOICES = (
        ('Y', 'Yes'),
        ('N', 'No'),
    )
    forest_health_enable = models.CharField(max_length=1, choices=FOREST_CHOICES, default='N')
    VARIANT_CHOICES = (
        ('Epel', 'Epel'),
        ('Acra', 'Acra'),
    )
    variant = models.CharField(max_length=4, choices=VARIANT_CHOICES, default='Epel')

    date_planted = models.DateField(default='2017-01-01')
    creation_time = models.DateTimeField(auto_now=True)
    # forest_health_enable= models.IntegerField(default=0)



    file = models.FileField()

    objects = PlotManager()

    def __str__(self):
        return '{id} <{client_plot_ID}>'.format(**self.__dict__)


# g. constituentAOIs: Foreign Key (from AOI)


class Aoi(models.Model):
    '''
    Representation of 'Area of interest'.
    Each AOI belongs to one client.

    coordinates stored in following format: [[x1, y1], [x2, y2], [xn, yn]]
    '''
    id = models.AutoField(primary_key=True)
    client = models.ForeignKey(Client)
    client_aoi_id = models.CharField(max_length=50)
    status = models.CharField(max_length=15)
    name = models.CharField(max_length=50, blank=True)
    coordinates = ArrayField(
        ArrayField(models.FloatField())
    )
    raw_coordinates = ArrayField(
        ArrayField(models.FloatField())
    )

    plot = models.ForeignKey(Plots, on_delete=models.CASCADE)
    # description = JSONField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    variant = models.TextField(null=True, blank=True)
    date_planted = models.DateField(default='2017-01-01')

    objects = AoiManager()

    # Overwrite the save function  for corresponding model like so:
    # this function only call the superclass save function (which actually saves the change)
    # if there is no pk, e.g. the model instance is new.
    # def save(self, *args, **kwargs):
    #     if self.pk is None:
    #         super(Aoi, self).save(*args, **kwargs)

    def __str__(self):
        return '{id} <{name}>'.format(**self.__dict__)


class Asset(models.Model):
    '''
    Represenation of raw or generated asset.
    Each asset belongs to one AOI.

    storage_url
        => Assets are stored in s3 bucket, hence download it from storage_url.

    note
        => Downloading and reading asset are expensive. Note used to store high level overall data and insight.
    '''
    id = models.AutoField(primary_key=True)
    aoi = models.ForeignKey(Aoi, on_delete=models.CASCADE)
    type = models.CharField(max_length=20)
    date = models.DateTimeField()
    storage_url = models.CharField(max_length=200, blank=True, null=True)
    planet_item_id = models.CharField(max_length=20)
    usability_score = models.FloatField(default=1.1)
    note = JSONField(null=True, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    # preparation_analysis = JSONField(null=True, blank=True)

    objects = AssetManager()

    def __str__(self):
        return '{id}'.format(**self.__dict__)


class Job(models.Model):
    '''
        Representation of job.
        Type of job might be :
            - downloading asset from planet
            - calculating indexes from raw asset
            - uploading asset to s3
            - etc

        params
            => A way to flexibly store parameters while job is queued
    '''
    id = models.AutoField(primary_key=True)
    aoi = models.ForeignKey(Aoi, on_delete=models.CASCADE)
    type = models.CharField(max_length=15)
    status = models.CharField(max_length=15)
    params = JSONField()
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '{id} <{aoi}>'.format(**self.__dict__)


class PreparationStat(models.Model):
    id = models.AutoField(primary_key=True)
    asset_id = models.OneToOneField(Asset, on_delete=models.CASCADE)
    plot_record = models.CharField(max_length=100, blank=True, null=True)
    plot_id = models.IntegerField()  # here plot id --> aoi_id
    plot_id_consol = models.IntegerField()  # here plot_id_console --> plot_id
    date = models.DateField()
    variant = models.CharField(max_length=30, null=True, blank=True)
    planted_date = models.DateField()
    age_at_obs_months = models.IntegerField(blank=True, null=True)
    min_rgb_haze_indicator = models.FloatField(blank=True, null=True)
    likely_haze = models.IntegerField(default=0)
    min_rgb_bad_fraction = models.FloatField(blank=True, null=True)
    likely_cloud = models.IntegerField(default=0)
    ndvi = models.FloatField(blank=True, null=True)
    ndvi_95 = models.FloatField(blank=True, null=True)
    ndvi_80 = models.FloatField(blank=True, null=True)
    ndvi_std = models.FloatField(blank=True, null=True)
    ndvi_count = models.FloatField(default=0)
    gndvi = models.FloatField(blank=True, null=True)
    gndvi_95 = models.FloatField(blank=True, null=True)
    gndvi_80 = models.FloatField(blank=True, null=True)
    gndvi_std = models.FloatField(blank=True, null=True)
    gndvi_count = models.IntegerField(default=0)
    evi = models.FloatField(blank=True, null=True)
    evi_95 = models.FloatField(blank=True, null=True)
    evi_80 = models.FloatField(blank=True, null=True)
    evi_std = models.FloatField(blank=True, null=True)
    evi_count = models.IntegerField(default=0)
    rvi = models.FloatField(blank=True, null=True)
    rvi_95 = models.FloatField(blank=True, null=True)
    rvi_80 = models.FloatField(blank=True, null=True)
    rvi_std = models.FloatField(blank=True, null=True)
    rvi_count = models.IntegerField(default=0)
    dirt = models.FloatField(blank=True, null=True)
    dirt_95 = models.FloatField(blank=True, null=True)
    dirt_std = models.FloatField(blank=True, null=True)
    dirt_count = models.IntegerField(default=0)
    ndwi = models.FloatField(blank=True, null=True)
    ndwi_95 = models.FloatField(blank=True, null=True)
    ndwi_80 = models.FloatField(blank=True, null=True)
    ndwi_20 = models.FloatField(blank=True, null=True)
    ndwi_05 = models.FloatField(blank=True, null=True)
    ndwi_std = models.FloatField(blank=True, null=True)
    ndwi_count = models.IntegerField(default=0)
    ndwi_high_count = models.IntegerField(default=0)

    def __str__(self):
        return '{id} <{plot_id}>'.format(**self.__dict__)


class Thresholds(models.Model):
    id = models.AutoField(primary_key=True)
    date_generated = models.DateField(blank=False)
    quantile_df = JSONField()

    def __str__(self):
        return '{id} <{date_generated}>'.format(**self.__dict__)


ALERT_TYPE_CHOICES = (
    ('Weed', 'Weed'),
    ('Forest_health', 'Forest_health'),
)

STATUS_CHOICES = (
    ('Active', 'Active'),
    ('Verified', 'Verified'),
    ('False_alarm', 'False_alarm'),
)


class Alert(models.Model):
    plot = models.ForeignKey(Plots, on_delete=models.CASCADE)
    alert_date = models.DateField(blank=False)
    type = models.CharField(max_length=14, choices=ALERT_TYPE_CHOICES, default='Weed') #here W is capital in weed
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='Active')
    notes = models.TextField(blank=True, null=True)
    area = JSONField(blank=True, null=True)
    file_path = models.CharField(max_length=250, blank=True, null=True)

    objects = AlertManager()

    def __str__(self):
        return '{id}<{type}>'.format(**self.__dict__)


class Subscriber(models.Model):
    name = models.CharField(max_length=200)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    email = models.EmailField(blank=True, null=True)
    plot = ChainedManyToManyField(Plots,
                                  chained_field="client",
                                  chained_model_field="client")
    plot_alert_json = JSONField(blank=True, null=True)

    def __str__(self):
        return '{id}<{email}>'.format(**self.__dict__)
