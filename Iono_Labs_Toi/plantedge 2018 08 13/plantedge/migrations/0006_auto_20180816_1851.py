# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-08-16 11:51
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plantedge', '0005_auto_20180813_2025'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aoi',
            name='coordinates',
            field=django.contrib.postgres.fields.ArrayField(base_field=django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), size=None), size=None),
        ),
        migrations.AlterField(
            model_name='aoi',
            name='raw_coordinates',
            field=django.contrib.postgres.fields.ArrayField(base_field=django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), size=None), size=None),
        ),
    ]
