import pyopenms
import plotly.graph_objects as go
import numpy as np

def binning_spectrum(exp, spectrum_value):
    alert = None
    
    merger = pyopenms.SpectraMerger()
    merger.average(exp, "gaussian")
    spectra = exp.getSpectra()
    # Extract spectra
    spectra = exp.getSpectra()

    # Verify if exists at least one spectrum
    if len(spectra) > 0:
        spectrum_index = spectrum_value
        try:
            spectrum = spectra[spectrum_index]
        except IndexError:
            alert = f"Spectrum index {spectrum_index} is out of range."
            return alert, None, spectrum_index

        mz_values, intensity_values = spectrum.get_peaks()
        rt = spectrum.getRT()
        ms_level = spectrum.getMSLevel()

        # Graficar el espectro promediado (sin binning adicional)
        fig_annotated = go.Figure()
        fig_annotated.add_trace(go.Scatter(
            x=mz_values,
            y=intensity_values,
            mode='lines',
            name="Averaged Spectrum (Gaussian)",
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
        return alert, None, spectrum_value

    # return fig_annotated, spectrum_index
