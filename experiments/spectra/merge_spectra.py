import pyopenms as oms
import numpy as np
import plotly.graph_objects as go

def merge_spectra(exp):
    # Cargar el archivo mzML
    spectra = exp.getSpectra()

    # Filtrar solo los espectros MS1 (puedes cambiar el nivel si es necesario)
    spectra_ms1 = [s for s in spectra if s.getMSLevel() == 1]


    # Inicializar arrays para almacenar m/z e intensidades
    mz_all = np.array([])
    intensity_all = np.array([])

    # Concatenar los picos de todos los espectros MS1
    for spectrum in spectra_ms1:
        mz_values, intensity_values = spectrum.get_peaks()
        mz_all = np.concatenate((mz_all, mz_values))
        intensity_all = np.concatenate((intensity_all, intensity_values))

    # Ordenar los valores de m/z
    sorted_indices = np.argsort(mz_all)
    mz_all_sorted = mz_all[sorted_indices]
    intensity_all_sorted = intensity_all[sorted_indices]

    # Fusionar las intensidades si los valores de m/z se repiten
    # En este caso, vamos a sumar las intensidades de los picos con el mismo m/z
    unique_mz, unique_indices = np.unique(mz_all_sorted, return_inverse=True)
    intensity_fused = np.zeros(len(unique_mz))

    for idx in range(len(mz_all_sorted)):
        intensity_fused[unique_indices[idx]] += intensity_all_sorted[idx]

    # Crear la gráfica con Plotly
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=unique_mz,
        y=intensity_fused,
        mode='lines',
        name='Merged Spectrum',
        line=dict(color='darkblue', width=2),
        fill='tozeroy',
        fillcolor='rgba(0,100,255,0.3)',
        hovertemplate='<b>m/z:</b> %{x:.4f}<br><b>Intensity:</b> %{y:.0f}<extra></extra>'
    ))

    fig.update_layout(
        margin=dict(t=10, l=60, r=60, b=50),
        xaxis_title='m/z',
        yaxis_title='Intensity',
        width=600,
        height=450,
        template='plotly_white',
        hovermode='x unified'
        
    )

    return fig


