function downloadPlotlyImage() {
    var format = document.getElementById('img-format').value;
    var width = parseInt(document.getElementById('img-width').value);
    var height = parseInt(document.getElementById('img-height').value);

    var div1 = document.getElementById('plotly-graph-1');
    var div2 = document.getElementById('plotly-graph-2');

    // Busca el div interno generado por Plotly
    var plotDiv1 = div1 ? div1.querySelector('div[id^="plotly-"]') : null;
    var plotDiv2 = div2 ? div2.querySelector('div[id^="plotly-"]') : null;

    if (plotDiv1) {
        Plotly.downloadImage(plotDiv1, {
            format: format,
            width: width,
            height: height,
            filename: 'exported_plot'
        });
    }
    if (plotDiv2) {
        Plotly.downloadImage(plotDiv2, {
            format: format,
            width: width,
            height: height,
            filename: 'exported_plot_2'
        });
    }
}