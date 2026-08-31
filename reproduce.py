"""Ejecuta y valida el análisis completo desde cualquier directorio."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "Trabajo1_Clima.ipynb"
MANIFEST = ROOT / "data" / "input_manifest.sha256"


def verify_inputs() -> None:
    failures: list[str] = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        expected, relative = line.split(maxsplit=1)
        path = ROOT / relative.strip()
        if not path.is_file():
            failures.append(f"Falta: {relative}")
            continue
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        actual = digest.hexdigest()
        if actual != expected:
            failures.append(f"SHA256 distinto: {relative}\n  esperado {expected}\n  actual   {actual}")
    if failures:
        raise RuntimeError("Los insumos no corresponden al snapshot validado:\n" + "\n".join(failures))
    print("Insumos: SHA256 verificados.", flush=True)


def make_kernel_spec(directory: Path) -> str:
    name = "clima-repro"
    spec_dir = directory / "kernels" / name
    spec_dir.mkdir(parents=True)
    spec = {
        "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "Clima reproducible",
        "language": "python",
    }
    (spec_dir / "kernel.json").write_text(json.dumps(spec), encoding="utf-8")
    return name


def validate_tabular_outputs() -> None:
    import pandas as pd

    csv_path = ROOT / "outputs" / "daily_2stations.csv"
    parquet_path = ROOT / "outputs" / "daily_2stations.parquet"
    csv_data = pd.read_csv(csv_path, parse_dates=["date"])
    parquet_data = pd.read_parquet(parquet_path)
    parquet_data["date"] = pd.to_datetime(parquet_data["date"])
    for column in csv_data.columns:
        if csv_data[column].dtype == object or parquet_data[column].dtype == object:
            csv_data[column] = csv_data[column].astype("string")
            parquet_data[column] = parquet_data[column].astype("string")
    pd.testing.assert_frame_equal(
        csv_data,
        parquet_data,
        check_dtype=False,
        check_exact=False,
        rtol=1e-12,
        atol=1e-15,
    )
    if csv_data.duplicated(["station", "date"]).any():
        raise AssertionError("Hay fechas diarias duplicadas por estación.")
    if set(csv_data["station"]) != {"PSM00091408", "FMM00091334"}:
        raise AssertionError("Las estaciones de salida no son las dos seleccionadas.")
    print(f"Tablas: CSV y Parquet equivalentes ({len(csv_data):,} filas).", flush=True)


def validate_outputs() -> None:
    required = [
        ROOT / "outputs" / "Trabajo1_Clima.executed.ipynb",
        ROOT / "hist-unificado-site" / "hist_unificado.html",
        ROOT / "index_codepen.html",
        ROOT / "Histogra_PSM.html",
        ROOT / "Histogra_FMM.html",
        ROOT / "mjo_precond.gif",
        ROOT / "mjo_phases" / "mjo_phase_all_phases.pdf",
        ROOT / "mjo_phases_anom" / "mjo_phase_anom_all_phases.pdf",
    ]
    required += [ROOT / "mjo_phases" / f"mjo_phase_{phase:02d}.png" for phase in range(1, 9)]
    required += [ROOT / "mjo_phases_anom" / f"mjo_phase_anom_{phase:02d}.png" for phase in range(1, 9)]
    for station in ("PSM00091408", "FMM00091334"):
        required += [
            ROOT / "figs" / f"{station}_box_N2_dark_nofill_micro_amp1.png",
            ROOT / "figs" / f"{station}_theta_profile_dark.png",
            ROOT / "figs" / f"{station}_composites_barras_dark.png",
        ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise AssertionError("Faltan salidas esperadas: " + ", ".join(missing))

    from PIL import Image

    image_paths = [path for path in required if path.suffix.lower() == ".png"]
    for path in image_paths:
        with Image.open(path) as image:
            image.verify()
    with Image.open(ROOT / "mjo_precond.gif") as animation:
        if getattr(animation, "n_frames", 1) != 8:
            raise AssertionError("El GIF MJO no contiene exactamente ocho fases.")

    for relative in (
        Path("mjo_phases/mjo_phase_all_phases.pdf"),
        Path("mjo_phases_anom/mjo_phase_anom_all_phases.pdf"),
    ):
        raw_pdf = (ROOT / relative).read_bytes()
        page_count = len(re.findall(rb"/Type\s*/Page\b", raw_pdf))
        if page_count != 8:
            raise AssertionError(f"{relative} no contiene exactamente ocho páginas.")

    html_paths = [path for path in required if path.suffix.lower() == ".html"]
    for path in html_paths:
        html = path.read_text(encoding="utf-8")
        if "<html" not in html.lower() or "</html>" not in html.lower():
            raise AssertionError(f"HTML incompleto: {path.relative_to(ROOT)}")
    site_html = (ROOT / "hist-unificado-site" / "hist_unificado.html").read_text(encoding="utf-8")
    external_scripts = re.findall(r"<script[^>]+src=[\"']https?://", site_html, flags=re.IGNORECASE)
    if external_scripts:
        raise AssertionError("El HTML principal no es autocontenido.")

    validate_tabular_outputs()
    print("Artefactos gráficos e interactivos: presentes e íntegros.", flush=True)


def execute_notebook(recompute_selection: bool) -> Path:
    import nbformat
    from nbclient import NotebookClient

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    output = ROOT / "outputs" / "Trabajo1_Clima.executed.ipynb"
    output.parent.mkdir(parents=True, exist_ok=True)
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    started = time.monotonic()

    def on_start(cell, cell_index):
        source = "".join(cell.get("source", "")).splitlines()
        label = source[0][:90] if source else cell.get("cell_type", "")
        print(f"[{cell_index + 1:02d}/{len(notebook.cells):02d}] {label}", flush=True)

    with tempfile.TemporaryDirectory(prefix="clima-kernel-") as temp:
        temp_path = Path(temp)
        kernel_name = make_kernel_spec(temp_path)
        previous_jupyter_path = os.environ.get("JUPYTER_PATH")
        previous_headless = os.environ.get("CLIMA_HEADLESS")
        os.environ["JUPYTER_PATH"] = str(temp_path) + (
            os.pathsep + previous_jupyter_path if previous_jupyter_path else ""
        )
        os.environ["CLIMA_HEADLESS"] = "1"
        if recompute_selection:
            os.environ["CLIMA_RECOMPUTE_SELECTION"] = "1"
        os.environ.setdefault("MPLBACKEND", "Agg")
        os.chdir(ROOT)
        try:
            client = NotebookClient(
                notebook,
                timeout=1800,
                kernel_name=kernel_name,
                allow_errors=False,
                on_cell_start=on_start,
            )
            client.execute()
        finally:
            if previous_jupyter_path is None:
                os.environ.pop("JUPYTER_PATH", None)
            else:
                os.environ["JUPYTER_PATH"] = previous_jupyter_path
            if previous_headless is None:
                os.environ.pop("CLIMA_HEADLESS", None)
            else:
                os.environ["CLIMA_HEADLESS"] = previous_headless

    nbformat.write(notebook, output)
    print(f"Notebook ejecutado en {time.monotonic() - started:.1f} s: {output}", flush=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--recompute-selection",
        action="store_true",
        help="vuelve a auditar las 40 candidatas IGRA (más lento y dependiente del snapshot completo)",
    )
    parser.add_argument("--skip-input-check", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if sys.version_info[:2] not in {(3, 11), (3, 12)}:
        raise RuntimeError("Use Python 3.11 o 3.12 para el entorno validado.")
    if not args.skip_input_check:
        verify_inputs()
    execute_notebook(args.recompute_selection)
    validate_outputs()
    print("Reproducción completa y validada.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
