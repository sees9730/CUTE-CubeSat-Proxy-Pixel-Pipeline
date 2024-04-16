import numpy as np
from mpi4py import MPI
from Helper_Function.Helper import readPickleFile, getTags, decoder, outputPickleFile

# Initialize parallelization vars
# rank = number of node being used
# size = total number of nodes being used to run the program
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Get the original science frames as well as the frame ids
sc_data = readPickleFile('Data_Files/WASP189b_Sc_Frames.pbz2')
sc_ful_frms, sc_frms_frids = sc_data['Frames'], sc_data['Frame IDs']

# Get the data from the files
proxy_matches_data = readPickleFile('Results/WASP189b_Median_Method_Proxy_Matches.pbz2')
visit_spec_nspec_data = readPickleFile('Data_Files/WASP189b_Nspec_Spec_Data_v5.pbz2')
visit_nspec_vals_sc = visit_spec_nspec_data['v5_nspec_vals_sc']
nspec_tags = getTags('Data_Files/nspec_tags.csv')
spec_tags = getTags('Data_Files/spec_tags.csv')
exclude_tags = getTags('Data_Files/exclude_tags.csv')

# For every node used in the previous part, create individual lists of the matches
# for easier access. Also, filter out hot pixels
spec_tags_ordered_list = []
nspec_tags_ordered_list = []

for i in range(96):
    for j in range(len(proxy_matches_data[i])):
        # Grab the spectral and non-spectral pixel tags from every proxy pixel match in the dictionary
        spec_tag = proxy_matches_data[i][j]['Combo'][0]
        nspec_tag = proxy_matches_data[i][j]['Combo'][1]
        # Filter out hot pixels 
        if spec_tag not in exclude_tags and nspec_tag not in exclude_tags:
            spec_tags_ordered_list.append(spec_tag)
            nspec_tags_ordered_list.append(nspec_tag)

# Create the background images based on the proxy pixel matches
background_images = []
num_frames = len(visit_nspec_vals_sc[0])
frames_per_node = np.array_split(np.arange(0, num_frames), size)

# Precompute the index mapping for nspec_tags
nspec_tag_to_index = {tag: index for index, tag in enumerate(nspec_tags)}

for i in range(frames_per_node[rank][0], frames_per_node[rank][0] + len(frames_per_node[rank])):

    # Create an empty image for each science frame
    bck_im = np.full((100, 2048), np.nan)

    # Fill in all non spectral pixels
    non_spec_coords = [decoder(tag, 2048) for tag in nspec_tags]
    x_coords, y_coords = zip(*non_spec_coords)
    bck_im[y_coords, x_coords] = 0 # Set them to 0

    # Fill in all spectral pixels with their proxy matches
    for j, (nspec_tag, spec_tag) in enumerate(zip(nspec_tags_ordered_list, spec_tags_ordered_list)):

        # Check if the nspec_tag is valid and continue if not
        if nspec_tag not in nspec_tag_to_index:
            continue

        nspec_tag_ind = nspec_tag_to_index[nspec_tag]

        # Check for valid frame index to avoid try-except
        if i < len(visit_nspec_vals_sc[nspec_tag_ind]):
            nspec_val = visit_nspec_vals_sc[nspec_tag_ind][i] # Get the non-spectral pixel value
            x_spec, y_spec = decoder(spec_tag, 2048) # Get the position of the spectral pixel 
            bck_im[y_spec, x_spec] = nspec_val # Place the non-spectral value in the place of a spectral value

    # Every node will create 'frames_per_node' amount of frames
    background_images.append(bck_im)

# Create the fixed images by subtracting the newly created background image from the original science image
fixed_ims = []

# Index the original science frames to create the equivalent background frames
sc_ims_visit = sc_ful_frms[128:189] # Visit 5 indices 

# Have every node create an equal amount of frames (same number of background images created by each node)
sc_ims_per_rank = np.array_split(sc_ims_visit, size)
sc_ims_rank = sc_ims_per_rank[rank]

# Create the fixed-background-subtracted images
for i in range(len(background_images)):

    # Create the empty canvas for the fixed images
    fixed_im = np.zeros_like(sc_ful_frms[0])

    # Go through every pixel tag and replace the pixel with the science value - the background value
    for tag in spec_tags:
        x, y = decoder(tag, 2048)
        fixed_im[y, x] = sc_ims_rank[i][y, x] - background_images[i][y, x]

    fixed_ims.append(fixed_im)

# Package the output of every single node to send it to the root node
out = [fixed_ims, background_images, rank]

# Gather all the output arrays to the root node
gathered = comm.gather(out, root = 0)

# Have the root node output the final file
if rank == 0:
    # Processed the gathered data
    frames = [fixed_frame for frames_per_node in gathered for fixed_frame in frames_per_node[0]]
    back_ims = [fixed_frame for frames_per_node in gathered for fixed_frame in frames_per_node[1]]

    # Set up the data that will be in the final file
    data = {'Info': 'Includes original science minus recreated background frames and the recreated background frames themselves for visit 5 of WASP189b.',
            'Fixed Frames': frames,
            'Background Frames': back_ims}

    # Output the pickle file
    outputPickleFile(data = data, filename = 'Results/WASP189b_Fixed_Frames_Pre_Infill_v5')