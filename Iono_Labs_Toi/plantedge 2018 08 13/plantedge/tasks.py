from plantedge.celerypy import celery_app

# Remote Tasks Register
from plantedge.facade.vegetationIndex import\
    activate_clipped_asset,\
    get_clipped_asset,\
    generate_analytic_assets


# Tasks Declaration
@celery_app.task
def ping():
    print('pong')
    return 'pong'
