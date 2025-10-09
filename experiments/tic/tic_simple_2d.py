import pyopenms as oms
import os
import matplotlib.pyplot as plt


def plot_tic(filename):

    # load the mzML file
    exp = oms.MSExperiment()
    oms.MzMLFile().load(filename, exp)

    # get the espectra list
    spectra = exp.getSpectra()

    # Initialize RT and TIC lists
    retention_times = []
    tic_values = []

    # Iterate through each spectrum MS1 to calculate the TIC
    for spectrum in spectra:
        if spectrum.getMSLevel() == 1:  # Only consider MS1 spectra
            rt = spectrum.getRT()  # Get Retention Time
            intensities = spectrum.get_peaks()[1]  # Get peak intensities
            tic = sum(intensities)  # Sum all the intensities to get TIC

            retention_times.append(rt)
            tic_values.append(tic)

    # Plotting the TIC
    plt.figure(figsize=(10, 6))
    plt.plot(retention_times, tic_values, label='TIC', color='blue')
    plt.xlabel('Retention Time (s)')
    plt.ylabel('Total Ion Current (TIC)')
    plt.title('Chromatogram - Total Ion Current (TIC)')
    plt.grid(True)
    name = os.path.basename(filename).replace('.mzML', '')  # Extract filename without extension
    os.makedirs('static/plots', exist_ok=True)
    plt.savefig(f'static/plots/{name}_tic_plot.png')  # Save the plot in the static/plots directory
    #return plt.show()
    plt.close()  # Close the plot to free memory
