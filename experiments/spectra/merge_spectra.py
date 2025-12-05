import pyopenms as oms
import numpy as np
import plotly.graph_objects as go

def merge_spectra(file_path):
    # Cargar el archivo mzML
    exp = oms.MSExperiment()
    oms.MzMLFile().load(file_path, exp)
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
        line=dict(color='blue', width=1),
        fill='tozeroy',
        fillcolor='rgba(0,100,255,0.2)',
        hovertemplate='<b>m/z:</b> %{x:.4f}<br><b>Intensity:</b> %{y:.0f}<extra></extra>'
    ))

    fig.update_layout(
        # title={
        #     'text': f'Total merged MS1 spectra: {len(spectra_ms1)}',
        #     'x': 0.5,
        #     'xanchor': 'center',
        #     'font': {'size': 16}
        # },
        margin=dict(t=0),
        xaxis_title='m/z',
        yaxis_title='Intensity',
        width=600,
        height=450,
        template='plotly_white',
        hovermode='x'
        
    )

    return fig


