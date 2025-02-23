import numpy as np

def get_indices(blue, green, nir, swir1, swir2):
    np.seterr(divide='ignore', invalid='ignore')
    ndwi = np.where((green + nir) == 0, -1, -(green - nir) / (green + nir)) # FLAG -ve fix
    mndwi = np.where((green + swir1) == 0, -1, -(green - swir1) / (green + swir1)) # FLAG -ve fix
    awei_sh =  (blue + 2.5 * green - 1.5 * (nir + swir1) - 0.25 * swir2)
    awei_nsh = -(4 * (green - swir1) - (0.25 * nir + 2.75 * swir2)) # FLAG -ve fix
    return ndwi, mndwi, awei_sh, awei_nsh
