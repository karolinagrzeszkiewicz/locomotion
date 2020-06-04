## Copyright Mechanisms Underlying Behavior Lab, Singapore
## https://mechunderlyingbehavior.wordpress.com/

## curve_gen.py is part of the locomotion package comparing animal behaviours, developed
## to support the work discussed in the paper "Computational geometric tools for
## modeling inherent variability in animal behavior" by MT Stamps, S Go, and AS Mathuru.

## This python script contains methods capturing and comparing randomly generated curves
## from curve_gen.py. The mathematical basis for this curve generation is described in
## the paper "Random space and plane curves" by Igor Rivin, which can be accessed here:
## https://arxiv.org/pdf/1607.05239.pdf. This script first extracts the coefficients from
## the files generated by curve_gen.py. It then generates the plane curves with coordinates
## [x(theta), y(theta)] given each step theta, and captures it based on the given framerates
## and pixel density. After capturing these test files, we run robustness tests using the
## locomotion package.


import os
import re
import sys
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.dirname(os.getcwd())))
import locomotion

PATH_TO_DATA_DIRECTORY = os.getcwd() + "/data"
try: # Safety check to ensure that data folder exists, and makes it otherwise.
    os.mkdir(PATH_TO_DATA_DIRECTORY)
except FileExistsError:
    pass

PATH_TO_RES_DIRECTORY = os.getcwd() + "/results"
try: # Safety check to ensure that results folder exists, and makes it otherwise.
    os.mkdir(PATH_TO_RES_DIRECTORY)
except FileExistsError:
    pass

PATH_TO_FIG_DIRECTORY = os.getcwd() + "/figures"
try: # Safety check to ensure that figures folder exists, and makes it otherwise.
    os.mkdir(PATH_TO_FIG_DIRECTORY)
except FileExistsError:
    pass


#static variables used for robustness testing
NUM_CURVES = 2 # This must match the number of curves in the data/curve_data directory.
ZFILL_LEN = int(np.ceil(np.log10(NUM_CURVES)))
NUM_SAMPLES = 50 # Number of samples being tested
SAMP_FILL = int(np.ceil(np.log10(NUM_SAMPLES)))
DEFAULT_START = 0 # Start Time in Minutes
DEFAULT_STOP = 1 # Stop Time in Minutes

########################################################################
#### Functions for getting curve data  ####
########################################################################

def genTrigFun(a_k, b_k):
    """ Generates the Fourier series function f(theta) = sum_0^k (a_k * cos(k * theta) + b_k * sin(k * theta))
        based on the given coefficient sequences.

        :Parameters:
            a_k/b_k : float list. Coefficient sequences of length k.

        :Returns:
            function f(theta), which is defined by f(theta) = sum_0^k (a_k * cos(k * theta) + b_k * sin(k * theta)).
    """

    #define the function we want to return
    def fun_theta (theta):
        #initialise the sum of all k terms
        cum_sum = 0

        #add each term of the function to the sum iteratively
        for i in range(len(a_k)):
            cum_sum += a_k[i] * np.sin(i * theta) + b_k[i] * np.cos(i * theta)
        return cum_sum

    return (fun_theta)

def changePixDensity(num, density):
    """ Converts a coordinate given in mm (num) to the corresponding coordinate in pixels, given the pixel density.

        :Parameters:
            num : float. Coordinate value, in mm.
            density: float. Pixel Density of given file, in px/mm.

        :Returns:
            float. Corresponding coordinate value, in px.
    """
    #initialise return value
    result = 0

    #if our values aren't edge cases, return the corresponding value discretised to the given pixel density
    if not (num == 0 or density == 0 or math.isnan(num) or math.isnan(density)):
        result = math.floor(num * density)

    return result


def genVariables(low, high, n):
    """ Uniformly samples n values from given interval.

        :Parameters:
            low : float. Lower bound of interval.
            high : float. Upper bound of interval.
            n : int. Number of samples.

        :Returns:
            list of n floats. The uniformly sampled values within the interval.
    """
    return list(np.random.uniform(low, high, n))

########################################################################
#### Capturing curves from given frame rate/resolution  ####
########################################################################


def cameraFunc(coeff_path, time_start, time_stop, frame_rate, density, plot=False):
    """ Given a path to coefficients for the plane curve and other necessary information,
        generate curve functions and capture curves as though captured by a camera, in pixels and frames.

        :Parameters:
            coeff_path : string. Path to coefficients_xx.csv for the curve we want to capture.
            time_start, time_stop : floats. Beginning and end times to generate time step increments, in seconds.
            frame_rate : int. Number of frames per second. Used to generate the time step increments, in frames/s.
            density : float. Pixel density. Used to convert from mm to pixels.

        :Returns:
            tuple of dataframes (coordinates, summaryStats). 
            dataframe with columns [X, Y].
    """
    #read in data from the corresponding coefficients csv file
    data = pd.read_csv(coeff_path)

    #get curve number from the path
    curve_no = re.search('coefficients_(\d+)\.csv', coeff_path).group(1)

    #coefficients - each are sequences of length k
    #a_k, b_k are used for x(theta) and c_k, d_k are used for y(theta)
    a_k = data['a_k'].values
    b_k = data['b_k'].values
    c_k = data['c_k'].values
    d_k = data['d_k'].values

    #extras
    #maximum theta value for input into the trig function
    max_theta = data['extras'][0]
    #size is the full dimensions of the camera, whereas x/y min/max/diff are the corresponding
    #dimensions for the bounding box that will contain the curve
    size = data['extras'][1]
    x_min = data['extras'][2]
    x_max = data['extras'][3]
    x_diff = x_max - x_min
    y_min = data['extras'][4]
    y_max = data['extras'][5]
    y_diff = y_max - y_min

    #calculate total frames
    total_frames = (time_stop - time_start) * frame_rate
    #partition the interval [0, max_theta] into total_frame steps
    thetas = max_theta * np.arange(0, 1, 1/total_frames)

    #generate trig functions for x, y coordinates. Each function's domain is theta in [0, 2pi]
    x_fun = genTrigFun(a_k, b_k)
    y_fun = genTrigFun(c_k, d_k)

    #get minimum and maximum x, y coordinates of the graph 
    x_og = x_fun(thetas)
    y_og = y_fun(thetas)
    lower_xlim = min(x_og)
    upper_xlim = max(x_og)
    lower_ylim = min(y_og)
    upper_ylim = max(y_og)

    #transform the coordinates to fit into the generated bounding box
    x_enlarged = []
    y_enlarged = []
    for i in range(0, total_frames):
        x_enlarged.append((x_diff / (upper_xlim - lower_xlim)) * (x_og[i] - lower_xlim) + x_min)
        y_enlarged.append((y_diff / (upper_ylim - lower_ylim)) * (y_og[i] - lower_ylim) + y_min)

    #transform coordinates from mm to px
    x = []
    y = []
    for i in range(0, total_frames):
        x.append(changePixDensity(x_enlarged[i], density))
        y.append(changePixDensity(y_enlarged[i], density))

    if plot:
        # Plots the X, Y coordinates and coefficients of each graph and saves it into the figures folder
        newsize = changePixDensity(size, density)
        plt.subplots_adjust(left = None, bottom = None, right = None, top = None, wspace = 0.5, hspace = 0.5)
        plt.subplot(121)
        plt.plot(x, y)
        plt.title("Coordinate plot for Curve No. " + curve_no)
        plt.axis([0, newsize, 0, newsize])
        plt.subplot(122)
        kSeq = np.arange(0, len(a_k), 1)
        plt.plot(kSeq, a_k)
        plt.plot(kSeq, b_k)
        plt.plot(kSeq, c_k)
        plt.plot(kSeq, d_k)
        plt.title("Coefficients of Curve No. " + curve_no)
        plt.axis([0, 20, -1, 1])
        plt.savefig(PATH_TO_FIG_DIRECTORY + "/plot_" + curve_no)
        plt.clf()

    # Transform data into dataframe
    data = np.transpose(np.array((x, y)))
    coordinates = pd.DataFrame(data, columns = ['X', 'Y'])
    summaryStats = coordinates.describe()
    return coordinates, summaryStats

########################################################################
#### Robustness Testing Setup ####
########################################################################

def captureOneCurve(dat_path, curve_str, test_str, coeff_path,
                    frame_rate, density, control = "False", plot = False):
    """ Given a path to curve data, capture the corresponding curve using cameraFunc,
        and outputs the data to data_path. Then, produce the json that captures the necessary information.

        :Parameters:
            dat_path : str. Absolute file output path.
            curve_str : str. ID of the curve.
            test_str : str. ID of the test.
            coeff_path : str. Absolute file path of the respective curve coefficients.
            frame_rate : int. Framerate of file, in frames/second.
            density : int. Pixel density of file, in pixels/mm.
            control : str. Indicating whether the current test is the control.
                           Valid options = "True", "False". Default = "False".
            plot : bool. If True, will save a plot of the curve. Default = False.
        :Returns:
            jsonItem : dict. Json format, as needed in animal.py.
    """

    # Generate Capture Data
    df, _ = cameraFunc(coeff_path, DEFAULT_START * 60, DEFAULT_STOP * 60, frame_rate, density, plot)
    # Save Capture Data to CSV
    df.to_csv(dat_path)
    jsonItem = {
        "name": "CRV_{}_TEST_{}".format(curve_str, test_str),
        "data_file_location": dat_path,
        "animal_attributes":
            {
                "species": "Magic Scoliosis Fish",
                "exp_type": "MCS",
                "ID": curve_str,
                "control_group": control
            },
            "capture_attributes":
            {
                "dim_x": 100,
                "dim_y": 100,
                "pixels_per_mm": density,
                "frames_per_sec": frame_rate,
                "start_time": DEFAULT_START,
                "end_time": DEFAULT_STOP,
                "baseline_start_time": DEFAULT_START,
                "baseline_end_time": DEFAULT_STOP
            }
    }
    return jsonItem

def captureAllCurves(test_key):
    """ Given a key in the testData dictionary (defined below), it iterates through the curve coefficients
        and captures the curves based on the different variables stored in testData.

        :Parameters:
            test_key : str. Must coincide with a key in testData.

        :Returns:
            None.
            Writes the file Results_variables.json into the results directory.
    """
    # Check / Create directory
    resultPath = PATH_TO_RES_DIRECTORY + "/" + test_key
    try:
        os.mkdir(resultPath)
    except FileExistsError:
        pass
    for curve_no in range(NUM_CURVES):
        curve_str = str(curve_no).zfill(ZFILL_LEN)
        jsonItems = []
        coeff_path = PATH_TO_DATA_DIRECTORY + "/curve_data/coefficients_{}.csv".format(curve_str)
        # Capture Control + Key Check
        try:
            control_fr, control_dens = testData[test_key]["control"]
        except KeyError:
            raise Exception("test_key not in testData")
        control_dat = resultPath + "/CRV_{}_TEST_CTRL.dat".format(curve_str)
        control_json = captureOneCurve(control_dat, curve_str, "CTRL", coeff_path, control_fr, control_dens, "True")
        jsonItems.append(control_json)
        # Capture test curves
        i = 0
        for fr in testData[test_key]["framerates"]:
            for dens in testData[test_key]["densities"]:
                test_str = str(i).zfill(SAMP_FILL)
                dat_path = resultPath + "/CRV_{}_TEST_{}.dat".format(curve_str, test_str)
                jsonItem = captureOneCurve(dat_path, curve_str, test_str, coeff_path, fr, dens)
                jsonItems.append(jsonItem)
        outfilename = resultPath + "/CRV_{}.json".format(curve_str)
        jsonstr = json.dumps(jsonItems, indent = 4)
        with open(outfilename, "w") as outfile:
            outfile.write(jsonstr)
        print("Wrote the information into %s" % outfilename)
    # Save Frame Rate data and Density data
    with open(resultPath + "/Results_variables.json", "w") as outfile:
        varJson = json.dumps(testData[test_key])
        outfile.write(varJson)


def runRobustnessTest(test_key, variables, norm_mode, start_min, end_min):
    """ Calculates the BDD of a test curve to the control curve of the test.
        Saves the results into a csv file in the result directory.

        :Parameters:
            test_key: str. Must coincide with a key in testData,
            variables: list of str. List of variables to use for generating the BDD.
            norm_mode: str. Normalization mode. Options defined in animal.py.
            start_min: float. Starting time in minutes.
            end_min: float. Ending time in minutes.

        :Returns:
            None.
            Writes the file Results_BDD.csv to the result directory.
    """
    NUM_TESTS = len(testData[test_key]["framerates"]) * len(testData[test_key]["densities"])
    results = np.zeros([NUM_CURVES, NUM_TESTS])
    for curve_no in range(NUM_CURVES):
        curve_str = str(curve_no).zfill(ZFILL_LEN)
        json_path = PATH_TO_RES_DIRECTORY + "/{}/CRV_{}.json".format(test_key, curve_str)
        # Load all animals
        animals = locomotion.getAnimalObjs(json_path)
        for a in animals:
            locomotion.trajectory.getCurveData(a)
        # Run BDD against control animal (index 0)
        control = animals[0]
        for a_no, a in enumerate(animals[1:]):
            bdd = locomotion.trajectory.computeOneBDD(a, control, variables,
                                                      start_min, end_min,
                                                      start_min, end_min,
                                                      norm_mode)
            results[curve_no][a_no] = bdd
    output = PATH_TO_RES_DIRECTORY + "/{}/Results_BDD.csv".format(test_key)
    pd.DataFrame(results).to_csv(output, index = False)

################################################################################
### Testing Space
################################################################################

# testData is a dict of dicts that allows us to set the variables for a test, and to save
# the variables in order to replicate the tests in the future.
testData = {
    "FR_test_lower" : {
        "framerates" : list(range(6,24)),
        "densities" : [2],
        "control" : (24, 2)
    },
    "FR_test_higher" : {
        "framerates" : list(range(24,120,2)),
        "densities" : [2],
        "control" : (24, 2)
    },
    "density_test_lower" : {
        "framerates" : [24],
        "densities" : genVariables(0.5, 2, NUM_SAMPLES),
        "control" : (24, 2)
    },
    "density_test_higher" : {
        "framerates" : [24],
        "densities" : genVariables(2, 8, NUM_SAMPLES),
        "control" : (24, 2)
    }
}

# Adjust these variables to the specific test you want to run.
test_name = "FR_test_higher"
test_variables = ['Velocity', 'Curvature']
test_norm_mode = 'spec'

# captureAllCurves(test_name) # Uncomment to recapture curves
runRobustnessTest(test_name, test_variables, test_norm_mode, DEFAULT_START, DEFAULT_STOP)

# df, _ = cameraFunc(PATH_TO_DATA_DIRECTORY + '/curve_data/coefficients_01.csv', DEFAULT_START * 60, DEFAULT_STOP * 60, 24, 2, True)
