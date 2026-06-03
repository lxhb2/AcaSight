const BASE_URL = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {};
  if (!(options?.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(`${BASE_URL}${url}`, { ...options, headers });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`API ${url} failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export const plotApi = {
  // XRD
  async generateXRDStacked(
    xrdData: any[],
    pdfCards: any[],
    config: Record<string, any>
  ): Promise<{ schema: any }> {
    return request('/plot/xrd/stacked', {
      method: 'POST',
      body: JSON.stringify({ xrd_data: xrdData, pdf_cards: pdfCards, config }),
    });
  },

  async parseCif(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    return request('/plot/xrd/parse-cif', { method: 'POST', body: formData });
  },

  async parseJade(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    return request('/plot/xrd/parse-jade', { method: 'POST', body: formData });
  },

  // Export
  async exportPlot(
    schema: any,
    format: string = 'png',
    width: number = 1200,
    height: number = 800,
    scale: number = 2
  ): Promise<{ image_url: string }> {
    return request('/plot/export', {
      method: 'POST',
      body: JSON.stringify({ plot_schema: schema, format, width, height, scale }),
    });
  },

  // Themes
  async getThemes(): Promise<{ themes: any[] }> {
    return request('/plot/themes');
  },

  async applyTheme(schema: any, themeId: string): Promise<{ schema: any }> {
    return request('/plot/apply-theme', {
      method: 'POST',
      body: JSON.stringify({ plot_schema: schema, theme_id: themeId }),
    });
  },

  // RSM
  async generateRSMSurface3d(
    xData: number[], yData: number[], zData: number[], config: Record<string, any>
  ): Promise<{ schema: any }> {
    return request('/plot/rsm/surface3d', {
      method: 'POST',
      body: JSON.stringify({ x_data: xData, y_data: yData, z_data: zData, config }),
    });
  },

  async generateRSMContour(
    xData: number[], yData: number[], zData: number[], config: Record<string, any>
  ): Promise<{ schema: any }> {
    return request('/plot/rsm/contour', {
      method: 'POST',
      body: JSON.stringify({ x_data: xData, y_data: yData, z_data: zData, config }),
    });
  },

  async fitRSMModel(
    xData: number[], yData: number[], zData: number[], degree: number = 2
  ): Promise<any> {
    return request('/plot/rsm/fit-model', {
      method: 'POST',
      body: JSON.stringify({ x_data: xData, y_data: yData, z_data: zData, degree }),
    });
  },

  // Spectrum processing
  async spectrumBaseline(
    xData: number[], yData: number[], method: string = 'als', params: Record<string, any> = {}
  ): Promise<any> {
    return request('/plot/spectrum/baseline', {
      method: 'POST',
      body: JSON.stringify({ x_data: xData, y_data: yData, method, params }),
    });
  },

  async spectrumSmooth(
    yData: number[], method: string = 'savgol', params: Record<string, any> = {}
  ): Promise<any> {
    return request('/plot/spectrum/smooth', {
      method: 'POST',
      body: JSON.stringify({ y_data: yData, method, params }),
    });
  },

  async spectrumFindPeaks(
    xData: number[], yData: number[], params: Record<string, any> = {}
  ): Promise<any> {
    return request('/plot/spectrum/find-peaks', {
      method: 'POST',
      body: JSON.stringify({ x_data: xData, y_data: yData, params }),
    });
  },

  async spectrumFitPeaks(
    xData: number[], yData: number[], peakPositions: number[],
    peakType: string = 'pvoigt', config: Record<string, any> = {}
  ): Promise<{ schema: any; fit_result: any }> {
    return request('/plot/spectrum/fit-peaks', {
      method: 'POST',
      body: JSON.stringify({ x_data: xData, y_data: yData, peak_positions: peakPositions, peak_type: peakType, config }),
    });
  },

  // Raman
  async generateRamanSpectrum(xData: number[], yData: number[], config: Record<string, any> = {}): Promise<{ schema: any }> {
    return request('/plot/raman/spectrum', {
      method: 'POST',
      body: JSON.stringify({ x_data: xData, y_data: yData, config }),
    });
  },

  async generateRamanPeakFit(xData: number[], yData: number[], peakPositions: number[], config: Record<string, any> = {}): Promise<any> {
    return request('/plot/raman/peak-fit', {
      method: 'POST',
      body: JSON.stringify({ x_data: xData, y_data: yData, peak_positions: peakPositions, config }),
    });
  },

  // XPS
  async generateXPSSpectrum(xData: number[], yData: number[], config: Record<string, any> = {}): Promise<{ schema: any }> {
    return request('/plot/xps/spectrum', {
      method: 'POST',
      body: JSON.stringify({ x_data: xData, y_data: yData, config }),
    });
  },

  async generateXPSPeakFit(xData: number[], yData: number[], peakPositions: number[], config: Record<string, any> = {}): Promise<any> {
    return request('/plot/xps/peak-fit', {
      method: 'POST',
      body: JSON.stringify({ x_data: xData, y_data: yData, peak_positions: peakPositions, config }),
    });
  },

  // FTIR
  async generateFTIRSpectrum(xData: number[], yData: number[], config: Record<string, any> = {}): Promise<{ schema: any }> {
    return request('/plot/ftir/spectrum', {
      method: 'POST',
      body: JSON.stringify({ x_data: xData, y_data: yData, config }),
    });
  },

  // UV-Vis
  async generateUVVisSpectrum(xData: number[], yData: number[], config: Record<string, any> = {}): Promise<{ schema: any }> {
    return request('/plot/uvvis/spectrum', {
      method: 'POST',
      body: JSON.stringify({ x_data: xData, y_data: yData, config }),
    });
  },

  async generateTaucPlot(xData: number[], yData: number[], config: Record<string, any> = {}): Promise<{ schema: any }> {
    return request('/plot/uvvis/tauc', {
      method: 'POST',
      body: JSON.stringify({ x_data: xData, y_data: yData, config }),
    });
  },

  // Thermal
  async generateTGADSC(xData: number[], tgaData: number[], dscData: number[] | null, config: Record<string, any> = {}): Promise<{ schema: any }> {
    return request('/plot/thermal/tga-dsc', {
      method: 'POST',
      body: JSON.stringify({ x_data: xData, tga_data: tgaData, dsc_data: dscData, config }),
    });
  },

  // BET
  async generateBETIsotherm(pPoAds: number[], vAds: number[], pPoDes: number[] | null, vDes: number[] | null, config: Record<string, any> = {}): Promise<{ schema: any }> {
    return request('/plot/bet/isotherm', {
      method: 'POST',
      body: JSON.stringify({ p_po_ads: pPoAds, v_ads: vAds, p_po_des: pPoDes, v_des: vDes, config }),
    });
  },

  async generateBJHPore(poreDiameter: number[], dvDd: number[], config: Record<string, any> = {}): Promise<{ schema: any }> {
    return request('/plot/bet/pore-distribution', {
      method: 'POST',
      body: JSON.stringify({ pore_diameter: poreDiameter, dv_dd: dvDd, config }),
    });
  },

  // Statistics
  async generateAnovaBar(groups: any[], comparisons: any[], config: Record<string, any> = {}): Promise<{ schema: any }> {
    return request('/plot/stats/anova-bar', {
      method: 'POST',
      body: JSON.stringify({ groups, comparisons, config }),
    });
  },

  async generateCorrelationHeatmap(variables: string[], corrMatrix: number[][], pMatrix: number[][] | null, config: Record<string, any> = {}): Promise<{ schema: any }> {
    return request('/plot/stats/correlation-heatmap', {
      method: 'POST',
      body: JSON.stringify({ variables, corr_matrix: corrMatrix, p_matrix: pMatrix, config }),
    });
  },

  async generatePCABiplot(scores: number[][], loadings: number[][], varianceExplained: number[], groupLabels: string[] | null, variableNames: string[], config: Record<string, any> = {}): Promise<{ schema: any }> {
    return request('/plot/stats/pca-biplot', {
      method: 'POST',
      body: JSON.stringify({ scores, loadings, variance_explained: varianceExplained, group_labels: groupLabels, variable_names: variableNames, config }),
    });
  },

  // DOE
  async generatePareto(effects: any[], config: Record<string, any> = {}): Promise<{ schema: any }> {
    return request('/plot/rsm/pareto', {
      method: 'POST',
      body: JSON.stringify({ effects, config }),
    });
  },

  async generateMainEffects(factors: any[], config: Record<string, any> = {}): Promise<{ schema: any }> {
    return request('/plot/rsm/main-effects', {
      method: 'POST',
      body: JSON.stringify({ factors, config }),
    });
  },

  async generateInteraction(factor1Levels: number[], factor2Levels: number[], meansMatrix: number[][], factor1Name: string, factor2Name: string, config: Record<string, any> = {}): Promise<{ schema: any }> {
    return request('/plot/rsm/interaction', {
      method: 'POST',
      body: JSON.stringify({ factor1_levels: factor1Levels, factor2_levels: factor2Levels, means_matrix: meansMatrix, factor1_name: factor1Name, factor2_name: factor2Name, config }),
    });
  },
};
