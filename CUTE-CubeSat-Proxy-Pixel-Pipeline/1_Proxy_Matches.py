import numpy as np
from mpi4py import MPI
from Helper_Function.Helper import readPickleFile, getTags, outputPickleFile

def getPixData():
    '''
    Get the pixel data from the pre-selected files.

    Inputs = None
    Outputs =  spec_vals_dk (array where each index contains the pixel values for the specific spectral pixel in a dark frame), 
               nspec_vals_dk (array where each index contains the pixel values for the specific non-spectral pixel in a dark frame), 
               spec_tags (array where each index contains a pixel tag for the spectral pixels), 
               nspec_tags (array where each index contains a pixel tag for the non-spectral pixels).

               The order of the tags is directly related to the order of the pixels in the non-tag output arrays.
               i.e. If spec_tags[10] = 10, then the pixel tag for spec_vals_dk is 10.
    '''
    # Get the pixel data from the file
    pix_data = readPickleFile('Data_Files/WASP189b_Nspec_and_Spec_Vals_Dk_Frames.pbz2')

    # Get the spectral pixel tags
    spec_tags = getTags('Data_Files/spec_tags.csv')

    # Get the non-spectral pixel tags
    nspec_tags = getTags('Data_Files/nspec_tags.csv')

    # Process the data
    spec_vals_dk = np.array(pix_data['Spectral Pixels in Dark Frames'])
    nspec_vals_dk = np.array(pix_data['Non-Spectral Pixels in Dark Frames'])

    return spec_vals_dk, nspec_vals_dk, spec_tags, nspec_tags

# Initialize parallelization vars
# rank = number of processor being used
# size = total number of processors being used to run the program
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

if rank == 0:
    # Get the big data arrays. Have the root node handle the data
    spec_vals_dk, nspec_vals_dk, spec_tags, nspec_tags = getPixData()

else:
    # Preallocate for all non root nodes
    spec_vals_dk = None
    nspec_vals_dk = None
    spec_tags = None
    nspec_tags = None

# Get the best match between a single spectral pixel and all its comparisons with non spectral pixels 
def getBestMatch(spec_tag, nspec_tags, medians_arr, stds_arr):
    '''
    Get the best statistical match base on the median and standard deviation of the residuals array.

    Inputs = spec_tag (int, tag of spectral pixel), nspec_tags (array, tags of all non-spectral pixels being compared to the spectral pixel)
             medians_arr (array, array of medians where each index is the median of a residual array), 
             stds_arr (array, array of standard deviations where each index is the standard deviation of a residual array).
    Output = best_match (dict) -> 'Combo' (tuple, the first index is the spectral tag, the second is the non spectral tag, the pair have the best match), 
                                  'Median' (float, the median of the best match)
                                  'STD' (float, the standard deviation of the best match)

    This function will determine the best match based on two filters. First, we look at the medians closest to 0, preferably 0. Of those medians,
    we select the match that has the smallest standard deviation.  
    '''

    # Lists used
    min_median_stds = []
    
    # Get the smallest median value closest to zero and its indices
    min_median = min(medians_arr)
    min_median_idxs = np.argwhere(medians_arr == min_median)

    # For every minimum median value (assumming multiple), find the smallest std of them all
    for i in range(len(min_median_idxs)):
        # Access the index
        idx = min_median_idxs[i][0]
        # Create an array that contains all the stds of all the minimum medians
        min_median_stds.append(stds_arr[idx])

    # Get the index at which the std is the smallest ONLY when comparing across minimum medians
    min_median_std_idx = min_median_stds.index(min(min_median_stds))
    
    # Edge case for there is only one minimum median
    if len(min_median_idxs) == 1:
        # Get the value
        index = min_median_idxs[0][0]
    else:
        # Turn the index value into an int
        index = min_median_idxs[min_median_std_idx][0]
        
    # Finally, get the values for the best match using the best match index 
    min_median = medians_arr[index]
    min_std = stds_arr[index]
    nspec_tag = nspec_tags[index]
    match = (spec_tag, nspec_tag)
    best_match = {'Combo': match, 'Median': min_median, 'STD': min_std}

    return best_match

def getBestMatchLSQ(spec_tag, nspec_tags, residuals, LSQ_list):
    '''
    Function that calculates the best match based on the smallest least squares error.

    Inputs = spec_tag (int, tag of spectral pixel), nspec_tags (array, tags of all non-spectral pixels being compared to the spectral pixel),
             residuals (array, where each index is the residual between the spectral pixel and the corresponding spectral pixel),
             LSQ_list (array, each index is the least squares error for the corresponding spectral and nonspectral pixel matches).
    Outputs = best_match_package (dict) -> 'Combo' (tuple, the first index is the spectral tag, the second is the non spectral tag, the pair have the best match),
                                           'LSQ' (float, value of least squares error for the best match).
    '''

    # Count the number of NaNs in each sub-array
    non_nan_counts = 134 - np.sum(np.isnan(residuals), axis=1)
    
    # Get the normalized LSQs. Do this so that the comparison is fair, even if some pixel values are missing
    norm_LSQ_list = LSQ_list / non_nan_counts

    # Get the index smallest normalized LSQ
    best_residual_idx = np.argmin(norm_LSQ_list)
    
    # Create the best match package
    nspec_tag = nspec_tags[best_residual_idx]
    best_lsq = LSQ_list[best_residual_idx]
    match = (spec_tag, nspec_tag)
    best_match_package = {'Combo': match, 'LSQ': best_lsq}

    return best_match_package

# Broadcast all the necessary data from the root node to the other nodes.
spec_vals = comm.bcast(spec_vals_dk, root = 0)
spec_tags = comm.bcast(spec_tags, root = 0)
nspec_vals = comm.bcast(nspec_vals_dk, root = 0)
nspec_tags = comm.bcast(nspec_tags, root = 0)

# Create the chunks of spectral pixels for each node 
chunks_per_node_spec_vals = np.array_split(spec_vals, size)
chunks_per_node_spec_tags = np.array_split(spec_tags, size)

# Reassign the array for each processor. This way each processor knows what they have to analyze after splitting the load above.
spec_vals_chunks = chunks_per_node_spec_vals[rank]
spec_tags_chunks = chunks_per_node_spec_tags[rank]

# Find residuals and best matc
best_matches_arr = []

for i in range(len(spec_vals_chunks)):
    spec_tag = spec_tags_chunks[i] # Get a specific spectral pixel tag
    residuals = spec_vals_chunks[i] - nspec_vals # Subtract every non spectral values from the specific spectral pixel values 

    '''
    LSQ Method
    '''
    # LSQ Method
    # LSQs = np.nansum(np.square(residuals), axis = 1)
    # best_match = getBestMatchLSQ(spec_tag, nspec_tags, residuals, LSQs)
    
    '''
    Median Method
    '''
    # Median Method
    medians_arr = abs(np.nanmedian(residuals, axis = 1)) # Get the medians of all the residuals
    stds_arr = abs(np.nanstd(residuals, axis = 1)) # Get the standard deviation of all the residuals
    best_match = getBestMatch(spec_tag, nspec_tags, medians_arr, stds_arr) # Compute the best match

    best_matches_arr.append(best_match) # Append to final results list

# Gather all the master_arr arrays to the root node for outputting
gathered = comm.gather(best_matches_arr, root=0)

# Have the root node output the final file
if rank == 0:
    # Create pickle file
    outputPickleFile(gathered, 'Results/WASP189b_Median_Method_Proxy_Matches')