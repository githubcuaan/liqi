"""Run the EDA notebooks and export their figures from the current dataset snapshot."""

from pathlib import Path

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "visualization_output"


def run_eda() -> None:
    notebook = nbformat.read(ROOT / "notebook/01_EDA.ipynb", as_version=4)
    names = (
        "01_quy_mo_va_nhan",
        "02_phan_bo_phe",
        "03_phan_bo_patch",
        "04_top_tuong",
        "05_phe_patch",
        "06_chat_luong_du_lieu",
    )
    folder = OUTPUT / "01_eda"
    folder.mkdir(parents=True, exist_ok=True)
    # The notebook calls plt.show() once per chart and does not otherwise save figures.
    notebook.cells.insert(
        2,
        nbformat.v4.new_code_cell(
            "import matplotlib.pyplot as plt\n"
            "from pathlib import Path\n"
            f"_figure_names = list({names!r})\n"
            f"_figure_dir = Path({str(folder)!r})\n"
            "_original_show = plt.show\n"
            "def _save_and_show(*args, **kwargs):\n"
            "    if not _figure_names:\n"
            "        raise RuntimeError('Unexpected additional EDA figure')\n"
            "    path = _figure_dir / (_figure_names.pop(0) + '.png')\n"
            "    plt.gcf().savefig(path, dpi=170, bbox_inches='tight')\n"
            "    print(f'Saved: {path}')\n"
            "    return _original_show(*args, **kwargs)\n"
            "plt.show = _save_and_show\n"
        ),
    )
    execute(notebook)
    if names and len(list(folder.glob("*.png"))) != len(names):
        raise RuntimeError("EDA did not export all six expected figures")


def run_visualization() -> None:
    notebook = nbformat.read(ROOT / "notebook/03_DataVisualization.ipynb", as_version=4)
    source = notebook.cells[1].source
    old = "candidates = [Path('dataset/csv'),"
    if source.count(old) != 1:
        raise RuntimeError("Visualization notebook data-path setup has changed")
    source = source.replace(
        old, "candidates = [Path('dataset/035ce761e53a47db/csv'),",
    )
    old_output = "OUT = Path('visualization_output')"
    if source.count(old_output) != 1:
        raise RuntimeError("Visualization notebook output setup has changed")
    source = source.replace(
        old_output, "OUT = Path('visualization_output/03_data_visualization')",
    )
    notebook.cells[1].source = source
    execute(notebook)


def execute(notebook: nbformat.NotebookNode) -> None:
    NotebookClient(
        notebook, timeout=300, kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    ).execute()
    for cell in notebook.cells:
        for output in cell.get("outputs", []):
            if output.output_type == "stream":
                print(output.text.strip())


if __name__ == "__main__":
    run_eda()
    run_visualization()
    print(f"Figures saved to {OUTPUT}")
