import numpy as np
import matplotlib.pyplot as plt
import os
from PIL import Image, ImageTk
import tkinter as tk

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
        image_array[cloud_positions[:, 0], cloud_positions[:, 1]] = 0
    
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

def prompt_roi(image_array, n):
    """
    Opens a Tkinter window displaying the image (as a numpy array).
    Allows the user to select multiple ROIs by click-and-drag.
    The ROI is automatically saved upon mouse release.
    When done, click the final button to close the window and return a list of ROI coordinates.
    
    Returns:
        A list of ints (ulx, uly, brx, bry) for each ROI.
    """
    # Convert the numpy array to a PIL image
    image = Image.fromarray(image_array)
    image = image.resize((500, 500))  # Resize the image to fit in the window
    width, height = image.size

    rois = []          # List to store confirmed ROI coordinates
    rects = []         # List to store the drawn rectangles
    current_roi = None # To temporarily hold the current ROI coordinates
    current_rect = None
    start_x = start_y = 0

    error_counter = 0
    while error_counter < 2:
        try:
            # Create the Tkinter window and canvas
            root = tk.Tk()
            root.title("Select Multiple ROIs")
            root.resizable(False, False)
            canvas = tk.Canvas(root, width=width, height=height)
            canvas.pack()

            # Display the image on the canvas
            tk_image = ImageTk.PhotoImage(image)
            canvas.create_image(0, 0, anchor="nw", image=tk_image)
            break
        except:
            error_counter += 1
            root = tk.Toplevel()
            root.title("CLOSE THIS WINDOW")
            canvas = tk.Canvas(root, width=width, height=height)
            canvas.pack()
            root.destroy()
            print("Please close any windows that were opened")
            root.mainloop()
    if error_counter >= 2:
        print("Broken prompt_roi function")
        return

    # Create the lines for following the cursor
    vertical_line = canvas.create_line(0, 0, 0, height, fill="red", dash=(4, 2))
    horizontal_line = canvas.create_line(0, 0, width, 0, fill="red", dash=(4, 2))
    
    # Helper function to update the status bar message.
    def set_status(msg):
        status_label.config(text=msg)

    # Event handlers for drawing the ROI rectangle
    def on_button_press(event):
        nonlocal start_x, start_y, current_rect, current_roi
        start_x, start_y = event.x, event.y
        if current_rect is not None:
            canvas.delete(current_rect)  # Delete the previous rectangle if exists
        # Start drawing a rectangle
        current_rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, 
                                               outline="red", width=2)
        current_roi = None  # Reset current ROI

    def on_move_press(event):
        nonlocal current_rect
        # Update the rectangle as the mouse is dragged
        canvas.coords(current_rect, start_x, start_y, event.x, event.y)
        # Update the follower lines by resetting their coordinates
        canvas.coords(vertical_line, event.x, 0, event.x, height)
        canvas.coords(horizontal_line, 0, event.y, width, event.y)

    def on_button_release(event):
        nonlocal current_roi
        # Finalize the ROI on mouse release
        end_x, end_y = event.x, event.y
        ulx = min(start_x, end_x)
        uly = min(start_y, end_y)
        brx = max(end_x, start_x)
        bry = max(end_y, start_y)
        current_roi = (ulx, uly, brx, bry)
        # Auto-save the ROI upon release
        save_roi()

    # Event handler for mouse motion (unpressed button) to update the lines
    def on_mouse_motion(event):
        canvas.coords(vertical_line, event.x, 0, event.x, height)
        canvas.coords(horizontal_line, 0, event.y, width, event.y)

    # Function to save the current ROI automatically
    def save_roi():
        nonlocal rois, current_roi, rects, current_rect
        if len(rois) < n:
            if current_roi is not None:
                # Ensure the ROI coordinates are within bounds
                current_roi = [max(0, int(roi)) for roi in current_roi]
                current_roi = [min(width, int(roi)) for roi in current_roi]

                rois.append(current_roi)
                rects.append(current_rect)  # Keep track of the rectangle reference
                canvas.itemconfig(current_rect, outline="green")
                set_status(("Saved ROI", current_roi))
                # Reset current selection variables for the next ROI
                current_roi = None
                current_rect = None
            else:
                set_status("No region of interest selected")
        else:
            set_status(f"Too many selections, expected: {n}. Overwrite a selection.")

    # Button callback to finish the ROI selection and close the window
    def finish():
        nonlocal rois
        # If there's a ROI in progress, try to save it.
        if current_roi is not None:
            save_roi()
        if len(rois) < n:
            set_status(f"{n - len(rois)} selection(s) remaining")
        else:
            root.destroy()

    def overwrite():
        nonlocal rois, current_roi, current_rect, rects
        # Remove the current drawing if any.
        canvas.delete(current_rect)
        if rois and rects:
            # Remove the last saved ROI and rectangle
            canvas.delete(rects[-1])
            rois.pop()  # Remove the last ROI coordinates
            rects.pop()  # Remove the last rectangle reference
            current_rect = None  # Reset the current rectangle reference
            current_roi = None  # Reset the current ROI coordinates
            set_status("Overwritten ROI")
        else:
            set_status("No regions of interest saved")

    # Bind mouse events to the canvas
    canvas.bind("<ButtonPress-1>", on_button_press)
    canvas.bind("<B1-Motion>", on_move_press)
    canvas.bind("<ButtonRelease-1>", on_button_release)
    canvas.bind("<Motion>", on_mouse_motion)

    # Create button frame and add "Overwrite" and "Finish" buttons only.
    button_frame = tk.Frame(root)
    button_frame.pack(fill=tk.X, pady=10)

    overwrite_button = tk.Button(button_frame, text="Overwrite", command=overwrite)
    overwrite_button.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)

    # Set initial text based on expected number of ROIs.
    finish_button = tk.Button(button_frame, text="Finish", command=finish)
    finish_button.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)
    
    # Create the status bar below the buttons
    status_label = tk.Label(root, text="", bd=1, relief=tk.SUNKEN, anchor=tk.W)
    status_label.pack(fill=tk.X, padx=2, pady=2)

    root.mainloop()
    return rois
