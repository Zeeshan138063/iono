import json

outputdata = {}
outputdata['features'] = []
coordinate = {}
coordinate['coordinates'] = []


with open('/home/zeeshan/Downloads/feat.geojson') as json_file:
    data = json.load(json_file)
    for p in data['features']:
        # print('type: ' + str(p['type']))

        # print('properties: ' + str(p['properties']))
        type = p['geometry']['type']
        print('type',str(type))
        coordinates = p['geometry']['coordinates']
        # print('cordinates' , str(coordinates))
        # for q in coordinates:
        # print('cordinates 0: ' + str(coordinates[0]))
        # print('cordinates 1: ' + str(coordinates[1]))

        # coordinate['coordinates'].append({coordinates[1]})
        # coordinate[1]=coordinates[0]

            # print('geometry 2 : ' + str(q[1]))

        # /print('From: ' + p['from'])
        # print('id',str(p['id']))
        codlist =[]
        # codelist=[coordinates[1],coordinates[0]]
        codelist=coordinates
        print(codelist)

        outputdata['features'].append({

                'coordinates':
                    codelist
            # 'properties': p['properties'],
            # 'website': 'stackabuse.com',
            # 'from': 'Nebraska'
        })
    with open('/home/zeeshan/Downloads/data.json', 'w') as outfile:
        json.dump(outputdata, outfile)