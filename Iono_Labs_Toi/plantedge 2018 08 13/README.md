# Plantedge
---

### Getting Started
---
This program developed in python3.6. To avoid compatibility issue, make sure **you have python3 installed**.

after cloning, run
```
pip install -r requirements.txt
```
if pip cant install the rios. Download it from:
```
https://s3-ap-southeast-1.amazonaws.com/plantedge-storage/rios-1.4.4.zip
```

To run the admin dashboard:
```
python manage.py runserver
```

To run the worker:
```
celery -A plantedge.tasks worker --loglevel=ERROR --concurrency=25
```

Example to queue vegetation index creation (run the celery worker 1st):
```
import json
import numpy
import time

from plantedge.core.athena import Athena
from plantedge.core.gaia import Gaia
from plantedge.facade.vegetationIndex import *
from plantedge.models import *

gaia = Gaia()
f_vegetation_Index = VegetationIndex()

aois = Aoi.objects.filter(id__gte=4, id__lt=234).order_by('id')
for aoi in aois:
    params = {
        'aoi_id': aoi.id,
        'start_date': '2018-02-01',
        'end_date': '2018-12-31',
    }
    print('starting AOI: ' + str(aoi.id))
    f_vegetation_Index.manage_index_creation(params)
    print()
    print()
    time.sleep(10)
```
### Project Structure
___
```
plantedgews/
|____ plantedge/
|________  core/ -> Consist of primary building blocks
|____________ gaia.py -> Responsible for generating AOI and files
|____________ athena.py -> Responsible for all calculation
|____________ theia.py -> Responsible for visualization
|________ facade/ -> Product Level interface that define process flow
|____________ vegetationIndex.py -> The main logic to generate vegetation indexes
|________ admin.py -> generate admin page
|________ models.py -> ORM
|________ tasks.py -> Tasks discovery for celery
```


```
### Authors
---
Created by Kent Wangsawan
