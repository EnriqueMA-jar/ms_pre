import pyopenms as oms
import plotly.graph_objects as go

def normalize_to_one(input_path):
    
    # Load the mzML file
    exp = oms.MSExperiment()
    oms.MzMLFile().load(input_path, exp)
    
    # Create a Normalizer object
    normalizer = oms.Normalizer()
    
    # Get and set parameters for normalization
    param = normalizer.getParameters()
    param.setValue("method", "to_one")
    
    # Apply normalization
    normalizer.setParameters(param)
    normalizer.filterPeakMap(exp)
    
    # Save the normalized mzML file in uploads/normalize
    import os
    normalize_dir = os.path.join("uploads", "normalize")
    os.makedirs(normalize_dir, exist_ok=True)
    base_name = os.path.basename(input_path).replace(".mzML", "_TO_ONE_normalized.mzML")
    output_path = os.path.join(normalize_dir, base_name)
    oms.MzMLFile().store(output_path, exp)
    
    # Create a plot of the first spectrum before and after normalization
    original_exp = oms.MSExperiment()
    oms.MzMLFile().load(input_path, original_exp)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=original_exp.getSpectrum(0).get_peaks()[0],
        y=original_exp.getSpectrum(0).get_peaks()[1],
        name='Original Spectrum',
        marker_color='blue',
        opacity=1.0,
        width=1,
        hovertemplate='<b>m/z:</b> %{x:.4f}<br><b>Intensity:</b> %{y:.0f}<extra></extra>'
    ))
    
    
    # Add the normalized spectrum to the plot
    normalized_exp = oms.MSExperiment()
    oms.MzMLFile().load(output_path, normalized_exp)
    fig2 =  go.Figure()
    fig2.add_trace(go.Bar(
        x=normalized_exp.getSpectrum(0).get_peaks()[0],
        y=normalized_exp.getSpectrum(0).get_peaks()[1],
        name='Normalized Spectrum',
        marker_color='red',
        opacity=1.0,
        width=1,
        hovertemplate='<b>m/z:</b> %{x:.4f}<br><b>Intensity:</b> %{y:.0f}<extra></extra>'
    ))
    fig.update_layout(
        title={
            'text': 'Spectrum Before Normalization to One',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16}
        },
        margin=dict(t=50),
        xaxis_title='m/z',
        yaxis_title='Intensity',
        width=600,
        height=450,
        legend=dict(x=0.01, y=0.99, bgcolor='white', bordercolor='rgba(0,0,0,0)'),
        template='plotly_white',
        showlegend=True
    )
    fig2.update_layout(
        title={
            'text': 'Spectrum After Normalization to One',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16}
        },
        margin=dict(t=50),
        xaxis_title='m/z',
        yaxis_title='Intensity',
        width=600,
        height=450,
        legend=dict(x=0.01, y=0.99, bgcolor='white', bordercolor='rgba(0,0,0,0)'),
        template='plotly_white',
        showlegend=True
    )
    return fig, fig2, output_path
    