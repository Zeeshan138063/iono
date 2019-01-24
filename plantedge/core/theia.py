import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

class Theia():
    '''
    Responsible for visualization
    '''
    def __init__(self):
        pass

    '''
    Custom Color Map palette; range -1 to 1:
    -1 to -0.01     blue
    -0.01 to 0.2    black
    0.2 to 0.4      red
    0.4 to 0.875    red -> green
    0.875 to 1      green
    '''
    def get_custom_cmap(self, cmap_name):
        '''
        Read the official documentation to understand how it works:
            https://matplotlib.org/examples/pylab_examples/custom_cmap.html
        '''
        custom_map_dict = {
            'NDVI': {
                'red': ((0.0, 0.0, 0.0),
                    (0.49, 0.0, 0.0),
                    (0.5, 0.0, 0.0),
                    (0.65, 0.0, 1.0),
                    (0.7, 1.0, 1.0),
                    (0.875, 0.0, 0.0),
                    (1.0, 0.0, 0.0)),
                'green': ((0.0, 0.0, 0.0),
                    (0.49, 0.0, 0.0),
                    (0.5, 0.0, 0.0),
                    (0.65, 0.0, 0.0),
                    (0.7, 0.0, 0.0),
                    (0.875, 1.0, 1.0),
                    (1.0, 1.0, 0.0)),
                'blue':  ((0.0, 1.0, 1.0),
                    (0.49, 1.0, 0.0),
                    (0.5, 0.0, 0.0),
                    (0.65, 0.0, 0.0),
                    (0.7, 0.0, 0.0),
                    (0.875, 0.0, 0.0),
                    (1.0, 0.0, 0.0))
            },
            'NDWI': {
                'red': ((0.0, 1.0, 1.0),
                    (0.5, 1.0, 1.0),
                    (0.6, 0.0, 0.0),
                    (1.0, 0.0, 0.0)),
                'green': ((0.0, 0.0, 0.0),
                    (0.5, 0.0, 0.0),
                    (0.6, 1.0, 0.0),
                    (1.0, 0.0, 0.0)),
                'blue':  ((0.0, 0.0, 0.0),
                    (0.5, 0.0, 0.0),
                    (0.6, 0.0, 1.0),
                    (1.0, 1.0, 1.0))
            },
            'RVI': {
                'red': ((0.0, 0.0, 0.0),
                    (0.5, 0.0, 1.0),
                    (0.67, 1.0, 1.0),
                    (1.0, 0.0, 0.0)),
                'green': ((0.0, 0.0, 0.0),
                    (0.5, 0.0, 0.0),
                    (0.67, 0.0, 0.0),
                    (1.0, 1.0, 1.0)),
                'blue':  ((0.0, 1.0, 1.0),
                    (0.5, 1.0, 0.0),
                    (0.67, 0.0, 0.0),
                    (1.0, 0.0, 0.0))
            },
            'DIRT': {
                'red': ((0.0, 0.0, 0.0),
                    (0.65, 0.0, 1.0),
                    (0.8, 1.0, 1.0),
                    (1.0, 1.0, 1.0)),
                'green': ((0.0, 1.0, 1.0),
                    (0.65, 1.0, 1.0),
                    (0.8, 0.0, 0.0),
                    (1.0, 0.0, 0.0)),
                'blue':  ((0.0, 0.0, 0.0),
                    (0.65, 0.0, 0.0),
                    (0.8, 0.0, 0.0),
                    (1.0, 0.0, 0.0))
            },
            'MSAVI': {
                'red': ((0.0, 0.0, 0.0),
                    (0.65, 0.0, 1.0),
                    (0.8, 1.0, 1.0),
                    (1.0, 1.0, 1.0)),
                'green': ((0.0, 1.0, 1.0),
                    (0.65, 1.0, 1.0),
                    (0.8, 0.0, 0.0),
                    (1.0, 0.0, 0.0)),
                'blue':  ((0.0, 0.0, 0.0),
                    (0.65, 0.0, 0.0),
                    (0.8, 0.0, 0.0),
                    (1.0, 0.0, 0.0))
            }
        }
        cdict = custom_map_dict.get(cmap_name, None)
        if not cdict:
            cdict = custom_map_dict.get('NDVI')
        return LinearSegmentedColormap('', cdict)

    def create_cmap_asset(self, data, output_path, filename, cmap_name='NDVI', vmin=-1, vmax=1):
        plt.imsave(output_path + filename + '.png',
            data, cmap=self.get_custom_cmap(cmap_name), vmin=vmin, vmax=vmax)
        return

    def create_histogram_asset(self, data, output_path, filename):
        out = plt.hist(data.flatten(), bins='auto', alpha=0.5, label='filename')
        out = plt.savefig(output_path + filename + '.png')
        out = plt.clf()
        return
