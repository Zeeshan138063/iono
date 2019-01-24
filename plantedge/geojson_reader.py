import json


class Reader:
    def json_reader(self):
        outputdata = {}
        outputdata['features'] = []
        coordinate = {}
        coordinate['coordinates'] = []

        with open('/home/zeeshan/Downloads/origonal-data') as json_file:
            data = json.load(json_file)
            for p in data:
                # print('type: ' + str(p['type']))

                # print('properties: ' + str(p['properties']))
                pk = p['pk']
                name = p['fields']['name']
                lat =  p['fields']['lat']
                long =  p['fields']['long']

                # coordinates = p['geometry']['coordinates']
                # print('cordinates' , str(coordinates))
                # for q in coordinates:
                # print('cordinates 0: ' + str(coordinates[0]))
                # print('cordinates 1: ' + str(coordinates[1]))

                # coordinate['coordinates'].append({coordinates[1]})
                # coordinate[1]=coordinates[0]

                # print('geometry 2 : ' + str(q[1]))

                # /print('From: ' + p['from'])
                # print('id',str(p['id']))
                codlist = []
                # coordinates=[lat,long]
                coordin=[float(lat),float(long)]
                # codelist = coordinates
                # print(codelist)
                type = "Point"

                outputdata['features'].append({
                'type':"Feature",
                    "properties": {
                        "name": name,
                        "id":pk
                    },
                    "geometry": {
                        "coordinates": coordin,
                        "type": "Point"
                    },

                    # 'coordinates':
                    #     codelist
                    # 'properties': p['properties'],
                    # 'website': 'stackabuse.com',
                    # 'from': 'Nebraska'
                })

            outputdata["type"] = "FeatureCollection"
            with open('/home/zeeshan/Downloads/data.json', 'w') as outfile:
                json.dump(outputdata, outfile)
