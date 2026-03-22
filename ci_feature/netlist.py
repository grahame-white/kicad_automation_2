"""Netlist normalisation hook for the KiCad export pipeline."""

import os
import shutil
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
    *output_path* refer to the same file.  The temporary file inherits the
    permissions of *input_path* so the normalised file is no more restrictive
    than the original export.

    Args:
        input_path: Path to the raw netlist file produced by ``kicad-cli``.
        output_path: Destination path for the normalised netlist.  May be the
            same as *input_path* for an in-place operation.
    """
    output_dir = os.path.dirname(os.path.abspath(output_path))
    fd, tmp_path = tempfile.mkstemp(dir=output_dir)
    try:
        try:
            fh = os.fdopen(fd, "wb")
        except Exception:
            # Ensure the raw file descriptor from mkstemp is not leaked.
            try:
                os.close(fd)
            except OSError:
                pass
            raise
        with fh:
            with open(input_path, "rb") as src:
                shutil.copyfileobj(src, fh)
        # Copy permissions from the source so the result is no more restrictive
        # than what kicad-cli produced (mkstemp uses mode 0o600 by default).
        shutil.copymode(input_path, tmp_path)
        os.replace(tmp_path, output_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
