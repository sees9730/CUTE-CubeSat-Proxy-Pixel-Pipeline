import numpy as np 
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import pickle as pkl
from Helper_Function.Helper import doubleGaussCurve, filterArray, readPickleFile, outputPickleFile

def random_params_within_bounds(lower_bound, upper_bound):
    '''Generate random parameters within the given bounds.'''

    return np.random.uniform(lower_bound + 0.0000001, upper_bound - 0.0000001)

def filterAndFitToCurve(x_data, median, big_params, n):
    '''
    Filter the median data, calculate initial parameters and bounds, and find the best fit.
    '''

    # Filter the median array
    col = filterArray(arr = median, hi = 200, lo =-20 )
    indices = np.isfinite(col)

    # Recreate the arrays based only where the filtered array value is finite 
    x_data_int, col_int = x_data[indices], col[indices]

    # Use the ratio to give the 'best' initial parameter guess
    ratio = big_params[0] / big_params[4]
    
    # Define the intial parameter guess and bounds
    g2_p0 = [big_params[0], big_params[1], big_params[2], big_params[3],
             big_params[0] / ratio, big_params[5], big_params[6], big_params[7]]
    adjustment = np.array([60] + [0.000001] * 7)

    # Allow for both peaks to fluctuate
    g2_lbound = np.array(g2_p0) - adjustment
    g2_ubound = np.array(g2_p0) + adjustment

    # Run a random search method to find the best fit coefficients
    best_resid, good_fit, good_params = 10000000, np.array([]), None
    for _ in range(n):
        # Generate the 'random' initial parameters  
        random_p0 = random_params_within_bounds(g2_lbound, g2_ubound)

        # Get the fit coefficients
        popt, _ = curve_fit(doubleGaussCurve, x_data_int, col_int, p0=random_p0, bounds=(g2_lbound, g2_ubound), maxfev=100000)

        # Perform a reality check on the coefficients. If they make sense, continue, else, don't bother.
        if popt[5] < popt[1] + 12:

            # Create a fit with the coefficients
            y_fit = doubleGaussCurve(x_data, *popt)

            # Get the residuals between the fit and the data
            resids = np.nansum(np.abs(y_fit - col))

            # If the new residual is better than the best one, the new residual is the new best one
            if resids < best_resid:

                # Save the fit data if the residual is the best one so far
                best_resid, good_fit, good_params = resids, y_fit, popt

    return good_fit, good_params, col

# Get the final science-minus-recreated-background frames from the pickle file
frames_data = readPickleFile('Results/WASP189b_Final_Frames_Pre_Infill_v5.pbz2')
frames = frames_data['Final Frames']

# Get the best fit parameters for the median frame from the best fit pickle file
fits_data = readPickleFile('Results/WASP189b_Median_Fits_v5.pbz2')
params = fits_data['Params']

# Get a multiple fits for each frame  
fits = []

for id, frame in enumerate(frames):

    # Create an array where each index corresponds to the pixel pixels in the corresponding column 
    cols = frame.T.tolist()

    # Get the columns split into 'x' sized bins so that each bin has 'x' number of columns
    x = 25
    split_cols = [cols[i:i + x] for i in range(0, len(cols), x)]

    # Get the medians of each bin at every row to create a master pix. distribution graph
    medians = [np.nanmedian(chunk, axis=0) for chunk in split_cols]

    # Perform a random search to find the best fit coefficients for each median trace curve 'n' times
    x_data = np.arange(len(frame))
    n = 20
    new_fits = []

    for i, median in enumerate(medians):
        # Perform and save the best fit
        fit_result = filterAndFitToCurve(x_data, median, params[i], n)
        new_fits.append(fit_result)

    fits.append(new_fits)

data = {'Info': f'Fits and parameters of fits for each median curve trace across the rows of the final frames with {x} columns per bin for visit 5 of WASP189b.', 
        'Fits': fits}

outputPickleFile(data = data, filename = 'Results/WASP189b_Final_Frames_Fits_v5')