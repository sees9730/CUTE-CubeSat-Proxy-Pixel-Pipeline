import numpy as np 
import pickle as pkl
import matplotlib.pyplot as plt
import csv
import bz2

'''
Functions That Help Visualize Things
'''

def plot(frame, title = '', vmin = 0, vmax = 200):
    '''
    Function that plots a frame using matplotlib.

    Inputs = frame (array [m x n]), title (string), vmin (int), vmax (int)
    '''
    plt.figure() # Create figure 
    plt.title(title) # Set title
    plt.imshow(frame, vmin = vmin, vmax = vmax, origin = 'lower', aspect = 'auto', interpolation = None) # Plot image
    plt.colorbar() # Set colorbar
    plt.ylabel('Y Pixels') # Set y label
    plt.xlabel('X Pixels') # Set x label
    plt.show() # Display

'''
Fitting Functions 
'''

def doubleGaussCurve(xVar, a1, b1, c1, d1, a2, b2, c2, d2):
    '''
    Function that comes up with the values for a double gaussian curve 
    
    Inputs = xVar (array [1 x n], the independent variable where the data is measured), 
             a1 (int, height of the first peak), 
             b1 (int, position of the first peak's center), 
             c1 (int, standard deviation of the first gaussian curve), 
             d1 (int, y-offset for the wings of the first gaussian), 
             a2, b2, c2, d2 are the same as above but for the second gaussian curve.
    
    Outputs = curve (array [1 x n], the two gaussian functions summed together)
    '''
    
    # Create the first gaussian curve
    g1 = a1 * np.exp(-(xVar - b1) ** 2 / (2 * c1 ** 2)) + d1

    # Create the second gaussian curve
    g2 = a2 * np.exp(-(xVar - b2) ** 2 / (2 * c2 ** 2)) + d2

    # Sum the two curves
    curve = g1 + g2

    return curve

def filterArray(arr, hi, lo):
    '''
    Function that eliminates the values in an array if the value is higher
    than [hi] or lower than [lo].

    Inputs = arr (array, [1 x n]), hi (int, upper bound value), lo (int, lower bound value)
    Outputs = new_array (array, [1 x n] filtered array)
    '''
    # Filter the array
    new_array = np.array([val if lo <= val <= hi else np.nan for val in arr])
    return new_array

'''
File Reading Functions
'''

def getTags(csv_file):

    '''
    Get the pixel tags from a csv file

    Outputs = tags (array [1 x n], where each index is a pixel tag)
    '''

    # Output Array
    tags = []
    
    # Reading from CSV
    with open(csv_file, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            tags.append(int(row[0]))

    return tags

def readPickleFile(file):
    '''
    Decompress and read in a compressed pickle file.
    '''

    # Decompress and load data
    data = bz2.BZ2File(file, 'rb')
    data = pkl.load(data)

    return data

def outputPickleFile(data, filename):
    '''
    Output a compressed pickle file. This will take a while to compress, but the 
    file size is much smaller when compared to the regular, uncompressed pickle file.
    '''
    # Compress and write file
    with bz2.BZ2File(filename + '.pbz2', 'w') as f: 
        pkl.dump(data, f)

    return


'''
Pixel-tags/pixel-value related functions
'''

def spectralPix(x_length):
    '''
    Get the pixel tags of the spectral pixels

    Inputs = x_length (int, number of pixels in the x-axis of the image)
    Outputs = pixels_in_area (array [1 x n], where each index is a pixel tag)
    '''

    # Create lower and upper bounds of the area. Line 1 is lower. Line 2 is upper. Values determined experimentally.
    line1 = [(0, 32), (2048, 58)]
    line2 = [(0, 65), (2048, 90)]

    # How many pixels in the x direction
    x = np.arange(x_length)

    # Create the lines
    y1 = lambda x: ((line1[1][1] - line1[0][1]) / x_length) * x + line1[0][1]
    y2 = lambda x: ((line2[1][1] - line2[0][1]) / x_length) * x + line2[0][1]

    # Get y values for each line for each x pixel
    line1 = y1(x)
    line2 = y2(x)

    pixels_in_area = []

    # A pixel tag is a way to determine the location of the pixel with a single value
    # tag = (length of x dimension) * (y-location) + (x-location) 
    # If the x-y pixel combo falls inside the lines, store the tag of the x-y pixel combo
    for x in range(x_length):
        for y in range(x_length):
            if line1[x] <= y <= line2[x]:
                if 50 <= x <= 2000: # Determined experimentally to improve computing time
                    tag = x_length * y + x
                    pixels_in_area.append(tag)
                
    return pixels_in_area

def decoder(tag, x_length):
    '''
    Decode a specific pixel tag.

    Input = tag (int, pixel tag), x_length (int, x axis length of the frame)
    Output = x (int, x index of the pixel), y (int, y index of the pixel)
    '''
    x = int(tag % x_length)
    y = int((tag - x) / x_length)
    return x, y

def getNspecAndSpecDkVals(dk_frames, spec_tags, nspec_tags, outliers = 1, mult = 3):
    '''
    This function generates the pixel value arrays that will be used in the 
    main pixel modeling algorithm. The user can either get the raw values from all the dark frames
    or they can also obtain the raw values minus outliers. The outliers are eliminated based on 
    the median and multiplier of the standard deviation of the pixel values (done by determining the
    value of the 'mult' parameter input).

    Inputs = dk_frames (array [1 x n], where each index of the array is a dark frame),
             spec_tags (array [1 x m], where each index of the array is a spectral pixel tag),
             nspec_tags (array [1 x n], where each index of the array is a non-spectral pixel tag),
             outliers (bool, 1 = keep outliers in pixel value arrays, 0 = remove outliers in pixel value arrays),
             mult (int, where the number indicates the multiplier of the standard deviation used for outlier removal)
    Outputs = spec_vals (array, where each index of the array is the pixel value series throughout all frames for a specific spectral pixel),
              nspec_vals (array, where each index of the array is the pixel value series throughout all frames for a specific non-spectral pixel),

    An outlier will be determined if it meets the following criteria: 
        mult = 3
        sigma = standard_deviation
        if pix_vals_median - sigma * mult < pix_val < pix_vals_median + sigma * mult

    '''

    # Pre-initialize arrays
    nspec_vals = []
    spec_vals = []

    # Get the pixel values of every spectral pixel in every image
    for stag in spec_tags:
        s_vals = []
        # Access every image
        for frame in dk_frames:
            xspec, yspec = decoder(stag, 2048)
            s_vals.append(frame[yspec, xspec])
        spec_vals.append(s_vals)

    # Get the pixel values of every non-spectral pixel in every image
    for nstag in nspec_tags:
        ns_vals = []
        # Access every image
        for frame in dk_frames:
            xnspec, ynspec = decoder(nstag, 2048)
            ns_vals.append(frame[ynspec, xnspec])
        nspec_vals.append(ns_vals)

    # Turn the arrays into numpy arrays for faster computations
    spec_vals = np.array(spec_vals)
    nspec_vals = np.array(nspec_vals)

    if not outliers:

        # Get the median value for every single pixel value throughout all the images
        spec_vals_median = np.nanmedian(spec_vals, axis = 1)
        nspec_vals_median = np.nanmedian(nspec_vals, axis = 1)

        # Get the median value for every single pixel value throughout all the images
        spec_vals_std = np.nanstd(spec_vals, axis = 1)
        nspec_vals_std = np.nanstd(nspec_vals, axis = 1)

        # Recreate the pixel values array except remove the outliers
        spec_vals_no_outliers = []
        nspec_vals_no_outliers = []

        for i in range(len(spec_vals)):
            # Create an array for every pixel
            no_outliers = []
            # Access each individual pixel series of values
            corr_spec_vals = spec_vals[i]
            corr_spec_vals_median = spec_vals_median[i]
            corr_spec_vals_std = spec_vals_std[i]

            # Create a boolean where 1 = inside of the determined band and 0 = outside of the determined band
            bool_arr = (corr_spec_vals < corr_spec_vals_median + mult * corr_spec_vals_std) & (corr_spec_vals > corr_spec_vals_median - mult * corr_spec_vals_std)

            # If the index in the boolean array is 1, keep the value as it is not an outlier.
            # If the index in the boolean array is 0, replace the value with a nan since the value is an outlier.
            for j, boole in enumerate(bool_arr):
                if boole:
                    no_outliers.append(spec_vals[i][j])
                else: 
                    no_outliers.append(np.nan)

            spec_vals_no_outliers.append(no_outliers)

        for i in range(len(nspec_vals)):
            # Create an array for every pixel
            no_outliers = []
            # Access each individual pixel series of values
            corr_nspec_vals = nspec_vals[i]
            corr_nspec_vals_median = nspec_vals_median[i]
            corr_nspec_vals_std = nspec_vals_std[i]

            # Create a boolean where 1 = inside of the determined band and 0 = outside of the determined band
            bool_arr = (corr_nspec_vals < corr_nspec_vals_median + mult * corr_nspec_vals_std) & (corr_nspec_vals > corr_nspec_vals_median - mult * corr_nspec_vals_std)

            # If the index in the boolean array is 1, keep the value as it is not an outlier.
            # If the index in the boolean array is 0, replace the value with a nan since the value is an outlier.
            for j, boole in enumerate(bool_arr):
                if boole:
                    no_outliers.append(nspec_vals[i][j])
                else: 
                    no_outliers.append(np.nan)

            nspec_vals_no_outliers.append(no_outliers)
        
        return spec_vals_no_outliers, nspec_vals_no_outliers

    return spec_vals, nspec_vals
