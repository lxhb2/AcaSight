"""CIF file parser for XRD diffraction peak calculation."""
import structlog

logger = structlog.get_logger()


def parse_cif_to_diffraction(cif_content: str, wavelength: str = "CuKa") -> dict:
    """
    Parse CIF file content and calculate diffraction peaks.
    Uses pymatgen if available, otherwise returns error suggesting installation.
    """
    try:
        from pymatgen.analysis.diffraction.xrd import XRDCalculator
        from pymatgen.io.cif import CifParser
        import tempfile
        import os

        # Write to temp file for pymatgen
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cif", delete=False, encoding="utf-8") as f:
            f.write(cif_content)
            tmp_path = f.name

        try:
            parser = CifParser(tmp_path)
            structures = parser.parse_structures()
            if not structures:
                return {"error": "No structure found in CIF file"}

            structure = structures[0]
            calc = XRDCalculator(wavelength=wavelength)
            pattern = calc.get_pattern(structure, two_theta_range=(0, 90))

            return {
                "two_theta": pattern.x.tolist(),
                "intensity": pattern.y.tolist(),
                "hkl": [str(hkl[0]) if hkl else "" for hkl in pattern.hkls],
                "d_spacing": pattern.d_hkls.tolist(),
                "card_info": {
                    "formula": structure.composition.reduced_formula,
                    "space_group": str(structure.spacegroup) if hasattr(structure, "spacegroup") else "unknown",
                },
            }
        finally:
            os.unlink(tmp_path)

    except ImportError:
        return {"error": "pymatgen not installed. Install with: pip install pymatgen"}
    except Exception as e:
        logger.error("CIF parse failed", error=str(e))
        return {"error": f"CIF parsing failed: {str(e)}"}
