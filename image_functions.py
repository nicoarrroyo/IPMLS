import numpy as np
import matplotlib.pyplot as plt
import os
from PIL import Image

def compress_image(factor, file_path_s):
    if not isinstance(file_path_s, list):
        with Image.open(file_path_s) as img:
            new_size = (img.width//factor, img.height//factor)
            img = img.resize(new_size)
            image_array = np.array(img)
        return image_array, new_size
    
    else:
        image_arrays = []
        for file_path in file_path_s:
            with Image.open(file_path) as img:
                new_size = (img.width//factor, img.height//factor)
                img = img.resize(new_size)
                image_arrays.append(np.array(img))
        return image_arrays, new_size

def plot_indices(data, sat_n, size, comp, dpi, save_image, res):
    indices = ["NDWI", "MNDWI", "AWEI-SH", "AWEI-NSH"]
    for i, water_index in enumerate(data):
        plt.figure(figsize=(size))
        if sat_n != 2:
            sat_name = "Landsat"
            sat_letter = "L"
        else:
            sat_name = "Sentinel"
            sat_letter = "S"
        plt.title(f"{sat_name} {sat_n} {indices[i]} C{comp} DPI{dpi} R{res}", 
                  fontsize=8)
        
        ax = plt.gca()
        plt.imshow(water_index)
        
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.tick_params(left=False, bottom=False, 
                       labelleft=False, labelbottom=False)
        
        if save_image:
            print(f"saving {indices[i]} image", end="... ")
            plot_name = f"{sat_letter}{sat_n}_{indices[i]}_C{comp}_DPI{dpi}_R{res}.png"
            
            # check for file name already existing and increment file name
            base_name, extension = os.path.splitext(plot_name)
            counter = 1
            while os.path.exists(plot_name):
                plot_name = f"{base_name}_{counter}{extension}"
                counter += 1
            
            plt.savefig(plot_name, dpi=dpi, bbox_inches="tight")
            print(f"complete! saved as {plot_name}")
        
        print(f"displaying {indices[i]} image", end="... ")
        plt.show()
        print(f"{indices[i]} image display complete!")

def upscale_image_array(img_array, factor=2):
    return np.repeat(np.repeat(img_array, factor, axis=0), factor, axis=1)

def get_rgb(blue_path, green_path, red_path, save_image, res, show_image):
    bands = []
    print("creating RGB image", end="... ")
    for path in (blue_path, green_path, red_path):
        with Image.open(path) as img:
            arr = np.array(img, dtype=np.float32)
            bands.append(((arr / arr.max()) * 255).astype(np.uint8))
    rgb_array = np.stack(bands, axis=-1)
    rgb_image = Image.fromarray(rgb_array)
    print("complete!")
    if save_image:
        print("saving image", end="... ")
        rgb_image.save(f"{res}m_RGB.png")
        print("complete!")
    if show_image:
        print("displaying image", end="... ")
        rgb_image.show()
        print("complete!")
    return rgb_array

def mask_sentinel(path, high_res, image_arrays, comp):
    if high_res:
        image_arrays[-1] = upscale_image_array(image_arrays[-1], factor=2)
        image_arrays[-2] = upscale_image_array(image_arrays[-2], factor=2)
        path = path + "MSK_CLDPRB_20m.jp2"
        clouds_array, size = compress_image(comp, path)
        clouds_array = upscale_image_array(clouds_array, factor=2)
    else:
        path = path + "MSK_CLDPRB_60m.jp2"
        clouds_array, size = compress_image(comp, path)
    
    clouds_array = np.where(clouds_array > 50, 100, clouds_array)
    cloud_positions = np.argwhere(clouds_array == 100)
    
    for image_array in image_arrays:
        image_array[cloud_positions[:, 0], cloud_positions[:, 1]] = np.amin(abs(image_array))
    
    return image_arrays

def find_rgb_file(path):
    for item in os.listdir(path):
        full_path = os.path.join(path, item)
        if os.path.isdir(full_path): # if item is a folder
            found_rgb, rgb_path = find_rgb_file(full_path)
            if found_rgb:  
                return True, rgb_path
        else: # if item is a file
            if "RGB" in item and "10m" in item and "bright" in item:
                return True, full_path
    return False, None
