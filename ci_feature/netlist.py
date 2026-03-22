"""Netlist normalisation hook for the KiCad export pipeline."""

import os
import tempfile

__all__ = ["normalize_netlist"]


def normalize_netlist(input_path: str, output_path: str) -> None:
    """Normalise a raw netlist file, writing the result to *output_path*.

    Currently this is a **pass-through** implementation: the content of
    *input_path* is copied to *output_path* unchanged.  The function exists as
    a stable extension point so that future normalisation transformations (e.g.
    sorting nets, stripping volatile timestamps) can be added here without
    touching the rest of the export pipeline.

    The output is written atomically via a temporary file in the same directory
    as *output_path*, then renamed into place.  This ensures that a failed write
    never leaves a truncated file behind — even when *input_path* and
    *output_path* refer to the same file.

    Args:
        input_path: Path to the raw netlist file produced by ``kicad-cli``.
        output_path: Destination path for the normalised netlist.  May be the
            same as *input_path* for an in-place operation.
    """
    with open(input_path, "rb") as fh:
        content = fh.read()

    output_dir = os.path.dirname(os.path.abspath(output_path))
    fd, tmp_path = tempfile.mkstemp(dir=output_dir)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(content)
        os.replace(tmp_path, output_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
