"""Unified plotting API router."""
import os
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from app.services.plot.xrd_plot import generate_xrd_stacked_schema, parse_jade_txt
from app.services.plot.cif_parser import parse_cif_to_diffraction
from app.services.plot.schema_renderer import schema_to_figure, export_figure
from app.services.plot.theme_engine import apply_theme_to_schema, list_themes, load_theme
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/plot", tags=["plot"])


# === Request/Response Models ===

class XRDDataSet(BaseModel):
    two_theta: List[float]
    intensity: List[float]
    label: str = "Sample"
    color: str = "#333333"

class PDFCard(BaseModel):
    two_theta: List[float]
    intensity: List[float]
    card_id: str = "PDF#00-0000"
    color: str = "#d62728"
    hkl: Optional[List[str]] = None

class XRDStackedRequest(BaseModel):
    xrd_data: List[XRDDataSet]
    pdf_cards: List[PDFCard] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)

class ExportRequest(BaseModel):
    plot_schema: dict
    format: str = "png"
    width: int = 1200
    height: int = 800
    scale: int = 2

class ThemeApplyRequest(BaseModel):
    plot_schema: dict
    theme_id: str = "nature"

class RSMSurfaceRequest(BaseModel):
    x_data: List[float]
    y_data: List[float]
    z_data: List[float]
    config: dict = Field(default_factory=dict)

class RSMContourRequest(BaseModel):
    x_data: List[float]
    y_data: List[float]
    z_data: List[float]
    config: dict = Field(default_factory=dict)

class RSMFitModelRequest(BaseModel):
    x_data: List[float]
    y_data: List[float]
    z_data: List[float]
    degree: int = 2

class SpectrumBaselineRequest(BaseModel):
    x_data: List[float]
    y_data: List[float]
    method: str = "als"
    params: dict = Field(default_factory=dict)

class SpectrumSmoothRequest(BaseModel):
    y_data: List[float]
    method: str = "savgol"
    params: dict = Field(default_factory=dict)

class SpectrumFindPeaksRequest(BaseModel):
    x_data: List[float]
    y_data: List[float]
    params: dict = Field(default_factory=dict)

class SpectrumFitPeaksRequest(BaseModel):
    x_data: List[float]
    y_data: List[float]
    peak_positions: List[float]
    peak_type: str = "pvoigt"
    config: dict = Field(default_factory=dict)

class RamanSpectrumRequest(BaseModel):
    x_data: List[float]
    y_data: List[float]
    config: dict = Field(default_factory=dict)

class RamanPeakFitRequest(BaseModel):
    x_data: List[float]
    y_data: List[float]
    peak_positions: List[float]
    config: dict = Field(default_factory=dict)

class XPSSpectrumRequest(BaseModel):
    x_data: List[float]
    y_data: List[float]
    config: dict = Field(default_factory=dict)

class XPSPeakFitRequest(BaseModel):
    x_data: List[float]
    y_data: List[float]
    peak_positions: List[float]
    config: dict = Field(default_factory=dict)

class FTIRSpectrumRequest(BaseModel):
    x_data: List[float]
    y_data: List[float]
    config: dict = Field(default_factory=dict)

class UVVisSpectrumRequest(BaseModel):
    x_data: List[float]
    y_data: List[float]
    config: dict = Field(default_factory=dict)

class TaucPlotRequest(BaseModel):
    x_data: List[float]
    y_data: List[float]
    config: dict = Field(default_factory=dict)

class TGADSCRequest(BaseModel):
    x_data: List[float]
    tga_data: List[float]
    dsc_data: Optional[List[float]] = None
    config: dict = Field(default_factory=dict)

class BETIsothermRequest(BaseModel):
    p_po_ads: List[float]
    v_ads: List[float]
    p_po_des: Optional[List[float]] = None
    v_des: Optional[List[float]] = None
    config: dict = Field(default_factory=dict)

class BJHPoreRequest(BaseModel):
    pore_diameter: List[float]
    dv_dd: List[float]
    config: dict = Field(default_factory=dict)

class ANOVABarRequest(BaseModel):
    groups: List[dict]
    comparisons: List[dict] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)

class CorrelationHeatmapRequest(BaseModel):
    variables: List[str]
    corr_matrix: List[List[float]]
    p_matrix: Optional[List[List[float]]] = None
    config: dict = Field(default_factory=dict)

class PCABiplotRequest(BaseModel):
    scores: List[List[float]]
    loadings: List[List[float]]
    variance_explained: List[float]
    group_labels: Optional[List[str]] = None
    variable_names: List[str]
    config: dict = Field(default_factory=dict)

class ParetoRequest(BaseModel):
    effects: List[dict]
    config: dict = Field(default_factory=dict)

class MainEffectsRequest(BaseModel):
    factors: List[dict]
    config: dict = Field(default_factory=dict)

class InteractionRequest(BaseModel):
    factor1_levels: List[float]
    factor2_levels: List[float]
    means_matrix: List[List[float]]
    factor1_name: str = "Factor A"
    factor2_name: str = "Factor B"
    config: dict = Field(default_factory=dict)


# === XRD Endpoints ===

@router.post("/xrd/stacked")
async def xrd_stacked(req: XRDStackedRequest):
    """Generate XRD stacked chart PlotSchema."""
    try:
        xrd_datasets = [d.model_dump() for d in req.xrd_data]
        pdf_cards = [c.model_dump() for c in req.pdf_cards]
        schema = generate_xrd_stacked_schema(xrd_datasets, pdf_cards, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("XRD stacked generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xrd/parse-cif")
async def parse_cif(file: UploadFile = File(...)):
    """Parse CIF file to diffraction peak data."""
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    wavelength = "CuKa"
    result = parse_cif_to_diffraction(text, wavelength)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


@router.post("/xrd/parse-jade")
async def parse_jade(file: UploadFile = File(...)):
    """Parse Jade-exported PDF card txt data."""
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    return parse_jade_txt(text)


# === Export ===

@router.post("/export")
async def export_plot(req: ExportRequest):
    """Export PlotSchema to image."""
    try:
        schema = req.plot_schema
        if req.format not in ("png", "pdf", "svg", "eps"):
            raise HTTPException(status_code=400, detail=f"Unsupported format: {req.format}")
        url = export_figure(schema, format=req.format, width=req.width, height=req.height, scale=req.scale)
        return {"image_url": url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Export failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === Themes ===

@router.get("/themes")
async def get_themes():
    """List available journal themes."""
    return {"themes": list_themes()}


@router.post("/apply-theme")
async def apply_theme(req: ThemeApplyRequest):
    """Apply a journal theme to a PlotSchema."""
    try:
        schema = apply_theme_to_schema(req.plot_schema, req.theme_id)
        return {"schema": schema}
    except Exception as e:
        logger.error("Theme apply failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === RSM Endpoints ===

@router.post("/rsm/surface3d")
async def rsm_surface3d(req: RSMSurfaceRequest):
    """Generate 3D response surface PlotSchema."""
    try:
        from app.services.plot.rsm_plot import generate_rsm_surface_schema
        schema = generate_rsm_surface_schema(req.x_data, req.y_data, req.z_data, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("RSM surface generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rsm/contour")
async def rsm_contour(req: RSMContourRequest):
    """Generate 2D contour PlotSchema."""
    try:
        from app.services.plot.rsm_plot import generate_contour_schema
        schema = generate_contour_schema(req.x_data, req.y_data, req.z_data, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("RSM contour generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rsm/fit-model")
async def rsm_fit_model(req: RSMFitModelRequest):
    """Fit response surface model and return equation + statistics."""
    try:
        from app.services.plot.rsm_plot import fit_response_model
        result = fit_response_model(req.x_data, req.y_data, req.z_data, req.degree)
        return result
    except Exception as e:
        logger.error("RSM model fitting failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === Spectrum Processing Endpoints ===

@router.post("/spectrum/baseline")
async def spectrum_baseline(req: SpectrumBaselineRequest):
    """Apply baseline correction to spectrum data."""
    try:
        from app.services.plot.spectrum_engine import correct_baseline
        import numpy as np
        result = correct_baseline(np.array(req.x_data), np.array(req.y_data), req.method, req.params)
        return result
    except Exception as e:
        logger.error("Baseline correction failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spectrum/smooth")
async def spectrum_smooth(req: SpectrumSmoothRequest):
    """Apply smoothing filter to spectrum data."""
    try:
        from app.services.plot.spectrum_engine import smooth_data
        import numpy as np
        result = smooth_data(np.array(req.y_data), req.method, req.params)
        return result
    except Exception as e:
        logger.error("Smoothing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spectrum/find-peaks")
async def spectrum_find_peaks(req: SpectrumFindPeaksRequest):
    """Detect peaks in spectrum data."""
    try:
        from app.services.plot.spectrum_engine import detect_peaks
        import numpy as np
        result = detect_peaks(np.array(req.x_data), np.array(req.y_data), req.params)
        return result
    except Exception as e:
        logger.error("Peak detection failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spectrum/fit-peaks")
async def spectrum_fit_peaks(req: SpectrumFitPeaksRequest):
    """Multi-peak fitting for spectrum data."""
    try:
        from app.services.plot.spectrum_engine import fit_peaks, generate_spectrum_fit_schema
        import numpy as np
        x = np.array(req.x_data)
        y = np.array(req.y_data)
        fit_result = fit_peaks(x, y, req.peak_positions, req.peak_type)
        if not fit_result.get("success", False):
            raise HTTPException(status_code=422, detail=fit_result.get("error", "Fitting failed"))
        schema = generate_spectrum_fit_schema(x, y, fit_result, req.config)
        return {"schema": schema, "fit_result": fit_result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Peak fitting failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === Raman Endpoints ===

@router.post("/raman/spectrum")
async def raman_spectrum(req: RamanSpectrumRequest):
    try:
        from app.services.plot.raman_plot import generate_raman_spectrum_schema
        schema = generate_raman_spectrum_schema(req.x_data, req.y_data, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("Raman spectrum generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/raman/peak-fit")
async def raman_peak_fit(req: RamanPeakFitRequest):
    try:
        from app.services.plot.raman_plot import generate_raman_peak_fit_schema
        result = generate_raman_peak_fit_schema(req.x_data, req.y_data, req.peak_positions, req.config)
        if not result.get("success", False):
            raise HTTPException(status_code=422, detail=result.get("error", "Fitting failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Raman peak fit failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === XPS Endpoints ===

@router.post("/xps/spectrum")
async def xps_spectrum(req: XPSSpectrumRequest):
    try:
        from app.services.plot.xps_plot import generate_xps_spectrum_schema
        schema = generate_xps_spectrum_schema(req.x_data, req.y_data, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("XPS spectrum generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xps/peak-fit")
async def xps_peak_fit(req: XPSPeakFitRequest):
    try:
        from app.services.plot.xps_plot import generate_xps_peak_fit_schema
        result = generate_xps_peak_fit_schema(req.x_data, req.y_data, req.peak_positions, req.config)
        if not result.get("success", False):
            raise HTTPException(status_code=422, detail=result.get("error", "Fitting failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("XPS peak fit failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === FTIR Endpoint ===

@router.post("/ftir/spectrum")
async def ftir_spectrum(req: FTIRSpectrumRequest):
    try:
        from app.services.plot.ftir_plot import generate_ftir_spectrum_schema
        schema = generate_ftir_spectrum_schema(req.x_data, req.y_data, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("FTIR spectrum generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === UV-Vis Endpoints ===

@router.post("/uvvis/spectrum")
async def uvvis_spectrum(req: UVVisSpectrumRequest):
    try:
        from app.services.plot.uvvis_plot import generate_uvvis_spectrum_schema
        schema = generate_uvvis_spectrum_schema(req.x_data, req.y_data, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("UV-Vis spectrum generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/uvvis/tauc")
async def uvvis_tauc(req: TaucPlotRequest):
    try:
        from app.services.plot.uvvis_plot import generate_tauc_plot_schema
        schema = generate_tauc_plot_schema(req.x_data, req.y_data, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("Tauc plot generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === Thermal Analysis ===

@router.post("/thermal/tga-dsc")
async def thermal_tga_dsc(req: TGADSCRequest):
    try:
        from app.services.plot.thermal_plot import generate_tga_dsc_schema
        schema = generate_tga_dsc_schema(req.x_data, req.tga_data, req.dsc_data, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("TGA/DSC plot generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === BET Endpoints ===

@router.post("/bet/isotherm")
async def bet_isotherm(req: BETIsothermRequest):
    try:
        from app.services.plot.bet_plot import generate_bet_isotherm_schema
        schema = generate_bet_isotherm_schema(req.p_po_ads, req.v_ads, req.p_po_des, req.v_des, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("BET isotherm generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bet/pore-distribution")
async def bet_pore_distribution(req: BJHPoreRequest):
    try:
        from app.services.plot.bet_plot import generate_bjh_pore_schema
        schema = generate_bjh_pore_schema(req.pore_diameter, req.dv_dd, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("BJH pore distribution generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === Statistics Endpoints ===

@router.post("/stats/anova-bar")
async def stats_anova_bar(req: ANOVABarRequest):
    try:
        from app.services.plot.stats_plot import generate_anova_bar_schema
        schema = generate_anova_bar_schema(req.groups, req.comparisons, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("ANOVA bar chart generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stats/correlation-heatmap")
async def stats_correlation_heatmap(req: CorrelationHeatmapRequest):
    try:
        from app.services.plot.stats_plot import generate_correlation_heatmap_schema
        schema = generate_correlation_heatmap_schema(req.variables, req.corr_matrix, req.p_matrix, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("Correlation heatmap generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stats/pca-biplot")
async def stats_pca_biplot(req: PCABiplotRequest):
    try:
        from app.services.plot.stats_plot import generate_pca_biplot_schema
        schema = generate_pca_biplot_schema(req.scores, req.loadings, req.variance_explained, req.group_labels, req.variable_names, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("PCA biplot generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === DOE Endpoints ===

@router.post("/rsm/pareto")
async def rsm_pareto(req: ParetoRequest):
    try:
        from app.services.plot.doe_plot import generate_pareto_schema
        schema = generate_pareto_schema(req.effects, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("Pareto chart generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rsm/main-effects")
async def rsm_main_effects(req: MainEffectsRequest):
    try:
        from app.services.plot.doe_plot import generate_main_effects_schema
        schema = generate_main_effects_schema(req.factors, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("Main effects chart generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rsm/interaction")
async def rsm_interaction(req: InteractionRequest):
    try:
        from app.services.plot.doe_plot import generate_interaction_schema
        schema = generate_interaction_schema(req.factor1_levels, req.factor2_levels, req.means_matrix, req.factor1_name, req.factor2_name, req.config)
        return {"schema": schema}
    except Exception as e:
        logger.error("Interaction chart generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
