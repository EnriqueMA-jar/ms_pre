import pandas as pd
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pyopenms as pyo


def extraer_datos_mzml(archivo_mzml):
    """
    Extrae masa (m/z), tiempo de retención e intensidad de un archivo mzML
    
    Args:
        archivo_mzml: ruta al archivo .mzML
    
    Returns:
        tuple: (df_mz, df_rt, df_intensity) - tres DataFrames con los datos
    """
    # Cargar el archivo mzML
    exp = pyo.MSExperiment()
    pyo.MzMLFile().load(archivo_mzml, exp)
    
    # Listas para almacenar los datos
    mz_lista = []
    rt_lista = []
    intensity_lista = []
    
    # Iterar sobre todos los espectros
    for spectrum in exp:
        rt = spectrum.getRT()  # Tiempo de retención en segundos
        
        # Obtener los picos (m/z e intensidad)
        for mz, intensity in zip(*spectrum.get_peaks()):
            mz_lista.append(mz)
            rt_lista.append(rt)
            intensity_lista.append(intensity)
    
    # Crear los DataFrames
    df_mz = pd.DataFrame({'Mass_mz': mz_lista})
    df_rt = pd.DataFrame({'Retention_Time': rt_lista})
    df_intensity = pd.DataFrame({'Intensity': intensity_lista})
    
    return df_mz, df_rt, df_intensity


# Ejemplo de uso
if __name__ == "__main__":
    # Reemplaza con la ruta a tu archivo mzML
    archivo = "C:\\Users\\Enrique\\Desktop\\Projects\\Flask projects\\flask_test\\uploads\\centroiding\\680_CD1-1neg_centroided.mzML"
    
    # Extraer los datos
    df_mz, df_rt, df_intensity = extraer_datos_mzml(archivo)
    
   

# Combinar los DataFrames
df_completo = pd.DataFrame({
    'Mass_mz': df_mz['Mass_mz'],
    'Retention_Time': df_rt['Retention_Time'],
    'Intensity': df_intensity['Intensity']
})

# Crear bins para agrupar los datos
rt_bins = 100
mz_bins = 100

# Crear histograma 2D
heatmap, xedges, yedges = np.histogram2d(
    df_completo['Retention_Time'],
    df_completo['Mass_mz'],
    bins=[rt_bins, mz_bins],
    weights=df_completo['Intensity']
)

# Crear malla para la superficie
X, Y = np.meshgrid(xedges[:-1], yedges[:-1])

# Generar superficie 3D con Plotly
fig = go.Figure(data=[go.Surface(
    x=X,
    y=Y,
    z=heatmap.T,
    colorscale='Viridis',
    colorbar=dict(title='Intensidad'),
    hovertemplate=(
        '<b>RT</b>: %{x:.2f} s<br>' +
        '<b>m/z</b>: %{y:.4f}<br>' +
        '<b>Intensity</b>: %{z:.2f}<br>' +
        '<extra></extra>'
    )
)])

fig.update_layout(
    title='Superficie 3D de Intensidad - LC-MS',
    scene=dict(
        xaxis_title='<b>RT (s)</b>',
        yaxis_title='<b>m/z</b>',
        zaxis_title='<b>Intensity</b>',
        xaxis=dict(
            title_font=dict(size=14),
            tickfont=dict(size=12)
        ),
        yaxis=dict(
            title_font=dict(size=14),
            tickfont=dict(size=12)
        ),
        zaxis=dict(
            title_font=dict(size=14),
            tickfont=dict(size=12)
        )
    ),
    width=1000,
    height=800
)

# Mostrar gráfico interactivo
fig.show()
    
# Crear malla para la superficie
X, Y = np.meshgrid(xedges[:-1], yedges[:-1])

# Generar superficie 3D con Plotly
fig = go.Figure(data=[go.Surface(
    x=X,
    y=Y,
    z=heatmap.T,
    colorscale='Viridis',
    colorbar=dict(
        title=dict(
            text='<b>Intensity</b>',
            font=dict(size=14)
        ),
        tickfont=dict(size=12)
    ),
    hovertemplate=(
        '<span style="font-size: 14px; font-weight: bold;">LC-MS Data Point</span><br>' +
        '<b>Retention Time</b>: %{x:.2f} s<br>' +
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
    title=dict(
        text='<b>3D Surface Plot - LC-MS Data</b>',
        x=0.5,
        font=dict(size=20, color='darkblue')
    ),
    scene=dict(
        xaxis=dict(
            title='<b>Retention Time (s)</b>',
            title_font=dict(size=16),
            tickfont=dict(size=12),
            gridcolor='lightgray',
            backgroundcolor='rgb(250, 250, 250)'
        ),
        yaxis=dict(
            title='<b>m/z</b>',
            title_font=dict(size=16),
            tickfont=dict(size=12),
            gridcolor='lightgray',
            backgroundcolor='rgb(250, 250, 250)'
        ),
        zaxis=dict(
            title='<b>Intensity</b>',
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
    width=1200,
    height=800,
    font=dict(family="Arial, sans-serif")
)

# Mostrar gráfico interactivo
fig.show()

# Guardar con nombre más descriptivo
fig.write_html('lc_ms_3d_surface_plot.html')   
    


# Configuración minimalista con fondo blanco puro
fig = go.Figure(data=[go.Surface(
    x=X, y=Y, z=heatmap.T,
    colorscale='Viridis',
    hovertemplate=(
        'RT: %{x:.1f} s<br>m/z: %{y:.4f}<br>Intensity: %{z:.0f}<extra></extra>'
    )
)])

fig.update_layout(
    title='LC-MS 3D Surface',
    scene=dict(
        xaxis_title='RT (s)',
        yaxis_title='m/z', 
        zaxis_title='Intensity',
        bgcolor='white',  # Fondo blanco puro
        xaxis=dict(backgroundcolor='white', gridcolor='lightgray'),
        yaxis=dict(backgroundcolor='white', gridcolor='lightgray'), 
        zaxis=dict(backgroundcolor='white', gridcolor='lightgray')
    ),
    paper_bgcolor='white',
    plot_bgcolor='white'
)

fig.show()    
    	
