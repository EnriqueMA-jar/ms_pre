import pyopenms
import plotly.graph_objects as go
import numpy as np
from scipy.signal import find_peaks

# Load the data from the mzML file list and extract retention times, base peaks, m/z values, and index peaks of every file
def load_chromatogram(file_paths, intensity_threshold):
    all_retention_times = []
    all_base_peaks = []
    all_mz_values = []
    all_index_peaks = []
    
    # Analize each file from the list of file paths
    for file_path in file_paths:
        exp = pyopenms.MSExperiment()
        pyopenms.MzMLFile().load(file_path, exp)
        spectra = exp.getSpectra()
        print(f"Number of spectra in {file_path}: {len(spectra)}")

        base_peaks = []
        retention_times = []
        mz_values = []

        # In each file, gets the spectrum data and appends to every list
        for spectrum in spectra:
            if spectrum.getMSLevel() == 1:
                mz_array, intensity_array = spectrum.get_peaks()
                if len(intensity_array) > 0:
                    max_intensity = max(intensity_array)
                    base_peaks.append(max_intensity)
                    max_index = list(intensity_array).index(max_intensity)
                    mz_values.append(mz_array[max_index])
                    retention_times.append(spectrum.getRT())

        index_peaks, _ = find_peaks(
            base_peaks,
            height=intensity_threshold,
            prominence=50,
            distance=10
        )
        all_retention_times.append(retention_times)
        all_base_peaks.append(base_peaks)
        all_mz_values.append(mz_values)
        all_index_peaks.append(index_peaks)
        
    # returns lists with data from every file
    return all_retention_times, all_base_peaks, all_mz_values, all_index_peaks

# Create the chromatograms plots using the data loaded from the files
def create_chromatogram_comparison(fig, all_rt, all_bp, all_mz, all_peaks, file_paths):
    for i, (rt, bp) in enumerate(zip(all_rt, all_bp)):
        fig.add_trace(go.Scatter(
            x=rt,
            y=bp,
            mode='lines',
            name=f'{file_paths[i].split("/")[-1].split(".")[0]}',
            line=dict(width=2),
            hovertemplate=f'<b>{file_paths[i].split("/")[-1].split(".")[0]}</b><br>Time: %{{x:.1f}} s<br>Intensity: %{{y:.0f}}<extra></extra>',
        ))
        for j in all_peaks[i]:
            fig.add_annotation(
                x=all_rt[i][j],
                y=all_bp[i][j],
                text=f"{all_mz[i][j]:.3f}",
                showarrow=False,
                # arrowhead=2,
                # arrowcolor="blue",
                # arrowwidth=1,
                # arrowsize=1,
                ax=0,
                ay=-30,
                font=dict(size=10, color="blue"),
                bgcolor="rgba(255,255,255,0.8)",
                # bordercolor="blue",
                borderwidth=1
            )
            
def render_chromatogram_comparison(file_paths, intensity_threshold):
    all_rt, all_bp, all_mz, all_peaks = load_chromatogram(file_paths, intensity_threshold)
    
    fig = go.Figure()
    fig.update_layout(
        margin=dict(t=0),
        xaxis_title = 'Retention Time (s)',
        yaxis_title = 'Intensity',
        width = 1280,
        height = 450,
        template = 'plotly_white',
        legend = dict(
            orientation = "h",
            yanchor = "bottom",
            y = 1.02,
            xanchor = "right",
            x = 1
        ),
        hovermode = 'x unified'
    )
    create_chromatogram_comparison(fig, all_rt, all_bp, all_mz, all_peaks, file_paths)
    return fig
