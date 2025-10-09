import pyopenms as oms
import os

def single_smoothing(file_path):
    
    # Create an MSExperiment object and a SavitzkyGolayFilter object
    exp = oms.MSExperiment()
    sg_filter = oms.SavitzkyGolayFilter()
    # Set the filter parameters
    params = sg_filter.getParameters()
    params.setValue("frame_length", 11)
    params.setValue("polynomial_order", 3)
    sg_filter.setParameters(params)
    
    # Load the mzML file
    oms.MzMLFile().load(file_path, exp)
    # Apply the Savitzky-Golay filter 
    sg_filter.filterExperiment(exp)
    
    # Define output path
    output_path = f"{os.path.splitext(file_path)[0]}_savgol.mzML"

    # Save the filtered data to a new mzML file
    oms.MzMLFile().store(output_path, exp)
    return output_path
    






