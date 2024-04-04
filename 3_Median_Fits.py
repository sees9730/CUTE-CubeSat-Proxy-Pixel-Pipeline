import numpy as np
from scipy.optimize import curve_fit
from Helper_Function.Helper import readPickleFile, outputPickleFile, doubleGaussCurve

# Get all the final-science-minus-recreated-background frames from the pickle file 
frames_data = readPickleFile('Results/WASP189b_Final_Frames_Pre_Infill_v5.pbz2')
frames = frames_data['Final Frames']

# Create a median master frame where each pixel is the median value
# of all the recreated-background-subtracted frames
med_frame = np.nanmedian(frames, axis = 0)

# Create an array where each index corresponds to the pixel pixels in the corresponding column 
master_cols = med_frame.T.tolist()

# Get the columns split into 'x' sized bins so that each bin has 'x' number of columns
x = 25
split_cols = [master_cols[i:i + x] for i in range(0, len(master_cols), x)]

# Get the medians of each bin at every row to create a master pix. distribution graph
medians = [np.nanmedian(chunk, axis=0) for chunk in split_cols]

# Now fit a double gauss to the medians curves
fits = []
x_data = np.arange(len(med_frame))

# Bound the double gaussian parameters for faster convergence 
g2_p0 = [150, 50, 20, 0, 150, 62, 20, 0]
g2_lbound = (10, 40, 0, -15, 10, 50, 0, -15)
g2_ubound = (400, 70, 50, 15, 400, 80, 50, 15)

# Random search method for a best fit for each curve
n = 10
random_params = np.random.randint(
    np.array(g2_lbound) + 1,  # Add 1 to lower bounds
    np.array(g2_ubound) - 1,  # Subtract 1 from upper bounds
    size=(n, len(g2_lbound))  # Generate a matrix of random parameters
)

x_data = np.arange(len(med_frame))
fits = []

# Perform random search method for a best fit for each curve
for median in medians:
    
    best_resid = 10000 # Set a worst case best residual value
    good_fit = np.array([])

    # Run the RSM for 'n' times
    for params in random_params:
        # Get the fit coefficients
        popt, _ = curve_fit(doubleGaussCurve, x_data, median, p0=params, bounds=(g2_lbound, g2_ubound), maxfev=100000) 
        
        # Perform a reality check on the coefficients. If they make sense, continue, else, don't bother.
        if popt[5] < popt[1] + 12:
            # Create a fit with the coefficients
            y_fit = doubleGaussCurve(x_data, *popt)

            # Get the residuals between the fit and the data
            resids = np.sum(np.abs(y_fit - median))

            # If the new residual is better than the best one, the new residual is the new best one
            if resids < best_resid:
                
                # Save the fit data if the residual is the best one so far
                best_resid = resids
                good_fit = y_fit
                good_params = popt
    
    # In the end, save the absolute best fit based on the 'n' number of runs 
    fits.append([good_fit, good_params])

# Extract the fits and parameters from the array
fit_curves = [chunk[0] for chunk in fits]
params = [chunk[1] for chunk in fits]

data = {'Info': f'Fits and parameters of fits for each median curve trace across the rows of the median frame with {x} columns per bin for visit 5 of WASP189b.', 
        'Fits': fit_curves,
        'Params': params}

# Output the pickle file
outputPickleFile(data = data, filename = 'Results/WASP189b_Median_Fits_v5')