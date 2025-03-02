""" Individual Project Machine Learning Software (IPMLS-25-03) """
""" Update Notes (from previous version IPMLS-25-02)
- earth engine
- optimisations
- output plots improved
- sentinel 2
    - functional index calculation, plot outputs, and plot saving
- machine learning
- cloud masking
- compositing
- separating general water and reservoir water
"""
# %% Start
# %%% External Library Imports
import time
MAIN_START_TIME = time.monotonic()
from PIL import Image
import os
import numpy as np
import threading

# %%% Internal Function Imports
from image_functions import compress_image, plot_image
from calculation_functions import get_indices
from satellite_functions import get_landsat_bands, get_sentinel_bands
from misc_functions import table_print

# %%% Connect with Earth Engine project (ee)
gee_connect = False
if gee_connect:
    from earth_engine_functions import authenticate_and_initialise
    print("connecting to google earth engine", end="... ")
    start_time = time.monotonic()
    thread = threading.Thread(target=authenticate_and_initialise)
    thread.start()
    thread.join(timeout=5)
    
    if thread.is_alive():
        print("Operation timed out after 5 seconds") # prevents slow network connection
    time_taken = time.monotonic() - start_time
    print(f"complete! time taken: {round(time_taken, 2)} seconds")

# %%% General Image and Plot Properties
compression = 15 # 1 for full-sized images, bigger integer for smaller images
dpi = 300 # 3000 for full resolution, below 1000, images become fuzzy
plot_size = (3, 3) # larger plots increase detail and pixel count
save_images = False
# main parent path where all image files are stored
HOME = "C:\\Users\\nicol\\Documents\\UoM\\YEAR 3\\Individual Project\\Downloads"
# %% General Landsat Function
do_l7 = False
do_l8 = False
do_l9 = False

def get_landsat(landsat_number, folder, do_landsat):
    print("===================")
    print(f"||LANDSAT {landsat_number} START||")
    print("===================")
    table_print(compression=compression, dpi=dpi, do_landsat=do_landsat, 
                save_images=save_images, plot_size=plot_size, gee_connect=gee_connect)
    file_paths = []
    images = []
    
    # %%% 1. Establishing Paths, Opening and Resizing Images, and Creating Image Arrays
    print("establishing paths, opening and resizing images, creating image arrays", 
          end="... ")
    start_time = time.monotonic()
    
    satellite = f"\\Landsat {landsat_number}\\"
    path = HOME + satellite + folder
    os.chdir(path)
    
    (landsat_and_sensor, processing_correction_level,
    wrs_path_row, acquisition_date,
    processing_date, collection_number,
    collection_category) = folder.split("_")
    
    if processing_correction_level[1] == "1":
        prefix = folder + "_B"
    else:
        if processing_correction_level[2] == "S":
            prefix = folder + "_SR_B"
        else:
            prefix = folder + "_B"
    
    bands = get_landsat_bands(landsat_number)
    for band in bands:
        file_paths.append(prefix + band + ".TIF")
    
    for file_path in file_paths:
        images.append(Image.open(file_path))
    
    width, height = images[1].size
    
    images, image_arrays, size = compress_image(compression, width, height, images)
    
    time_taken = time.monotonic() - start_time
    print(f"complete! time taken: {round(time_taken, 2)} seconds")
    
    # %%% 2. Masking Clouds
    print("masking clouds", end="... ")
    start_time = time.monotonic()
    
    qa = Image.open(folder + "_QA_PIXEL.TIF")
    qa_array = np.array(qa)
    qa_array = np.where(qa_array == 1, 0, qa_array / 2**16) # FLAG div 2**16 because 
    # it is being shown not with the gradient plot but with regular imshow pltshow
    
    import matplotlib.pyplot as plt
    plt.imshow(qa_array)
    plt.show()
    
    time_taken = time.monotonic() - start_time
    print(f"complete! time taken: {round(time_taken, 2)} seconds")
    
    # %%% 3. Calculating Water Indices
    print("populating water index arrays", end="... ")
    start_time = time.monotonic()
    
    blue, green, nir, swir1, swir2 = image_arrays
    ndwi, mndwi, awei_sh, awei_nsh = get_indices(blue, green, nir, swir1, swir2)
    indices = [ndwi, mndwi, awei_sh, awei_nsh]
    
    time_taken = time.monotonic() - start_time
    print(f"complete! time taken: {round(time_taken, 2)} seconds")
    
    # %%% 4. Showing Images
    if do_landsat:
        minimum = -1
        maximum = 1
        if save_images:
            print("displaying and saving water index images...")
        else:
            print("displaying water index images...")
        start_time = time.monotonic()
        plot_image(indices, landsat_number, plot_size, 
                   minimum, maximum, compression, dpi, save_images)
        time_taken = time.monotonic() - start_time
        print(f"complete! time taken: {round(time_taken, 2)} seconds")
    
    return indices
# %% General Sentinel Function
do_s2 = True

def get_sentinel(sentinel_number, folder, do_s2):
    print("====================")
    print(f"||SENTINEL {sentinel_number} START||")
    print("====================")
    table_print(compression=compression, dpi=dpi, do_sentinel=do_s2, 
                save_images=save_images, plot_size=plot_size, gee_connect=gee_connect)
    file_paths = []
    images = []
    
    # %%% 1. Establishing Paths, Opening and Resizing Images, and Creating Image Arrays
    print("establishing paths, opening and resizing images, creating image arrays", 
          end="... ")
    start_time = time.monotonic()
    
    satellite = f"\\Sentinel {sentinel_number}\\"
    path = HOME + satellite + folder + "\\GRANULE"
    
    subdirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
    if len(subdirs) == 1:
        path = (f"{path}\\{subdirs[0]}\\")
        os.chdir(path)
    else:
        print("Too many subdirectories in 'GRANULE':", len(subdirs))
        return
    
    path = (path + "\\IMG_DATA\\R20m\\")
    
    (sentinel_name, instrument_and_product_level, datatake_start_sensing_time, 
     processing_baseline_number, relative_orbit_number, tile_number_field, 
     product_discriminator_and_format) = folder.split("_")
    prefix = (f"{tile_number_field}_{datatake_start_sensing_time}_B")
    bands = get_sentinel_bands(sentinel_number)
    
    for band in bands:
        file_paths.append(path + prefix + band + "_20m.jp2")
    
    for file_path in file_paths:
        images.append(Image.open(file_path))
    
    width, height = images[1].size
    
    images, image_arrays, size = compress_image(compression, width, height, images)
    
    time_taken = time.monotonic() - start_time
    print(f"complete! time taken: {round(time_taken, 2)} seconds")
    
    # %%% 2. Masking Clouds
    print("masking clouds", end="... ")
    start_time = time.monotonic()
    
    path = HOME + satellite + folder + "\\GRANULE\\" + subdirs[0] + "\\QI_DATA\\"
    
    qa = Image.open(path + "MSK_CLDPRB_20m.jp2") # pixel value from 0 - 100
    # representing the probability that a given pixel is a cloud
    qa, qa_array, size = compress_image(compression, width, height, qa)
    
    import matplotlib.pyplot as plt # troubleshooting
    plt.imshow(qa_array[0]) # troubleshooting
    plt.show() # troubleshooting
    
    time_taken = time.monotonic() - start_time
    print(f"complete! time taken: {round(time_taken, 2)} seconds")
    
    # %%% 3. Calculating Water Indices
    print("populating water index arrays", end="... ")
    start_time = time.monotonic()
    
    blue, green, nir, swir1, swir2 = image_arrays
    ndwi, mndwi, awei_sh, awei_nsh = get_indices(blue, green, nir, swir1, swir2)
    indices = [ndwi, mndwi, awei_sh, awei_nsh]
    
    time_taken = time.monotonic() - start_time
    print(f"complete! time taken: {round(time_taken, 2)} seconds")
    
    # %%% 4. Showing Images
    if do_s2:
        minimum = -1
        maximum = 1
        if save_images:
            print("displaying and saving water index images...")
        else:
            print("displaying water index images...")
        start_time = time.monotonic()
        plot_image(indices, sentinel_number, plot_size, 
                   minimum, maximum, compression, dpi, save_images)
        time_taken = time.monotonic() - start_time
        print(f"complete! time taken: {round(time_taken, 2)} seconds")
    
    return indices
# %% Running Functions    
"""
Landsat 7 has only one Short-Wave Infrared (SWIR) band, which means that Autom-
ated Water Extraction Index (AWEI) cannot be properly calculated. 
The AWEI is calculated anyway, however please note that the SWIR2 band is repl-
aced with the Mid-Wave Infrared (MIR) band. 
"""
if do_l7:
    l7_indices = get_landsat(landsat_number=7, 
                             folder="LE07_L2SP_201023_20000619_20200918_02_T1", 
                             do_landsat=do_l7)

"""
Landsat 8 has no Mid-Wave Infrared (MIR) band. MNDWI is calculated with SWIR2, 
which is the correct method. 
"""
if do_l8:
    l8_indices = get_landsat(landsat_number=8, 
                             folder="LC08_L2SP_201024_20241120_20241203_02_T1", 
                             do_landsat=do_l8)

"""
Landsat 9 has the same band imagers as Landsat 8, meaning that it lacks the MIR
band. 
"""
if do_l9:
    l9_indices = get_landsat(landsat_number=9, 
                             folder="LC09_L1TP_201023_20241011_20241011_02_T1", 
                             do_landsat=do_l9)

"""
Sentinel 2 has varying resolution bands, with Blue (2), Green (3), Red (4), and 
NIR (8) having 10m spatial resolution, while SWIR 1 (11) and SWIR 2 (12) have 
20m spatial resolution. There is no MIR band, so MNDWI is calculated correctly 
with the SWIR2 band. 
"""
if do_s2:
    s2_indices = get_sentinel(sentinel_number=2, 
                              folder=("S2C_MSIL2A_20250301T111031_N0511_R137"
                                  "_T31UCU_20250301T152054.SAFE"), 
                                  do_s2=do_s2)
# %% Final
TOTAL_TIME = time.monotonic() - MAIN_START_TIME
print(f"total time taken for all processes: {round(TOTAL_TIME, 2)} seconds")
