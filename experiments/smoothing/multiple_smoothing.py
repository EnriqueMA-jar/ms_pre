
import pyopenms as oms
import os

def multiple_smoothing(file_paths, window_length, polyorder):


# Set up Savitzky-Golay filter parameters
    sg_filter = oms.SavitzkyGolayFilter()
    params = sg_filter.getParameters()
    params.setValue("frame_length", window_length)          # Window length (odd: 5, 7, 11, etc.)
    params.setValue("polynomial_order", polyorder)       # Polynomial order (1, 2, 3, etc.)
    sg_filter.setParameters(params)
    output_files = []

    # Process every mzML file in the input directory
    for file in file_paths:
        if file.endswith(".mzML"):
            input_file = file
            output_file = f"{os.path.splitext(file)[0]}_savgol.mzML"

            # Load mzML files
            exp = oms.MSExperiment()
            oms.MzMLFile().load(input_file, exp)

            # Apply Savitzky-Golay filter to each spectrum
            sg_filter.filterExperiment(exp)

            # Save processed files
            oms.MzMLFile().store(output_file, exp)

            output_files.append(output_file)
    return output_files
