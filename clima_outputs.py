"""Generadores deterministas de salidas interactivas del análisis MJO–N²."""

from pathlib import Path

import numpy as np
import plotly.graph_objects as go


PHASE_COLORS = {
    1: "#1f77b4",
    2: "#ff7f0e",
    3: "#2ca02c",
    4: "#d62728",
    5: "#9467bd",
    6: "#17becf",
    7: "#e377c2",
    8: "#bcbd22",
}


def build_unified_histogram_html(
    df,
    site_filename="hist-unificado-site/hist_unificado.html",
    codepen_filename="index_codepen.html",
    amp_values=None,
    amp_default=1.0,
    bins_default=40,
):
    """Genera el histograma N² unificado para las dos estaciones.

    ``site_filename`` es autocontenido y funciona sin internet. La copia para
    CodePen usa el CDN de Plotly para reducir el tamaño al pegarla/publicarla.
    """
    required = {"station", "N2_s2", "phase", "amplitude"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {sorted(missing)}")

    data = df.dropna(subset=list(required)).copy()
    data["phase"] = data["phase"].astype(int)
    stations = sorted(data["station"].astype(str).unique())
    if not stations:
        raise ValueError("No hay estaciones con N², fase y amplitud válidos.")

    if amp_values is None:
        amp_values = np.round(np.arange(0.0, 2.51, 0.1), 1)
    amp_values = tuple(float(x) for x in amp_values)
    if amp_default not in amp_values:
        raise ValueError("amp_default debe estar incluido en amp_values.")

    xmin, xmax = np.nanpercentile(data["N2_s2"].to_numpy(), [1, 99])
    if not np.isfinite(xmin + xmax) or xmax <= xmin:
        raise ValueError("El rango de N² no es válido.")

    figure = go.Figure()
    trace_sources = []
    for station_index, station in enumerate(stations):
        station_data = data[data["station"].astype(str) == station]
        for phase in range(1, 9):
            phase_data = station_data[station_data["phase"] == phase]
            x_all = np.round(phase_data["N2_s2"].to_numpy(dtype=float), 8)
            amp_all = np.round(phase_data["amplitude"].to_numpy(dtype=float), 3)
            trace_sources.append((x_all, amp_all))
            figure.add_trace(
                go.Histogram(
                    x=x_all[amp_all >= amp_default],
                    name=str(phase),
                    legendgroup=str(phase),
                    showlegend=(station_index == 0),
                    visible=(station_index == 0),
                    opacity=0.45,
                    marker={
                        "color": PHASE_COLORS[phase],
                        "line": {"width": 0.6, "color": "rgba(255,255,255,0.35)"},
                    },
                    xbins={
                        "start": float(xmin),
                        "end": float(xmax),
                        "size": float((xmax - xmin) / bins_default),
                    },
                    histnorm="probability density",
                )
            )

    trace_count = len(trace_sources)
    frames = []
    for amp in amp_values:
        frames.append(
            go.Frame(
                name=f"amp{amp:.1f}",
                traces=list(range(trace_count)),
                data=[go.Histogram(x=x[a >= amp]) for x, a in trace_sources],
            )
        )
    figure.frames = frames

    station_buttons = []
    for station_index, station in enumerate(stations):
        first = station_index * 8
        visible = [first <= index < first + 8 for index in range(trace_count)]
        showlegend = visible.copy()
        station_buttons.append(
            {
                "label": station,
                "method": "update",
                "args": [
                    {"visible": visible, "showlegend": showlegend},
                    {"title.text": f"{station} · N² (980–850 hPa)"},
                ],
            }
        )

    density_buttons = [
        {
            "label": "Densidad",
            "method": "update",
            "args": [{"histnorm": "probability density"}, {"yaxis.title.text": "Densidad"}],
        },
        {
            "label": "Conteo",
            "method": "update",
            "args": [{"histnorm": ""}, {"yaxis.title.text": "Conteo"}],
        },
    ]

    amp_steps = [
        {
            "label": f"{amp:.1f}",
            "method": "animate",
            "args": [
                [f"amp{amp:.1f}"],
                {
                    "mode": "immediate",
                    "frame": {"duration": 0, "redraw": True},
                    "transition": {"duration": 0},
                },
            ],
        }
        for amp in amp_values
    ]
    bin_values = range(10, 81, 10)
    bin_steps = [
        {
            "label": str(count),
            "method": "restyle",
            "args": [{"xbins.size": float((xmax - xmin) / count)}],
        }
        for count in bin_values
    ]

    grid = "rgba(255,255,255,0.15)"
    figure.update_layout(
        title={"text": f"{stations[0]} · N² (980–850 hPa)", "font": {"size": 25}},
        barmode="overlay",
        paper_bgcolor="black",
        plot_bgcolor="black",
        font={"family": "Arial", "size": 17, "color": "white"},
        legend={"title": {"text": "Fase RMM"}, "orientation": "h", "y": 1.02},
        margin={"l": 80, "r": 25, "t": 155, "b": 75},
        updatemenus=[
            {
                "type": "dropdown",
                "buttons": station_buttons,
                "x": 0.0,
                "y": 1.22,
                "xanchor": "left",
                "bgcolor": "#111111",
            },
            {
                "type": "buttons",
                "buttons": density_buttons,
                "direction": "right",
                "x": 0.37,
                "y": 1.22,
                "bgcolor": "#111111",
            },
        ],
        sliders=[
            {
                "active": amp_values.index(amp_default),
                "steps": amp_steps,
                "x": 0.0,
                "y": 1.11,
                "len": 0.58,
                "currentvalue": {"prefix": "amp ≥ "},
            },
            {
                "active": list(bin_values).index(bins_default),
                "steps": bin_steps,
                "x": 0.66,
                "y": 1.11,
                "len": 0.32,
                "currentvalue": {"prefix": "bins = "},
            },
        ],
    )
    figure.update_xaxes(
        title="N² (s⁻²)",
        range=[float(xmin), float(xmax)],
        linecolor="white",
        gridcolor=grid,
        zerolinecolor=grid,
    )
    figure.update_yaxes(title="Densidad", linecolor="white", gridcolor=grid, zerolinecolor=grid)

    site_path = Path(site_filename)
    codepen_path = Path(codepen_filename)
    site_path.parent.mkdir(parents=True, exist_ok=True)
    codepen_path.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(site_path, include_plotlyjs=True, full_html=True, auto_play=False)
    figure.write_html(codepen_path, include_plotlyjs="cdn", full_html=True, auto_play=False)
    print(f"HTML autocontenido: {site_path}")
    print(f"HTML para CodePen/CDN: {codepen_path}")
    return figure
