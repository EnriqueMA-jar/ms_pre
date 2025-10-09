import pyopenms as oms
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.colors import sample_colorscale
import matplotlib.cm as cm
import datashader as ds
from datashader.mpl_ext import dsshow
import pandas as pd
from plotly.subplots import make_subplots
from scipy.ndimage import gaussian_filter



# sample file path mzML_samples/Col/Col_1.mzML


def load_and_process_data(file_path):
    
    # load the mzML file
    exp = oms.MSExperiment()
    oms.MzMLFile().load(file_path, exp)
    
    # get the espectra list
    spectra = exp.getSpectra()
    
    #Initialize RT and TIC lists
    rt_list = []
    tic_list = []
    mz_list = []
    
    # Iterate through each spectrum MS1 to calculate the TIC
    for spectrum in spectra:
        if spectrum.getMSLevel() == 1: # Only consider MS1 spectra
            rt = spectrum.getRT()/60 # Get Retention Time
            mz_values= spectrum.get_peaks()[0] # Get m/z values
            mz = np.mean(mz_values) if len(mz_values) > 0 else np.nan
            intensities = spectrum.get_peaks()[1] # Get peak intensities
            tic = sum(intensities) # Sum all the intensities to get TIC
        
            rt_list.append(rt)
            mz_list.append(mz)
            tic_list.append(tic)

    return rt_list, mz_list, tic_list

# Function to create a 3D scatter plot using Plotly
def create_optimized_3d_spikes(rt_list, mz_list, tic_list, 
                                max_points=10000, filter_type='Plasma'):
    """
    Create a 3D visualization with vertical lines (spikes) more efficiently
    than the original method, while maintaining the same aesthetics.
    """
    # Convert lists to arrays for efficient processing
    rt_array = np.array(rt_list)
    mz_array = np.array(mz_list)
    tic_array = np.array(tic_list)
    
    # If too many points, random subsample
    n_points = len(rt_array)
    if n_points > max_points:
        print(f"Subsampling from {n_points} to {max_points} points for improved performance...")
        indexes = np.random.choice(n_points, max_points, replace=False)
        rt_array = rt_array[indexes]
        mz_array = mz_array[indexes]
        tic_array = tic_array[indexes]
    
    # Normalize TIC values for color mapping
    min_tic = tic_array.min()
    max_tic = tic_array.max()
    norm_tic = (tic_array - min_tic) / (max_tic - min_tic)
    
    # Método optimizado: usar un único trazo para todas las líneas
    # Creamos secuencias de puntos con None como separador entre líneas
    x_data = []
    y_data = []
    z_data = []
    colors = []

    # Generate colors based on intensity
    color_values = sample_colorscale(getattr(px.colors.sequential, filter_type), norm_tic)
    
    for i, (rt, mz, tic, color) in enumerate(zip(rt_array, mz_array, tic_array, color_values)):
        # Add basepoints (x, y, 0)
        x_data.extend([rt, rt, None])
        y_data.extend([mz, mz, None]) 
        z_data.extend([0, tic, None])
        colors.extend([color, color, color])  # same color for the spike line and the None
    
    # Create the 3D figure
    fig = go.Figure()
    
    # Add line trace
    fig.add_trace(
        go.Scatter3d(
            x=x_data,
            y=y_data,
            z=z_data,
            mode='lines',
            line=dict(
                color=colors,
                width=2
            ),
            hoverinfo='none',
            showlegend=False
        )
    )
    
    # Adding a dummy trace for the colorbar
    fig.add_trace(
        go.Scatter3d(
            x=[None],
            y=[None],
            z=[None],
            mode='markers',
            marker=dict(
                colorscale=filter_type,
                cmin=min_tic,
                cmax=max_tic,
                colorbar=dict(
                    title='Total Ion Current (TIC)',
                    title_font=dict(color='black'),
                    tickfont=dict(color='black'),
                    thickness=20,
                    len=0.75
                )
            ),
            hoverinfo='none'
        )
    )

    # Improved design config
    fig.update_layout(
        title='Total Ion Current (TIC) 3D Visualization - Vertical Spikes',
        scene=dict(
            xaxis=dict(
                title='Retention Time (min)',
                backgroundcolor='white',
                color='black',
                gridcolor='rgba(0,0,0,0.5)',
                title_font=dict(size=14)
            ),
            yaxis=dict(
                title='m/z',
                backgroundcolor='white',
                color='black',
                gridcolor='rgba(0,0,0,0.2)',
                title_font=dict(size=14)
            ),
            zaxis=dict(
                title='Total Ion Current',
                backgroundcolor='white',
                color='black',
                gridcolor='rgba(0,0,0,0.2)',
                title_font=dict(size=14)
            ),
            aspectmode='manual',
            aspectratio=dict(x=1.5, y=1, z=0.7),
            camera=dict(
                eye=dict(x=1.8, y=-1.8, z=0.9),
                up=dict(x=0, y=0, z=1)
            )
        ),
        template='plotly_white',
        margin=dict(l=0, r=0, t=50, b=0),
        width=650,
        height=500,
        font=dict(
            family="Arial, sans-serif",
            size=12,
            color="black"
        ),
        # Performance options
        uirevision='true'  # Maintains view when updating
    )
    
    return fig
        
        
# def create_2d_heatmap(rt_list, mz_list, tic_list, width=1200, height=800,
#                       colorscale='viridis'):
#     """
#     Creates a more efficient 2D visualization using datashader
#     """
#     # Create the DataFrame
#     df = pd.DataFrame({
#         'RT': rt_list,
#         'mz': mz_list,
#         'Total Ion Current': tic_list
#     })
    
#     df = df.replace([np.inf, -np.inf], np.nan)
#     df = df.dropna(subset=['RT', 'mz', 'Total Ion Current'])
#     df = df[pd.to_numeric(df['mz'], errors='coerce').notnull()]
    
#     # Create a datashader canvas
#     cvs = ds.Canvas(plot_width=width, plot_height=height)
#     agg = cvs.points(df, 'RT', 'mz', ds.mean('Total Ion Current'))
    
#     # Create a datashader figure
#     fig = go.Figure()
    
#     # Convert datashader aggregation to image
#     # Convert Plotly colormap name to matplotlib
#     matplotlib_colormap = colorscale.lower()
#     img = ds.tf.shade(agg, cmap=getattr(cm, matplotlib_colormap))
#     img_data = img.to_pil().tobytes()
    
#     # Create the heatmap
#     fig.add_trace(
#         go.Heatmap(
#             z=agg.values,
#             x=agg.coords['RT'].values,
#             y=agg.coords['mz'].values,
#             colorscale=colorscale,
#             colorbar=dict(
#                 title='Total Ion Current',
#                 title_font=dict(color='white'),
#                 tickfont=dict(color='white'),
#                 thickness=20,
#                 len=0.75
#             )
#         )
#     )
    
#     # Design config
#     fig.update_layout(
#         title='Total Ion Current (TIC) 2D Heatmap',
#         xaxis=dict(
#             title='Retention Time (min)',
#             color='white',
#             gridcolor='rgba(255,255,255,0.1)',
#             title_font=dict(size=14)
#         ),
#         yaxis=dict(
#             title='m/z',
#             color='white',
#             gridcolor='rgba(255,255,255,0.1)',
#             title_font=dict(size=14)
#         ),
#         paper_bgcolor='black',
#         plot_bgcolor='black',
#         margin=dict(l=0, r=0, t=50, b=0),
#         width=600,
#         height=500,
#         font=dict(
#             family="Arial, sans-serif",
#             size=12,
#             color="white"
#         )
#     )
    
#     return fig

    
def create_2d_surface_and_heatmap(rt_list, mz_list, tic_list, width=600, height=500, filter_type='Plasma'): 
    df = pd.DataFrame({'RT': rt_list, 'mz': mz_list, 'Total Ion Current': tic_list})
    df = df.dropna(subset=['RT', 'mz', 'Total Ion Current'])
    
    rt_min, rt_max = df['RT'].min(), df['RT'].max()
    mz_min, mz_max = df['mz'].min(), df['mz'].max()
    
    num_rt_bins = min(300, len(df['RT'].unique()))
    num_mz_bins = min(300, int(len(df['mz'].unique())/10))
    
    rt_edges = np.linspace(rt_min, rt_max, num_rt_bins + 1)
    mz_edges = np.linspace(mz_min, mz_max, num_mz_bins + 1)
    
    H, rt_edges, mz_edges = np.histogram2d(
        df['RT'], df['mz'], bins=[rt_edges, mz_edges], weights=df['Total Ion Current']
    )
    
    H_smooth = gaussian_filter(H, sigma=1)
    H_log = np.log1p(H_smooth)
    
    rt_centers = (rt_edges[:-1] + rt_edges[1:]) / 2
    mz_centers = (mz_edges[:-1] + mz_edges[1:]) / 2
    
    # Only create and return a 2D heatmap
    fig = go.Figure()
    fig.add_trace(
        go.Heatmap(
            z=H_log,
            x=mz_centers,
            y=rt_centers,
            colorscale=filter_type,
            colorbar=dict(title='Log(TIC)'),
            showscale=True
        )
    )
    fig.update_layout(
        title='2D TIC Heatmap',
        template='plotly_white',
        font=dict(color='black'),
        yaxis_title='Retention Time (min)',
        xaxis_title='m/z',
        width=width,
        height=height
    )
    return fig, df

# Obtain all peaks as a DataFrame
# def get_all_peaks(file_path):
#     exp = oms.MSExperiment()
#     oms.MzMLFile().load(file_path, exp)
#     spectra = exp.getSpectra()
#     data = []
#     for spectrum in spectra:
#         if spectrum.getMSLevel() == 1:
#             rt = spectrum.getRT() / 60  # minutes
#             mz_array, intensity_array = spectrum.get_peaks()
#             for mz, intensity in zip(mz_array, intensity_array):
#                 if intensity > 5:  # threshold to filter noise
#                     data.append({'RT': rt, 'mz': mz, 'Total Ion Current': intensity})
#     return pd.DataFrame(data)
def main(file_path, mode, max_points, df, filter):
    # For 2D mode, use all individual peaks, not just spectrum averages
    if mode == '2d':
        # Get all peaks as a DataFrame (each row: RT, mz, intensity)
        # df = get_all_peaks(file_path)
        # Create the combined 2D/3D visualization using the new method
        fig = create_2d_surface_and_heatmap(df['RT'], df['mz'], df['Total Ion Current'], filter_type=filter)
        return fig

    # For 3D and 3d-spikes, keep using the original logic
    rt_list, mz_list, tic_list = load_and_process_data(file_path)
    if mode == '3d':
        fig = create_optimized_3d_spikes(rt_list, mz_list, tic_list,
                                         max_points=max_points, filter_type=filter)
        return fig
    elif mode == '3d-spikes':
        fig = create_optimized_3d_spikes(rt_list, mz_list, tic_list,
                                      max_points=max_points, filter_type=filter)
        return fig

    # Default: return None if mode is not recognized
    return None

    
    # Para visualización rápida 2D (recomendado para exploración)
    # main(file_path, mode='2d')
    
    # Para visualización 3D con líneas verticales (como en el código original)
    
    # Para visualización 3D con puntos (alternativa)
    # main(file_path, mode='3d', max_points=8000)