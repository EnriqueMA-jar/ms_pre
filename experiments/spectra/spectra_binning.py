import pyopenms
import plotly.graph_objects as go
import numpy as np

def binning_spectrum(exp, spectrum_value):
    alert = None
    # Load the mzML file
    # exp = pyopenms.MSExperiment()
    # # file_path = exp
    # # File loaded by frontend
    # pyopenms.MzMLFile().load(file_path, exp)


    # Extract spectra
    spectra = exp.getSpectra()

    # Verify if exists at least one spectrum
    if len(spectra) > 0:
        # Select the spectrum (you can change the index)
        spectrum_index = spectrum_value  # Change this index to select different spectra
        try:
            spectrum = spectra[spectrum_index]
        except IndexError:
            alert = f"Spectrum index {spectrum_index} is out of range."
            return alert, None, spectrum_index

        # Extract m/z and intensity values
        mz_values, intensity_values = spectrum.get_peaks()
    
        # Get additional spectrum information
        rt = spectrum.getRT()  # Retention time
        ms_level = spectrum.getMSLevel()  # MS level
    
        # Binning function
        def binning_peaks(mz_values, intensity_values, bin_width=0.5):
            # Groups nearby peaks using binning - Only keeps the MOST INTENSE peak of each group
            # bin_width: width of the bin in m/z units (default: 0.5)
        
            if len(mz_values) == 0:
                return np.array([]), np.array([])
        
            # Create bins
            min_mz = np.floor(min(mz_values) / bin_width) * bin_width
            max_mz = np.ceil(max(mz_values) / bin_width) * bin_width
            bins = np.arange(min_mz, max_mz + bin_width, bin_width)
        
            # Assign each peak to a bin
            index_bins = np.digitize(mz_values, bins) - 1
        
            # Group each peak to a bin
            unique_bins = np.unique(index_bins)

            # Find the most intense peak in each bin
            binned_mz = []
            binned_intensity = []
        
            for bin_idx in unique_bins:
                mask = index_bins == bin_idx
                peaks_in_bin = mz_values[mask]
                intensities_in_bin = intensity_values[mask]
            
                if len(peaks_in_bin) > 0:
                
                    # Only keep the MOST INTENSE peak (do not sum)
                    max_intensity_idx = np.argmax(intensities_in_bin)
                    representative_mz = peaks_in_bin[max_intensity_idx]
                    max_intensity = intensities_in_bin[max_intensity_idx]
                    binned_mz.append(representative_mz)
                    binned_intensity.append(max_intensity)

            return np.array(binned_mz), np.array(binned_intensity)
    
        # Apply binning
        bin_width = 0.5
        binned_mz, binned_intensity = binning_peaks(mz_values, intensity_values, bin_width)
    
        # CLEAN SPECTRUM WITH BINNING
        fig_annotated = go.Figure()
    
        # Only the spectrum after binning
        fig_annotated.add_trace(go.Scatter(
            x=binned_mz,
            y=binned_intensity,
            mode='lines',
            name=f"Clean Spectrum (Bin: ±{bin_width/2:.2f})",
            line=dict(color='darkblue', width=2),
            fill='tozeroy',
            fillcolor='rgba(0,100,255,0.3)',
            hovertemplate='<b>m/z:</b> %{x:.4f}<br><b>Intensity:</b> %{y:.0f}<extra></extra>'
        ))
    
        fig_annotated.update_layout(
            margin=dict(t=10, l=60, r=60, b=50),
            xaxis_title='m/z',
            yaxis_title='Intensity',
            width=600,
            height=450,
            template='plotly_white',
            hovermode='x unified'
        )
        
        fig_annotated.update_traces(
            hoverlabel=dict(namelength=-1)
        )
        alert = None
        return alert, fig_annotated, spectrum_index

    else:
        alert = "No valid spectrum found."
        return alert, None, spectrum_index

    # return fig_annotated, spectrum_index
