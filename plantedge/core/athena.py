import numpy
import rasterio


class Athena():
    '''
    Responsible for all calculation and operation
    '''

    def get_reflectance_coefficient(self, xmldoc):
        '''
        Extract reflectance coefficient from xml metadata

        Input:
            xmldoc  => xml metadata from planet

        Output
            coeffs  => list of reflectence coefficient. Each index corespond to its RGB band
            err     => string error messages
        '''
        nodes = xmldoc.getElementsByTagName("ps:bandSpecificMetadata")
        if not nodes:
            return None, 'Tag bandSpecificMetadata not found'

        coeffs = {}
        for node in nodes:
            bn = node.getElementsByTagName("ps:bandNumber")[0].firstChild.data
            if bn in ['1', '2', '3', '4']:
                i = int(bn)
                value = node.getElementsByTagName("ps:reflectanceCoefficient")[0].firstChild.data
                coeffs[i] = float(value)

        if not coeffs:
            return None, 'Tag reflectanceCoefficient not found'

        return coeffs, None

    def calculate_BAI(self, band_data, metadata):
        '''
        Calculating Burnt Area Index from given assets

        Input:
            band_data   => rasterio object from a  planet's analytic item
            metadata    => path to the corresponding metadata

        Output:
            bai         => numpy array with BAI of each pixel
            err         => string error messages
        '''
        band_red = band_data.read(3)
        band_nir = band_data.read(4)

        coeffs, err = self.get_reflectance_coefficient(metadata)
        if err:
            return None, err

        # Multiply by corresponding coefficients
        band_red = band_red * coeffs[3]
        band_nir = band_nir * coeffs[4]

        numpy.seterr(divide='ignore', invalid='ignore')  # Allow division by zero
        bai = 1.0 / (numpy.power((0.1 - band_red), 2) + numpy.power((0.06 - band_nir), 2))
        bai /= bai.max()  # Normalized BAI

        return bai, None

    def calculate_NDWI(self, band_data, metadata):
        '''
        Calculating Normalized Difference Water Index from given assets

        Input:
            band_data   => rasterio object from a  planet's analytic item
            metadata    => path to the corresponding metadata

        Output:
            ndwi        => numpy array with NDWI of each pixel
            err         => string error messages
        '''
        band_green = band_data.read(2)
        band_nir = band_data.read(4)

        coeffs, err = self.get_reflectance_coefficient(metadata)
        if err:
            return None, err

        band_green = band_green * coeffs[2]
        band_nir = band_nir * coeffs[4]

        numpy.seterr(divide='ignore', invalid='ignore')
        ndwi = (band_green.astype(float) - band_nir.astype(float)) / (band_nir + band_green)
        ndwi = numpy.nan_to_num(ndwi)

        return ndwi, None

    def calculate_NDVI(self, band_data, metadata):
        '''
        Calculating Normalized Difference Vegetation Index from given assets

        Input:
            band_data   => rasterio object from a  planet's analytic item
            metadata    => path to the corresponding metadata

        Output:
            ndvi        => numpy array with NDVI of each pixel
            err         => string error messages
        '''
        band_red = band_data.read(3)
        band_nir = band_data.read(4)

        coeffs, err = self.get_reflectance_coefficient(metadata)
        if err:
            return None, err

        band_red = band_red * coeffs[3]
        band_nir = band_nir * coeffs[4]

        numpy.seterr(divide='ignore', invalid='ignore')
        ndvi = (band_nir.astype(float) - band_red.astype(float)) / (band_nir + band_red)
        ndvi = numpy.nan_to_num(ndvi)

        return ndvi, None

    def calculate_RVI(self, band_data, metadata):
        band_red = band_data.read(3)
        band_nir = band_data.read(4)

        coeffs, err = self.get_reflectance_coefficient(metadata)
        if err:
            return None, err

        band_red = band_red * coeffs[3]
        band_nir = band_nir * coeffs[4]

        numpy.seterr(divide='ignore', invalid='ignore')
        rvi = band_nir.astype(float) / band_red.astype(float)

        return rvi, None

    def calculate_GNDVI(self, band_data, metadata):
        band_green = band_data.read(2)
        band_nir = band_data.read(4)

        coeffs, err = self.get_reflectance_coefficient(metadata)
        if err:
            return None, err

        band_green = band_green * coeffs[2]
        band_nir = band_nir * coeffs[4]

        numpy.seterr(divide='ignore', invalid='ignore')
        gndvi = (band_nir.astype(float) - band_green.astype(float)) / (
        band_nir.astype(float) + band_green.astype(float))

        return gndvi, None

    def calculate_MSAVI(self, band_data, metadata):
        band_red = band_data.read(3)
        band_nir = band_data.read(4)

        coeffs, err = self.get_reflectance_coefficient(metadata)
        if err:
            return None, err

        band_red = band_red * coeffs[3]
        band_nir = band_nir * coeffs[4]

        a = (2 * band_nir) + 1
        b = 8 * (band_nir - band_red)

        msavi = (a - numpy.sqrt(numpy.power(a, 2) - b)) / 2

        return msavi, None

    def calculate_DIRT(self, band_data, metadata):
        band_red = band_data.read(3)

        coeffs, err = self.get_reflectance_coefficient(metadata)
        if err:
            return None, err

        band_red = band_red * coeffs[3]

        ndvi, err = self.calculate_NDVI(band_data, metadata)

        beta = 0.12
        DIRT = numpy.sign(beta - band_red) * ndvi

        return DIRT, None

    def calculate_EVI(self, band_data, metadata):
        band_blue = band_data.read(1)
        band_red = band_data.read(3)
        band_nir = band_data.read(4)

        coeffs, err = self.get_reflectance_coefficient(metadata)
        if err:
            return None, err

        band_blue = band_blue * coeffs[1]
        band_red = band_red * coeffs[3]
        band_nir = band_nir * coeffs[4]

        L = 1
        C1 = 6
        C2 = 7.5
        G = 2.5

        EVI = G * ((band_nir - band_red) / (band_nir + (C1 * band_red) - (C2 * band_blue) + L))

        return EVI, None

    def calculate_usability_score(self, band_data):
        '''
        Calculating usability score fro an asset.
        Score is a percentage of pixels which are usable from an asset.

        Input:
            band_data   => rasterio object from a UDM file

        Output:
            score       => percantage of pixels which are usable from an asset
        '''
        udm = band_data.read(1).flatten()
        arr = [0, 0]
        for v in udm:
            if not int(v):
                arr[0] += 1
            else:
                arr[1] += 1
        score = float(arr[0]) / (float(arr[0]) + float(arr[1]))
        return round(score, 2)

    def create_unusable_clip_mask(self, band_data, udm):
        '''
        Creating new udm, combining information from band_data and planet's udm
        '''
        data_sum = band_data.read(1) + band_data.read(2) + band_data.read(3) + band_data.read(4)
        unusable_mask = numpy.where(data_sum, 0, 1)
        unusable_mask = unusable_mask + udm.read(1)
        unusable_mask = numpy.where(unusable_mask, 1, 0)
        return unusable_mask

    def is_hazy(self, band_data, metadata, udm):
        '''
        One approach trying to determine the scenery is hazy or not.

        Assuming the hazy scenery would be whiter (have lower saturation) than usual scenery,
        The average of the minimum RGB value from hazy scenery would be LOWER than non hazy scenery.

        The treshold of hazy or not from this score is widely vary from scenery to scenery
        '''
        coeffs, err = self.get_reflectance_coefficient(metadata)
        r = band_data.read(1).flatten() * coeffs[1]
        g = band_data.read(2).flatten() * coeffs[2]
        b = band_data.read(3).flatten() * coeffs[3]

        arr = []
        for i, v in enumerate(r):
            x = min(r[i], g[i], b[i])
            arr.append(x)

        mean = numpy.ma.array(data=arr, mask=udm.flatten()).mean()
        return mean

    def is_cloudy_udm(self, croped_udm):
        '''
        Calculating the cloudy area for an asset(croped udm) .

        Input:
            filepath of  a UDM file.

        Output:
                 Return  'cloudy_fraction' if cloudy area is > 2 Percent
                 Return 0 if cloudy area is < 2 Percent
                 Return -1 in case of error
        '''
        try:
            with rasterio.open(croped_udm) as src:
                udm = src.read()

            total = numpy.left_shift(udm, 7)
            total = numpy.right_shift(total, 7)
            total = total.size - numpy.sum(total)

            cloudy = numpy.left_shift(udm, 6)
            cloudy = numpy.right_shift(cloudy, 7)
            cloudy = numpy.sum(cloudy)

            cloudy_fraction = round(cloudy / total, 2)
            print('cloudy_fraction  ', str(cloudy_fraction * 100) + ' %')
            if (cloudy_fraction > 0.02):
                return cloudy_fraction
            return 0

        except:
            return -1

    def qualify_create_alert(self, raw_tif, weed_alert):

        """
        :param raw_tif:
        :param weed_alert: ndarray array containg weed_alert
        :return True if percentage of '1' pixels
        is more than 10% of total number of valid pixels:
        else False
        """
        try:
            with rasterio.open(raw_tif) as src:
                udm = src.read()

            total = numpy.left_shift(udm, 7)
            total = numpy.right_shift(total, 7)
            total = total.size - numpy.sum(total)
            ratio = numpy.sum(weed_alert) / total
            if ratio > 0.1:
                return True
            return False
        except:
            return False
