# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-09-04 07:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plantedge', '0010_auto_20180904_1427'),
    ]

    operations = [
        migrations.AlterField(
            model_name='plots',
            name='file',
            field=models.FileField(upload_to='input_geojson/'),
        ),
    ]
