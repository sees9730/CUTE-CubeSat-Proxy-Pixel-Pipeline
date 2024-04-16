import numpy as np
import lacosmic
from Helper_Function.Helper import readPickleFile, outputPickleFile

def infillFrame(frame, frame_fits):
    '''
    Infill a single frame based on the fixed frame fits

    Inputs = frame (array [n x m], the frame to be infilled),
             frame_fits (array [1 x n], where n is the number of bins)
             
    Ouputs = frame (array [n x m], the input frame after infill)

    The frame will be infilled is the value of the pixel is nan or 
    if the value is less than zero (due to an oversubtraction).
    '''

    for row_idx, row in enumerate(frame):
        for col_idx, val in enumerate(row):
            if np.isnan(val) or val < 0:
                col_fit_idx = col_idx // 25  # Determine the fit column index
                fit = frame_fits[col_fit_idx][0]  # Access the corresponding fit
                val_to_replace = abs(fit[row_idx])  # Determine the value to replace
                frame[row_idx][col_idx] = val_to_replace  # Replace the original value

    return frame

# Get the fixed science-minus-recreated-background and the recreated-background frames from the pickle file
frames_data = readPickleFile('Results/WASP189b_Fixed_Frames_Pre_Infill_v5.pbz2')
fixed_frames = frames_data['Fixed Frames']
background_frames = frames_data['Background Frames']

# Get the fixed frame fits from the pickle file
fits_data = readPickleFile('Results/WASP189b_Fixed_Frames_Fits_v5.pbz2')
fits = fits_data['Fits']

# Infill all the images
final_frames_infilled = [infillFrame(frame.copy(), fits[id]) for id, frame in enumerate(fixed_frames)]

# Remove cosmic rays from final frames using lacosmic
# 'Neighbor threshold' and 'cr threshold' are the modifiable parameters, the others are inherent to the CCD
cr_removed_frames = []
la_cosmic_mask = []
cr_removed_frames, la_cosmic_mask = zip(*[lacosmic.lacosmic(data=frame, contrast=2, cr_threshold=6, neighbor_threshold=4, effective_gain=1.5, readnoise=4.5) for frame in final_frames_infilled])

# Save the final frames
outputPickleFile(cr_removed_frames, 'Results/WASP189b_Final_Frames_v5')