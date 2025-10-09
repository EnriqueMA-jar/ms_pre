import pyopenms
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np

# Load the mzML file
def load_mzml_file(file_path):
    exp = pyopenms.MSExperiment()
    pyopenms.MzMLFile().load(file_path, exp)
    
    # Get the list of spectra
    spectra = exp.getSpectra()
    
    # Separate spectra by MS level
    spectra_ms1 = [s for s in spectra if s.getMSLevel() == 1]
    spectra_ms2 = [s for s in spectra if s.getMSLevel() == 2]
    

    if len(spectra_ms1) > 0 and len(spectra_ms2) > 0:
        ms1_index = min(500, len(spectra_ms1) - 1)  # MS1 spectrum
        ms2_index = min(100, len(spectra_ms2) - 1)  # MS2 spectrum

        spectrum_ms1 = spectra_ms1[ms1_index]
        #print(f"spectrum_ms1: {spectrum_ms1.getType()}")
        spectrum_ms2 = spectra_ms2[ms2_index]
        #print(f"spectrum_ms2: {spectrum_ms2.getType()}")

        if spectrum_ms1.getType() == 1 and spectrum_ms2.getType() == 1:
            type = "Centroid"
            print("Both MS1 and MS2 spectra are centroided.")
        else:
            type = "Profile"
            print("At least one of the spectra is profile (not centroided).")
        
         # Extract MS1 data
        mz_ms1, intensity_ms1 = spectrum_ms1.get_peaks()
        rt_ms1 = spectrum_ms1.getRT()
    
        # Extract MS2 data
        mz_ms2, intensity_ms2 = spectrum_ms2.get_peaks()
        rt_ms2 = spectrum_ms2.getRT()
    
        # Get precursor ion for MS2 (if available)
        precursor_mz = "N/A"
        if spectrum_ms2.getPrecursors():
            precursor_mz = f"{spectrum_ms2.getPrecursors()[0].getMZ():.3f}"

    return spectra_ms1, spectra_ms2, spectrum_ms1, spectrum_ms2, mz_ms1, intensity_ms1, rt_ms1, mz_ms2, intensity_ms2, rt_ms2, precursor_mz, type

# Plot comparative spectra side by side
def comparative_spectra_plots(file_path):
    spectra_ms1, spectra_ms2, spectrum_ms1, spectrum_ms2, mz_ms1, intensity_ms1, rt_ms1, mz_ms2, intensity_ms2, rt_ms2, precursor_mz, type = load_mzml_file(file_path)

    fig_comparison = make_subplots(
        rows=1, cols=2,
        subplot_titles=(f'MS1 Spectrum (RT: {rt_ms1:.1f}s)', f'MS2 Spectrum (RT: {rt_ms2:.1f}s, Precursor: {precursor_mz})'),
        horizontal_spacing=0.1
    )
    # MS1 Spectrum (left)
    fig_comparison.add_trace(
        go.Scatter(
            x=mz_ms1,
            y=intensity_ms1,
            mode='lines',
            name='MS1',
            line=dict(color='blue', width=1),
            fill='tozeroy',
            fillcolor='rgba(0,100,255,0.3)',
            hovertemplate='<b>MS1</b><br><b>m/z:</b> %{x:.4f}<br><b>Intensity:</b> %{y:.0f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # MS2 Spectrum (right)
    fig_comparison.add_trace(
        go.Scatter(
            x=mz_ms2,
            y=intensity_ms2,
            mode='lines',
            name='MS2',
            line=dict(color='red', width=1),
            fill='tozeroy',
            fillcolor='rgba(255,0,0,0.3)',
            hovertemplate='<b>MS2</b><br><b>m/z:</b> %{x:.4f}<br><b>Intensity:</b> %{y:.0f}<extra></extra>'
        ),
        row=1, col=2
    )
    
    fig_comparison.update_layout(
        title='MS1 vs MS2 Comparison',
        width=1280,
        height=400,
        template='plotly_white',
        showlegend=True
    )
    
    fig_comparison.update_xaxes(title_text="m/z", row=1, col=1)
    fig_comparison.update_xaxes(title_text="m/z", row=1, col=2)
    fig_comparison.update_yaxes(title_text="Intensity", row=1, col=1)
    fig_comparison.update_yaxes(title_text="Intensity", row=1, col=2)
    return fig_comparison

def overlay_spectra_plots(file_path):
    spectra_ms1, spectra_ms2, spectrum_ms1, spectrum_ms2, mz_ms1, intensity_ms1, rt_ms1, mz_ms2, intensity_ms2, rt_ms2, precursor_mz, type = load_mzml_file(file_path)

    fig_overlay = go.Figure()
    
    # Normalize intensities for comparison
    max_ms1 = max(intensity_ms1) if len(intensity_ms1) > 0 else 1
    max_ms2 = max(intensity_ms2) if len(intensity_ms2) > 0 else 1
    
    # Normalized MS1
    fig_overlay.add_trace(go.Scatter(
        x=mz_ms1,
        y=intensity_ms1 / max_ms1 * 100,  # Normalizado a 100%
        mode='lines',
        name=f'MS1 (RT: {rt_ms1:.1f}s)',
        line=dict(color='blue', width=1.5),
        fill='tozeroy',
        fillcolor='rgba(0,100,255,0.2)',
        hovertemplate='<b>MS1</b><br><b>m/z:</b> %{x:.4f}<br><b>Relative Intensity:</b> %{y:.1f}%<extra></extra>'
    ))
    # Normalized MS2
    fig_overlay.add_trace(go.Scatter(
        x=mz_ms2,
        y=intensity_ms2 / max_ms2 * 100,  # Normalizado a 100%
        mode='lines',
        name=f'MS2 (RT: {rt_ms2:.1f}s, Prec: {precursor_mz})',
        line=dict(color='red', width=1.5),
        fill='tozeroy',
        fillcolor='rgba(255,0,0,0.2)',
        hovertemplate='<b>MS2</b><br><b>m/z:</b> %{x:.4f}<br><b>Relative Intensity:</b> %{y:.1f}%<extra></extra>'
    ))
    
    fig_overlay.update_layout(
        title='Overlayed MS1 vs MS2 (Normalized Intensities)',
        xaxis_title='m/z',
        yaxis_title='Relative Intensity (%)',
        width=1280,
        height=500,
        template='plotly_white',
        hovermode='x'
    )
    
    return fig_overlay

def create_stick_traces(mz_array, intensity_array, name, color, show_fill=False):
    """
    Create stick traces (vertical lines) for centroided data
    """
    x_stick = []
    y_stick = []
    
    for mz, intensity in zip(mz_array, intensity_array):
        x_stick.extend([mz, mz, None])  # x, x, None para línea vertical
        y_stick.extend([0, intensity, None])  # 0, intensidad, None
    
    trace = go.Scatter(
        x=x_stick,
        y=y_stick,
        mode='lines',
        name=name,
        line=dict(color=color, width=1.5),
        hoverinfo='skip',  # Desactivar hover en las líneas
        showlegend=True
    )
    
    # Agregar puntos en las cimas para hover mejorado
    hover_trace = go.Scatter(
        x=mz_array,
        y=intensity_array,
        mode='markers',
        marker=dict(color=color, size=4, opacity=0.8),
        name=name + ' (peaks)',
        showlegend=False,
        hovertemplate=f'<b>{name}</b><br><b>m/z:</b> %{{x:.4f}}<br><b>Intensity:</b> %{{y:.0f}}<extra></extra>'
    )
    
    return trace, hover_trace

def comparative_spectra_plots2(file_path):
    spectra_ms1, spectra_ms2, spectrum_ms1, spectrum_ms2, mz_ms1, intensity_ms1, rt_ms1, mz_ms2, intensity_ms2, rt_ms2, precursor_mz, type = load_mzml_file(file_path)
    
    ms1_index = min(500, len(spectra_ms1) - 1)  # Espectro MS1
    ms2_index = min(100, len(spectra_ms2) - 1)  # Espectro MS2
    
    spectrum_ms1 = spectra_ms1[ms1_index]
    spectrum_ms2 = spectra_ms2[ms2_index]
    
    # Extraer datos MS1
    mz_ms1, intensity_ms1 = spectrum_ms1.get_peaks()
    rt_ms1 = spectrum_ms1.getRT()
    
    # Extraer datos MS2
    mz_ms2, intensity_ms2 = spectrum_ms2.get_peaks()
    rt_ms2 = spectrum_ms2.getRT()
    
    # Obtener ion precursor para MS2 (si está disponible)
    precursor_mz = "N/A"
    if spectrum_ms2.getPrecursors():
        precursor_mz = f"{spectrum_ms2.getPrecursors()[0].getMZ():.3f}"
    
    print(f"\nMS1 - Índice: {ms1_index}, RT: {rt_ms1:.2f} s, Picos: {len(mz_ms1)}")
    print(f"MS2 - Índice: {ms2_index}, RT: {rt_ms2:.2f} s, Picos: {len(mz_ms2)}, Precursor: {precursor_mz}")
    
    # ==================== GRÁFICO COMPARATIVO STICK (LADO A LADO) ====================
    fig_comparison = make_subplots(
        rows=1, cols=2,
        subplot_titles=(f'MS1 Spectrum (RT: {rt_ms1:.1f}s)', f'MS2 Spectrum (RT: {rt_ms2:.1f}s, Precursor: {precursor_mz})'),
        horizontal_spacing=0.1
    )
    
    # MS1 Spectrum (izquierda) - modo stick
    ms1_stick, ms1_hover = create_stick_traces(mz_ms1, intensity_ms1, 'MS1', 'blue')
    fig_comparison.add_trace(ms1_stick, row=1, col=1)
    fig_comparison.add_trace(ms1_hover, row=1, col=1)
    
    # MS2 Spectrum (derecha) - modo stick
    ms2_stick, ms2_hover = create_stick_traces(mz_ms2, intensity_ms2, 'MS2', 'red')
    fig_comparison.add_trace(ms2_stick, row=1, col=2)
    fig_comparison.add_trace(ms2_hover, row=1, col=2)
    
    fig_comparison.update_layout(
        title='MS1 vs MS2 Comparison (Centroid - Stick Mode)',
        width=1280,
        height=500,
        template='plotly_white',
        showlegend=True
    )
    
    fig_comparison.update_xaxes(title_text="m/z", row=1, col=1)
    fig_comparison.update_xaxes(title_text="m/z", row=1, col=2)
    fig_comparison.update_yaxes(title_text="Intensidad", row=1, col=1)
    fig_comparison.update_yaxes(title_text="Intensidad", row=1, col=2)

    return fig_comparison

def overlay_spectra_plots2(file_path):
    spectra_ms1, spectra_ms2, spectrum_ms1, spectrum_ms2, mz_ms1, intensity_ms1, rt_ms1, mz_ms2, intensity_ms2, rt_ms2, precursor_mz, type = load_mzml_file(file_path)
    
    fig_overlay = go.Figure()
    
    # Normalizar intensidades para comparación
    max_ms1 = max(intensity_ms1) if len(intensity_ms1) > 0 else 1
    max_ms2 = max(intensity_ms2) if len(intensity_ms2) > 0 else 1
    
    # MS1 normalizado - modo stick
    intensity_ms1_norm = intensity_ms1 / max_ms1 * 100
    ms1_stick_norm, ms1_hover_norm = create_stick_traces(mz_ms1, intensity_ms1_norm, f'MS1 (RT: {rt_ms1:.1f}s)', 'blue')
    fig_overlay.add_trace(ms1_stick_norm)
    fig_overlay.add_trace(ms1_hover_norm)
    
    # MS2 normalizado - modo stick
    intensity_ms2_norm = intensity_ms2 / max_ms2 * 100
    ms2_stick_norm, ms2_hover_norm = create_stick_traces(mz_ms2, intensity_ms2_norm, f'MS2 (RT: {rt_ms2:.1f}s, Prec: {precursor_mz})', 'red')
    fig_overlay.add_trace(ms2_stick_norm)
    fig_overlay.add_trace(ms2_hover_norm)
    
    fig_overlay.update_layout(
        title='Overlayed MS1 vs MS2 (Centroid - Stick Mode, Normalized Intensities)',
        xaxis_title='m/z',
        yaxis_title='Relative Intensity (%)',
        width=1280,
        height=500,
        template='plotly_white',
        hovermode='closest'
    )
    return fig_overlay

def render_spectra_plots(file_path):
    type = load_mzml_file(file_path)[-1]
    if type == "Centroid":
        fig_comparison, fig_overlay = comparative_spectra_plots2(file_path), overlay_spectra_plots2(file_path)
        return fig_comparison, fig_overlay
    elif type == "Profile":
        fig_comparison, fig_overlay = comparative_spectra_plots(file_path), overlay_spectra_plots(file_path)
        return fig_comparison, fig_overlay