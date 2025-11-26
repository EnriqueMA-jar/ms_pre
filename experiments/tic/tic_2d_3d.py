from flask import session
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
from scipy.interpolate import griddata

from experiments.summary import summary


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
    
    # Crear DataFrame sin guardar en sesión (eso lo hace el endpoint)
    df_summary = pd.DataFrame({
        'RT': rt_list, 
        'mz': mz_list, 
        'TIC': tic_list, 
        'filter_type': ['Plasma'] * len(rt_list)
    })

    return df_summary


# Function to create a 3D scatter plot using Plotly
def create_optimized_3d_spikes(df_summary, max_points=10000):
    """
    Crea una gráfica 3D tipo superficie (como 3d_personalizado.py) pero usando filter_type como colorscale.
    """
    import numpy as np
    import plotly.graph_objects as go

    # Convertir listas a arrays de numpy
    rt_array = np.array(df_summary['RT'])
    mz_array = np.array(df_summary['mz'])
    tic_array = np.array(df_summary['TIC'])

    # Si hay demasiados puntos, muestrea aleatoriamente
    n_points = len(rt_array)
    if n_points > max_points:
        idx = np.random.choice(n_points, max_points, replace=False)
        rt_array = rt_array[idx]
        mz_array = mz_array[idx]
        tic_array = tic_array[idx]

    # Crear bins para agrupar los datos
    rt_bins = 100
    mz_bins = 100

    # Crear histograma 2D
    heatmap, xedges, yedges = np.histogram2d(
        rt_array,
        mz_array,
        bins=[rt_bins, mz_bins],
        weights=tic_array
    )

    # Crear malla para la superficie
    X, Y = np.meshgrid(xedges[:-1], yedges[:-1])

    # Generar superficie 3D con Plotly
    fig = go.Figure(data=[go.Surface(
        x=X,
        y=Y,
        z=heatmap.T,
        colorscale=df_summary['filter_type'].iloc[0],
        colorbar=dict(
            title=dict(
                text='Intensity',
                font=dict(size=14)
            ),
            tickfont=dict(size=12)
        ),
        hovertemplate=(
            '<span style="font-size: 14px; font-weight: bold;">LC-MS Data Point</span><br>' +
            '<b>Retention Time</b>: %{x:.2f} min<br>' +
            '<b>m/z</b>: %{y:.4f} Da<br>' +
            '<b>Intensity</b>: %{z:.0f}<br>' +
            '<extra></extra>'
        ),
        lighting=dict(
            ambient=0.8,
            diffuse=0.8,
            fresnel=0.1,
            specular=0.5,
            roughness=0.5
        ),
        lightposition=dict(x=100, y=100, z=1000)
    )])

    fig.update_layout(
        # title=dict(
        #     text='3D Surface Plot - LC-MS Data',
        #     x=0.5,
        #     font=dict(size=20, color='darkblue')
        # ),
        margin=dict(l=10, r=10, t=30, b=10),
        scene=dict(
            xaxis=dict(
                title='Retention Time (min)',
                title_font=dict(size=16),
                tickfont=dict(size=12),
                gridcolor='lightgray',
                backgroundcolor='rgb(250, 250, 250)'
            ),
            yaxis=dict(
                title='m/z',
                title_font=dict(size=16),
                tickfont=dict(size=12),
                gridcolor='lightgray',
                backgroundcolor='rgb(250, 250, 250)'
            ),
            zaxis=dict(
                title='Intensity',
                title_font=dict(size=16),
                tickfont=dict(size=12),
                gridcolor='lightgray',
                backgroundcolor='rgb(250, 250, 250)'
            ),
            bgcolor='rgb(255, 255, 255)',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5)
            )
        ),
        width=700,
        height=550
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

    
def create_2d_surface_and_heatmap(df_summary): 
    
    
    rt_min, rt_max = df_summary['RT'].min(), df_summary['RT'].max()
    mz_min, mz_max = df_summary['mz'].min(), df_summary['mz'].max()
    
    num_rt_bins = min(300, len(df_summary['RT'].unique()))
    num_mz_bins = min(300, int(len(df_summary['mz'].unique())/10))
    
    rt_edges = np.linspace(rt_min, rt_max, num_rt_bins + 1)
    mz_edges = np.linspace(mz_min, mz_max, num_mz_bins + 1)
    
    H, rt_edges, mz_edges = np.histogram2d(
        df_summary['RT'], df_summary['mz'], bins=[rt_edges, mz_edges], weights=df_summary['TIC']
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
            colorscale=df_summary['filter_type'].iloc[0],
            colorbar=dict(title='Log(TIC)'),
            showscale=True
        )
    )
    fig.update_layout(
        # title='2D TIC Heatmap',
        margin=dict(l=10, r=10, t=30, b=10),
        template='plotly_white',
        font=dict(color='black'),
        yaxis_title='Retention Time (min)',
        xaxis_title='m/z',
        width=550,
        height=550
    )
    return fig, df_summary

def main(file_path=None, mode=None, max_points=None, df_summary=None, filter_type='Plasma'):
    if df_summary is not None:
        df_summary['filter_type'] = filter_type
    else:
        df_summary = load_and_process_data(file_path)
    # For 2D mode, use all individual peaks, not just spectrum averages
    if mode == '2d':
        fig = create_2d_surface_and_heatmap(df_summary=df_summary)
        return fig
    # For 3D and 3d-spikes, keep using the original logic
    elif mode == '3d-spikes':
        fig = create_optimized_3d_spikes(df_summary=df_summary, max_points=max_points)
        return fig
    return None

    
    # Para visualización rápida 2D (recomendado para exploración)
    # main(file_path, mode='2d')
    
    # Para visualización 3D con líneas verticales (como en el código original)
    
    # Para visualización 3D con puntos (alternativa)
    # main(file_path, mode='3d', max_points=8000)