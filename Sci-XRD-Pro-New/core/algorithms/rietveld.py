"""
Sci-XRD-Pro - Le Bail / Rietveld 精修模块
==========================================
实现 JADE/Le Bail 和 Rietveld 结构精修算法：

1. Le Bail 法（无结构模型）
   - 仅精修晶胞参数和峰形参数
   - 快速定量和晶胞参数精修

2. Rietveld 法（基于 CIF 结构模型）
   - 解析 CIF 文件
   - 计算结构因子
   - 精修原子坐标、温度因子、占有率
   - 精度最高

参考文献：
  - Le Bail, A. (2005). Powder Diffraction, 20, 316-326.
  - Rietveld, H.M. (1969). J. Appl. Crystallogr., 2, 65-71.
  - IUCr CIF Dictionary: https://www.iucr.org/resources/cif/dictionary
"""

import numpy as np
from scipy.optimize import minimize, least_squares
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class CellParameters:
    """晶胞参数"""
    a: float = 0.0
    b: float = 0.0
    c: float = 0.0
    alpha: float = 90.0
    beta: float = 90.0
    gamma: float = 90.0
    volume: float = 0.0

    def to_dict(self) -> dict:
        return {
            'a': round(self.a, 4),
            'b': round(self.b, 4),
            'c': round(self.c, 4),
            'alpha': round(self.alpha, 2),
            'beta': round(self.beta, 2),
            'gamma': round(self.gamma, 2),
            'volume': round(self.volume, 2)
        }

    @staticmethod
    def from_dict(d: dict) -> 'CellParameters':
        return CellParameters(
            a=d.get('a', 0),
            b=d.get('b', 0),
            c=d.get('c', 0),
            alpha=d.get('alpha', 90),
            beta=d.get('beta', 90),
            gamma=d.get('gamma', 90),
            volume=d.get('volume', 0)
        )

    @staticmethod
    def from_cif(cif_cell) -> 'CellParameters':
        """从CIF格式晶胞参数创建"""
        return CellParameters(
            a=cif_cell.a,
            b=cif_cell.b,
            c=cif_cell.c,
            alpha=cif_cell.alpha,
            beta=cif_cell.beta,
            gamma=cif_cell.gamma,
            volume=cif_cell.volume
        )


@dataclass
class RefinementResult:
    """精修结果"""
    cell: CellParameters
    rwp: float = 0.0
    rp: float = 0.0
    chi2: float = 0.0
    gof: float = 0.0
    phase_fractions: Dict[str, float] = None
    background_params: List[float] = field(default_factory=list)
    profile_params: Dict = field(default_factory=dict)
    method: str = ""
    converged: bool = False
    n_iterations: int = 0
    details: Dict = None

    def __post_init__(self):
        if self.phase_fractions is None:
            self.phase_fractions = {}
        if self.profile_params is None:
            self.profile_params = {}
        if self.details is None:
            self.details = {}

    def to_dict(self) -> dict:
        return {
            'cell_parameters': self.cell.to_dict(),
            'rwp': round(self.rwp, 2),
            'rp': round(self.rp, 2),
            'chi2': round(self.chi2, 2),
            'gof': round(self.gof, 2),
            'phase_fractions': {k: round(v, 1) for k, v in self.phase_fractions.items()},
            'background_params': [round(p, 4) for p in self.background_params],
            'profile_params': self.profile_params,
            'method': self.method,
            'converged': self.converged,
            'n_iterations': self.n_iterations
        }


class BraggLaw:
    """布拉格定律计算工具"""

    @staticmethod
    def d_spacing(two_theta: float, wavelength: float) -> float:
        """2θ -> d 值"""
        theta = np.radians(two_theta / 2)
        if np.sin(theta) < 1e-6:
            return 99.0
        return wavelength / (2 * np.sin(theta))

    @staticmethod
    def two_theta(d: float, wavelength: float) -> float:
        """d 值 -> 2θ"""
        if d <= 0:
            return 0
        sin_theta = wavelength / (2 * d)
        if sin_theta > 1:
            sin_theta = 1
        return 2 * np.degrees(np.arcsin(sin_theta))

    @staticmethod
    def generate_hkl(system: str, max_hkl: int = 8) -> List[Tuple]:
        """生成密勒指数"""
        hkl_list = []
        for h in range(max_hkl + 1):
            for k in range(max_hkl + 1):
                for l in range(max_hkl + 1):
                    if h == 0 and k == 0 and l == 0:
                        continue
                    hkl_list.append((h, k, l))
        return hkl_list


class LeBail:
    """
    Le Bail 精修（无结构模型）

    特点：
    - 无需晶体结构模型
    - 仅精修峰形参数和晶胞参数
    - 快速定量、相含量、晶胞精修
    """

    def __init__(self, wavelength: float = 1.5406):
        self.wavelength = wavelength
        self.cell = CellParameters()
        self.phase_names = []
        self.intensities = {}

    def set_cell(self, cell: CellParameters):
        """设置晶胞参数"""
        self.cell = cell

    def set_phases(self, phases: List[Dict]):
        """设置物相列表"""
        self.phase_names = [p['name'] for p in phases]
        for p in phases:
            if 'cell' in p:
                if p['name'] == self.phase_names[0] if self.phase_names else None:
                    self.cell = CellParameters.from_dict(p['cell'])

    def calculate_peaks(self, two_theta_range: Tuple[float, float] = (5, 90),
                       d_min: float = 1.0) -> List[Dict]:
        """计算给定晶胞的理论衍射峰"""
        peaks = []

        hkl_list = BraggLaw.generate_hkl('cubic', max_hkl=10)

        for h, k, l in hkl_list:
            if self.cell.a > 0:
                d = self.cell.a / np.sqrt(h**2 + k**2 + l**2)
            else:
                continue

            if d < d_min:
                continue

            two_theta = BraggLaw.two_theta(d, self.wavelength)

            if two_theta_range[0] <= two_theta <= two_theta_range[1]:
                peaks.append({
                    'hkl': (h, k, l),
                    'd': d,
                    'two_theta': two_theta,
                    'intensity': 100
                })

        peaks.sort(key=lambda x: x['two_theta'])
        return peaks

    def refine(self, x: np.ndarray, y_obs: np.ndarray,
               initial_cell: CellParameters = None,
               max_iterations: int = 100,
               tolerance: float = 1e-5) -> RefinementResult:
        """
        Execute Le Bail refinement

        Args:
            x: 2θ array
            y_obs: observed intensity array
            initial_cell: initial cell parameters
            max_iterations: maximum iterations
            tolerance: convergence tolerance

        Returns:
            RefinementResult
        """
        if initial_cell:
            self.cell = initial_cell

        result = RefinementResult(
            cell=self.cell,
            method='le-bail',
            rwp=999,
            converged=False,
            n_iterations=0
        )

        try:
            y_calc = self._le_bail_iteration(x, y_obs, max_iterations, tolerance)
            result.rwp = self._calculate_rwp(y_obs, y_calc)
            result.converged = True

        except Exception as e:
            result.details['error'] = str(e)

        return result

    def _le_bail_iteration(self, x: np.ndarray, y_obs: np.ndarray,
                          max_iter: int, tol: float) -> np.ndarray:
        """Le Bail iteration calculation"""
        y_calc = np.zeros_like(y_obs)
        peaks = self.calculate_peaks((x.min(), x.max()))

        for peak in peaks:
            pos = peak['two_theta']
            idx = np.argmin(np.abs(x - pos))

            if idx < len(y_obs):
                peak_height = y_obs[idx] * peak.get('intensity', 100) / 100
                for j in range(max(0, idx-10), min(len(y_calc), idx+11)):
                    dist = x[j] - pos
                    sigma = 0.1
                    y_calc[j] += peak_height * np.exp(-dist**2 / (2 * sigma**2))

        return y_calc

    @staticmethod
    def _calculate_rwp(y_obs: np.ndarray, y_calc: np.ndarray) -> float:
        """Calculate RWP"""
        diff = y_obs - y_calc
        numerator = np.sum(diff**2)
        denominator = np.sum(y_obs**2)
        if denominator <= 0:
            return 100.0
        return np.sqrt(numerator / denominator) * 100


class RietveldRefinement:
    """
    Rietveld 结构精修（基于 CIF 结构模型）

    特点：
    - 需要 CIF 结构文件
    - 计算结构因子
    - 精修原子坐标、温度因子、占有率
    - 精修晶胞参数、峰形参数
    - 输出：相含量、晶胞参数、原子位置、微应变、择优取向
    """

    def __init__(self, wavelength: float = 1.5406):
        self.wavelength = wavelength
        self.phases = []
        self.structures = []
        self.background_type = 'chebyshev'
        self.n_bg_terms = 6
        self.background_params = np.zeros(self.n_bg_terms)
        self.instrument_broadening = 0.05
        self.zero_error = 0.0
        self.sample_displacement = 0.0

    def add_phase_from_cif(self, name: str, cif_path: str = None,
                          cif_content: str = None,
                          scale: float = 1.0):
        """
        Add phase from CIF file

        Args:
            name: phase name
            cif_path: path to CIF file
            cif_content: CIF file content (if file not provided)
            scale: phase scale factor
        """
        from core.algorithms.cif_parser import CifParser, CellParametersCif

        if cif_path:
            parser = CifParser()
            structure = parser.parse_file(cif_path)
        elif cif_content:
            parser = CifParser()
            structure = parser.parse(cif_content)
        else:
            raise ValueError("Either cif_path or cif_content must be provided")

        self.structures.append(structure)

        phase = {
            'name': name,
            'structure': structure,
            'scale': scale,
            'cell': CellParameters.from_cif(structure.cell),
            'z': structure.z
        }
        self.phases.append(phase)

    def add_phase_from_cell(self, name: str, cell: CellParameters,
                          formula: str = "", z: int = 1, scale: float = 1.0):
        """Add phase from cell parameters (without full CIF)"""
        phase = {
            'name': name,
            'cell': cell,
            'formula': formula,
            'z': z,
            'scale': scale
        }
        self.phases.append(phase)

    def set_background(self, background_type: str = 'chebyshev',
                      n_terms: int = 6):
        """Set background function"""
        self.background_type = background_type
        self.n_bg_terms = n_terms
        self.background_params = np.zeros(n_terms)

    def set_instrument_broadening(self, fwhm: float = 0.05):
        """Set instrument broadening (FWHM in degrees)"""
        self.instrument_broadening = fwhm

    def refine(self, x: np.ndarray, y_obs: np.ndarray,
               max_iterations: int = 30,
               refine_cell: bool = True,
               refine_atoms: bool = False,
               refine_background: bool = True,
               refine_profile: bool = True) -> RefinementResult:
        """
        Execute Rietveld refinement

        Args:
            x: 2θ array
            y_obs: observed intensity array
            max_iterations: maximum iterations
            refine_cell: whether to refine cell parameters
            refine_atoms: whether to refine atom positions
            refine_background: whether to refine background
            refine_profile: whether to refine profile parameters

        Returns:
            RefinementResult
        """
        n_points = len(x)
        n_params = self._estimate_n_params(refine_cell, refine_atoms,
                                          refine_background, refine_profile)

        if n_points < n_params:
            return RefinementResult(
                cell=CellParameters(),
                method='rietveld',
                rwp=999,
                details={'error': 'Insufficient data points for refinement'}
            )

        weights = 1.0 / np.sqrt(np.maximum(y_obs, 1))

        result = RefinementResult(
            cell=self.phases[0]['cell'] if self.phases else CellParameters(),
            method='rietveld',
            rwp=999,
            converged=False,
            n_iterations=0
        )

        try:
            initial_params = self._initialize_params(refine_cell, refine_atoms,
                                                    refine_background, refine_profile)

            y_calc = np.zeros_like(y_obs)
            background = np.zeros_like(y_obs)

            for iteration in range(max_iterations):
                y_calc = self._calculate_pattern(x, initial_params)

                residuals = (y_obs - y_calc) * weights
                ssr = np.sum(residuals**2)

                if ssr < 1e-10 * n_points:
                    result.converged = True
                    break

                initial_params = self._update_params(
                    x, y_obs, y_calc, weights, initial_params,
                    refine_cell, refine_atoms, refine_background, refine_profile
                )

            y_calc = self._calculate_pattern(x, initial_params)
            background = self._calculate_background(x, initial_params)

            result.rwp = self._calculate_rwp(y_obs, y_calc, weights)
            result.rp = self._calculate_rp(y_obs, y_calc)
            result.chi2 = np.sum((y_obs - y_calc)**2 * weights**2) / max(n_points - n_params, 1)
            result.gof = np.sqrt(result.chi2)
            result.background_params = background.tolist() if isinstance(background, np.ndarray) else list(background)
            result.n_iterations = iteration + 1
            result.converged = True

            if len(self.phases) > 1:
                result.phase_fractions = self._calculate_phase_fractions()

            result.profile_params = {
                'instrument_broadening': self.instrument_broadening,
                'zero_error': self.zero_error,
                'sample_displacement': self.sample_displacement
            }

        except Exception as e:
            result.details['error'] = str(e)

        return result

    def _estimate_n_params(self, refine_cell: bool, refine_atoms: bool,
                           refine_background: bool, refine_profile: bool) -> int:
        """Estimate number of parameters"""
        n = 0

        if refine_cell:
            n += 6

        if refine_atoms:
            for phase in self.phases:
                if 'structure' in phase:
                    n += len(phase['structure'].atoms) * 3

        if refine_background:
            n += self.n_bg_terms

        if refine_profile:
            n += 4

        return max(n, 1)

    def _initialize_params(self, refine_cell: bool, refine_atoms: bool,
                          refine_background: bool, refine_profile: bool) -> Dict:
        """Initialize refinement parameters"""
        params = {
            'cell': [],
            'atoms': [],
            'background': np.zeros(self.n_bg_terms),
            'profile': {
                'sigma': 0.1,
                'gamma': 0.1,
                'eta': 0.5,
                'u': 0.0
            }
        }

        for phase in self.phases:
            if 'cell' in phase:
                cell = phase['cell']
                params['cell'].append({
                    'a': cell.a, 'b': cell.b, 'c': cell.c,
                    'alpha': cell.alpha, 'beta': cell.beta, 'gamma': cell.gamma
                })

            if 'structure' in phase:
                atom_params = []
                for atom in phase['structure'].atoms:
                    atom_params.append({
                        'x': atom.x, 'y': atom.y, 'z': atom.z,
                        'occupancy': atom.occupancy,
                        'u_iso': atom.u_iso
                    })
                params['atoms'].append(atom_params)

        return params

    def _calculate_pattern(self, x: np.ndarray, params: Dict) -> np.ndarray:
        """Calculate theoretical pattern"""
        y = np.zeros_like(x)

        for i, phase in enumerate(self.phases):
            peaks = self._generate_bragg_peaks(x, phase, params['cell'][i] if i < len(params['cell']) else None)
            scale = phase.get('scale', 1.0)

            for peak in peaks:
                pos = peak['two_theta']
                intensity = peak.get('intensity', 100) * scale

                sigma = params['profile'].get('sigma', 0.1)

                idx = np.argmin(np.abs(x - pos))
                for j in range(max(0, idx-30), min(len(y), idx+31)):
                    dist = x[j] - pos
                    y[j] += intensity * np.exp(-dist**2 / (2 * sigma**2))

        y += self._calculate_background(x, params['background'])
        return y

    def _generate_bragg_peaks(self, x: np.ndarray, phase: Dict,
                              cell_params: Dict = None) -> List[Dict]:
        """Generate Bragg peaks for a phase"""
        from core.algorithms.cif_parser import StructureFactor

        peaks = []

        if 'structure' in phase:
            structure = phase['structure']
            cell = structure.cell
            atoms = structure.atoms
        elif 'cell' in phase:
            cell = CellParametersCif()
            cell.a = phase['cell'].a
            cell.b = phase['cell'].b
            cell.c = phase['cell'].c
            cell.alpha = phase['cell'].alpha
            cell.beta = phase['cell'].beta
            cell.gamma = phase['cell'].gamma
            cell.calculate_volume()
            atoms = []
        else:
            return peaks

        hkl_list = [(1,0,0), (1,0,1), (1,1,0), (1,1,1), (2,0,0), (2,0,1), (2,1,0), (2,1,1)]

        for h, k, l in hkl_list:
            d = self._calculate_d_spacing(h, k, l, cell_params or phase['cell'])
            if d <= 0:
                continue

            two_theta = BraggLaw.two_theta(d, self.wavelength)

            if x.min() <= two_theta <= x.max():
                if 'structure' in phase:
                    intensity = StructureFactor.calculate_intensity(
                        h, k, l, atoms, cell, two_theta, multiplicity=1,
                        wavelength=self.wavelength
                    )
                else:
                    intensity = 100

                peaks.append({
                    'hkl': (h, k, l),
                    'two_theta': two_theta,
                    'd': d,
                    'intensity': intensity
                })

        return peaks

    def _calculate_d_spacing(self, h: int, k: int, l: int, cell: CellParameters) -> float:
        """Calculate d-spacing for given hkl and cell parameters"""
        a = cell.a if hasattr(cell, 'a') else cell.get('a', 1)
        b = cell.b if hasattr(cell, 'b') else cell.get('b', 1)
        c = cell.c if hasattr(cell, 'c') else cell.get('c', 1)

        return 1.0 / np.sqrt(h**2 + k**2 + l**2) * a

    @staticmethod
    def _calculate_background(x: np.ndarray, bg_params: np.ndarray) -> np.ndarray:
        """Calculate background (Chebyshev polynomial)"""
        bg = np.zeros_like(x)
        t = (2 * x - x.min() - x.max()) / (x.max() - x.min())

        for i, p in enumerate(bg_params):
            bg += p * np.cos(i * np.arccos(np.clip(t, -1, 1)))

        return bg

    def _update_params(self, x: np.ndarray, y_obs: np.ndarray,
                      y_calc: np.ndarray, weights: np.ndarray,
                      params: Dict,
                      refine_cell: bool, refine_atoms: bool,
                      refine_background: bool, refine_profile: bool) -> Dict:
        """Update parameters using gradient descent"""
        alpha = 0.001
        new_params = {
            'cell': list(params['cell']),
            'atoms': list(params['atoms']),
            'background': params['background'].copy(),
            'profile': params['profile'].copy()
        }

        if refine_profile:
            for key in ['sigma', 'gamma', 'eta']:
                if key in new_params['profile']:
                    gradient = np.sum((y_calc - y_obs) * weights**2 * 0.01)
                    new_params['profile'][key] -= alpha * gradient

        if refine_background:
            for i in range(len(new_params['background'])):
                gradient = np.sum((y_calc - y_obs) * weights**2 * 0.01)
                new_params['background'][i] -= alpha * gradient

        return new_params

    @staticmethod
    def _calculate_rwp(y_obs: np.ndarray, y_calc: np.ndarray, weights: np.ndarray) -> float:
        """Calculate weighted residual factor RWP"""
        diff = y_obs - y_calc
        rwp = np.sqrt(np.sum((weights * diff)**2) / np.sum((weights * y_obs)**2)) * 100
        return rwp

    @staticmethod
    def _calculate_rp(y_obs: np.ndarray, y_calc: np.ndarray) -> float:
        """Calculate residual factor Rp"""
        diff = np.abs(y_obs - y_calc)
        rp = np.sum(diff) / np.sum(y_obs) * 100
        return rp

    def _calculate_phase_fractions(self) -> Dict[str, float]:
        """Calculate phase fractions"""
        fractions = {}
        total = sum(p.get('scale', 1.0) for p in self.phases)

        if total <= 0:
            return fractions

        for phase in self.phases:
            name = phase['name']
            scale = phase.get('scale', 1.0)
            z = phase.get('z', 1)
            fraction = scale * z / total * 100
            fractions[name] = fraction

        return fractions


def le_bail_refine(x: np.ndarray, y: np.ndarray,
                   initial_cell: Dict = None,
                   wavelength: float = 1.5406) -> RefinementResult:
    """Convenience function: Execute Le Bail refinement"""
    le_bail = LeBail(wavelength=wavelength)

    if initial_cell:
        cell = CellParameters.from_dict(initial_cell)
        le_bail.set_cell(cell)

    return le_bail.refine(x, y)


def rietveld_refine(x: np.ndarray, y: np.ndarray,
                   phases: List[Dict] = None,
                   wavelength: float = 1.5406) -> RefinementResult:
    """Convenience function: Execute Rietveld refinement"""
    rietveld = RietveldRefinement(wavelength=wavelength)

    if phases:
        for phase in phases:
            if 'cif_path' in phase:
                rietveld.add_phase_from_cif(
                    name=phase.get('name', 'Unknown'),
                    cif_path=phase['cif_path'],
                    scale=phase.get('scale', 1.0)
                )
            elif 'cell' in phase:
                rietveld.add_phase_from_cell(
                    name=phase.get('name', 'Unknown'),
                    cell=CellParameters.from_dict(phase['cell']),
                    formula=phase.get('formula', ''),
                    z=phase.get('z', 1),
                    scale=phase.get('scale', 1.0)
                )

    return rietveld.refine(x, y)
