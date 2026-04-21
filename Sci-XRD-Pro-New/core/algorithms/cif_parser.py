"""
Sci-XRD-Pro - CIF 结构文件解析器
==========================================
实现 CIF (Crystallographic Information File) 解析：

支持：
  - 晶胞参数 (cell)
  - 原子坐标 (atom_site)
  - 空间群 (space_group)
  - 化学式 (chemical_formula)
  - 结构因子计算

参考文献：
  - IUCr CIF Dictionary: https://www.iucr.org/resources/cif/dictionary
  - Hall, S.R. et al. (1991). Acta Cryst. A47, 655-685.
"""

import re
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class AtomSite:
    """原子位置信息"""
    label: str
    type_symbol: str
    x: float
    y: float
    z: float
    occupancy: float = 1.0
    adp_type: str = "Uiso"
    u_iso: float = 0.0
    u_eq: float = 0.0
    charge: float = 0.0
    multiplicity: int = 1

    def to_dict(self) -> dict:
        return {
            'label': self.label,
            'type_symbol': self.type_symbol,
            'x': round(self.x, 6),
            'y': round(self.y, 6),
            'z': round(self.z, 6),
            'occupancy': round(self.occupancy, 4),
            'adp_type': self.adp_type,
            'u_iso': round(self.u_iso, 6),
            'u_eq': round(self.u_eq, 6)
        }


@dataclass
class SpaceGroup:
    """空间群信息"""
    name: str
    it_number: int = 0
    hall_symbol: str = ""
    international_short: str = ""
    point_group: str = ""
    crystal_system: str = ""

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'it_number': self.it_number,
            'hall_symbol': self.hall_symbol,
            'international_short': self.international_short,
            'point_group': self.point_group,
            'crystal_system': self.crystal_system
        }


@dataclass
class CifStructure:
    """完整 CIF 结构"""
    cell: 'CellParametersCif'
    atoms: List[AtomSite]
    space_group: SpaceGroup
    formula: str = ""
    formula_weight: float = 0.0
    z: int = 1
    density: float = 0.0
    title: str = ""

    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'formula': self.formula,
            'formula_weight': round(self.formula_weight, 4),
            'z': self.z,
            'density': round(self.density, 4),
            'cell': self.cell.to_dict() if hasattr(self.cell, 'to_dict') else {},
            'space_group': self.space_group.to_dict(),
            'atoms': [a.to_dict() for a in self.atoms]
        }


class CellParametersCif:
    """CIF 格式晶胞参数"""

    def __init__(self):
        self.a: float = 0.0
        self.b: float = 0.0
        self.c: float = 0.0
        self.alpha: float = 90.0
        self.beta: float = 90.0
        self.gamma: float = 90.0
        self.volume: float = 0.0
        self.length_a_err: float = 0.0
        self.length_b_err: float = 0.0
        self.length_c_err: float = 0.0
        self.angle_alpha_err: float = 0.0
        self.angle_beta_err: float = 0.0
        self.angle_gamma_err: float = 0.0

    def calculate_volume(self):
        """计算晶胞体积"""
        a, b, c = self.a, self.b, self.c
        alpha, beta, gamma = np.radians([self.alpha, self.beta, self.gamma])

        vol = a * b * c * np.sqrt(
            1 + 2*np.cos(alpha)*np.cos(beta)*np.cos(gamma)
            - np.cos(alpha)**2 - np.cos(beta)**2 - np.cos(gamma)**2
        )
        self.volume = vol
        return vol

    def to_dict(self) -> dict:
        return {
            'a': round(self.a, 4),
            'b': round(self.b, 4),
            'c': round(self.c, 4),
            'alpha': round(self.alpha, 2),
            'beta': round(self.beta, 2),
            'gamma': round(self.gamma, 2),
            'volume': round(self.volume, 2),
            'a_err': round(self.length_a_err, 4),
            'b_err': round(self.length_b_err, 4),
            'c_err': round(self.length_c_err, 4)
        }


class CifParser:
    """
    CIF 文件解析器

    支持标准 CIF 1.1 格式
    """

    def __init__(self):
        self.data: Dict = {}
        self.loop_data: Dict = {}

    def parse(self, content: str) -> CifStructure:
        """
        解析 CIF 文件内容

        Args:
            content: CIF 文件字符串

        Returns:
            CifStructure 对象
        """
        lines = content.split('\n')

        self._parse_blocks(lines)

        cell = self._parse_cell()
        atoms = self._parse_atoms()
        space_group = self._parse_space_group()
        formula = self._get_value('_chemical_formula_sum') or self._get_value('_chemical_formula_moiety', '')
        z = int(float(self._get_value('_cell_formula_units_z', '1')))
        title = self._get_value('_audit_creation_date', 'Unknown')

        structure = CifStructure(
            cell=cell,
            atoms=atoms,
            space_group=space_group,
            formula=formula,
            z=z,
            title=title
        )

        if cell.volume == 0:
            cell.calculate_volume()

        structure.formula_weight = self._calculate_formula_weight(formula)

        if cell.volume > 0 and z > 0:
            na = len(atoms) if atoms else 1
            structure.density = (structure.formula_weight * z) / (cell.volume * 0.6022)

        return structure

    def parse_file(self, filepath: str) -> CifStructure:
        """解析 CIF 文件"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return self.parse(content)

    def _parse_blocks(self, lines: List[str]):
        """解析数据块"""
        current_block = None
        in_loop = False
        loop_keys = []
        loop_values = []
        in_quoted = False
        quote_char = None

        for line in lines:
            stripped = line.strip()

            if not stripped or stripped.startswith('#'):
                continue

            if stripped.startswith('data_'):
                current_block = stripped[5:].strip()
                self.data[current_block] = {}
                in_loop = False
                continue

            if in_loop:
                if stripped.startswith('_'):
                    if loop_values:
                        for i, key in enumerate(loop_keys):
                            val = loop_values[i] if i < len(loop_values) else ''
                            self.data[current_block][key] = val
                        loop_values = []
                    loop_keys.append(stripped)
                elif stripped.startswith(';') or stripped.startswith("'"):
                    in_quoted = not in_quoted
                    quote_char = stripped[0]
                elif not in_quoted:
                    loop_values.append(stripped)
                continue

            if stripped.startswith('_'):
                key, value = self._parse_tag_value(stripped)
                if current_block:
                    self.data[current_block][key] = value

            elif stripped.lower().startswith('loop_'):
                in_loop = True
                loop_keys = []
                loop_values = []

            elif stripped.startswith('_'):
                key, value = self._parse_tag_value(stripped)
                if current_block:
                    self.data[current_block][key] = value

    def _parse_tag_value(self, line: str) -> Tuple[str, str]:
        """解析标签和值"""
        parts = line.split(None, 1)
        key = parts[0] if parts else ''
        value = parts[1] if len(parts) > 1 else ''
        value = value.strip().strip('"').strip("'").strip()
        return key, value

    def _get_value(self, key: str, default: str = '') -> str:
        """获取值"""
        for block_data in self.data.values():
            if key in block_data:
                return block_data[key]
        return default

    def _parse_cell(self) -> CellParametersCif:
        """解析晶胞参数"""
        cell = CellParametersCif()

        def get_float(key: str, default: float = 0.0) -> float:
            val = self._get_value(key)
            try:
                return float(val)
            except:
                return default

        cell.a = get_float('_cell_length_a')
        cell.b = get_float('_cell_length_b')
        cell.c = get_float('_cell_length_c')
        cell.alpha = get_float('_cell_angle_alpha')
        cell.beta = get_float('_cell_angle_beta')
        cell.gamma = get_float('_cell_angle_gamma')
        cell.length_a_err = get_float('_cell_length_a_esd', 0)
        cell.length_b_err = get_float('_cell_length_b_esd', 0)
        cell.length_c_err = get_float('_cell_length_c_esd', 0)
        cell.angle_alpha_err = get_float('_cell_angle_alpha_esd', 0)
        cell.beta_err = get_float('_cell_angle_beta_esd', 0)
        cell.gamma_err = get_float('_cell_angle_gamma_esd', 0)

        cell.calculate_volume()
        return cell

    def _parse_atoms(self) -> List[AtomSite]:
        """解析原子位置"""
        atoms = []

        keys = [
            '_atom_site_label', '_atom_site_type_symbol',
            '_atom_site_fract_x', '_atom_site_fract_y', '_atom_site_fract_z',
            '_atom_site_occupancy', '_atom_site_adp_type',
            '_atom_site_u_iso_or_equiv', '_atom_site_charge'
        ]

        block = None
        for b in self.data.values():
            block = b
            break

        if not block:
            return atoms

        label_key = '_atom_site_label'
        type_key = '_atom_site_type_symbol'
        x_key = '_atom_site_fract_x'
        y_key = '_atom_site_fract_y'
        z_key = '_atom_site_fract_z'
        occ_key = '_atom_site_occupancy'
        adp_key = '_atom_site_adp_type'
        u_key = '_atom_site_u_iso_or_equiv'

        if label_key not in block:
            return atoms

        labels = block.get(label_key, '').split()
        if isinstance(labels, str):
            labels = [labels]

        type_symbols = block.get(type_key, '').split()
        if isinstance(type_symbols, str):
            type_symbols = [type_symbols]

        x_coords = block.get(x_key, '').split()
        if isinstance(x_coords, str):
            x_coords = [x_coords]

        y_coords = block.get(y_key, '').split()
        if isinstance(y_coords, str):
            y_coords = [y_coords]

        z_coords = block.get(z_key, '').split()
        if isinstance(z_coords, str):
            z_coords = [z_coords]

        occ_values = block.get(occ_key, '').split()
        if isinstance(occ_values, str):
            occ_values = [occ_values]

        adp_types = block.get(adp_key, '').split()
        if isinstance(adp_types, str):
            adp_types = [adp_types]

        u_values = block.get(u_key, '').split()
        if isinstance(u_values, str):
            u_values = [u_values]

        n_atoms = min(len(labels), len(x_coords), len(y_coords), len(z_coords))

        for i in range(n_atoms):
            try:
                atom = AtomSite(
                    label=labels[i] if i < len(labels) else f'Atom{i}',
                    type_symbol=type_symbols[i] if i < len(type_symbols) else 'X',
                    x=float(x_coords[i]) if i < len(x_coords) else 0.0,
                    y=float(y_coords[i]) if i < len(y_coords) else 0.0,
                    z=float(z_coords[i]) if i < len(z_coords) else 0.0,
                    occupancy=float(occ_values[i]) if i < len(occ_values) and occ_values[i] else 1.0,
                    adp_type=adp_types[i] if i < len(adp_types) and adp_types[i] else 'Uiso',
                    u_iso=float(u_values[i]) if i < len(u_values) and u_values[i] else 0.0,
                    u_eq=float(u_values[i]) if i < len(u_values) and u_values[i] else 0.0
                )
                atoms.append(atom)
            except (ValueError, IndexError):
                continue

        return atoms

    def _parse_space_group(self) -> SpaceGroup:
        """解析空间群"""
        sg = SpaceGroup(name='')

        sg.hall_symbol = self._get_value('_space_group_hall', '')
        sg.international_short = self._get_value('_space_group_name_IT_addenda', '')
        sg.name = self._get_value('_space_group_name_H-M_alt', sg.international_short)

        it_num_str = self._get_value('_space_group_IT_number', '0')
        try:
            sg.it_number = int(float(it_num_str))
        except:
            sg.it_number = 0

        sg.crystal_system = self._get_value('_symmetry_cell_setting', '')

        return sg

    @staticmethod
    def _calculate_formula_weight(formula: str) -> float:
        """计算化学式分子量"""
        from core.algorithms.element_constrained_search import ElementExtractor
        return ElementExtractor.formula_weight(formula)


class StructureFactor:
    """
    结构因子计算

    F(hkl) = Σ f_j * exp[2πi (h*x_j + k*y_j + l*z_j)]

    其中 f_j 是原子散射因子
    """

    ELEMENT_SCATTER_FACTORS = {
        'H': 1.0, 'C': 6.0, 'N': 7.0, 'O': 8.0,
        'Fe': 26.0, 'Cu': 29.0, 'Zn': 30.0, 'S': 16.0
    }

    @staticmethod
    def calculate_f(h: int, k: int, l: int, atoms: List[AtomSite],
                   cell: CellParametersCif, two_theta: float,
                   wavelength: float = 1.5406) -> complex:
        """
        计算结构因子

        Args:
            h, k, l: 密勒指数
            atoms: 原子列表
            cell: 晶胞参数
            two_theta: 布拉格角
            wavelength: 波长

        Returns:
            复数结构因子
        """
        f_total = 0j

        for atom in atoms:
            theta = np.radians(two_theta / 2)
            sin_theta = np.sin(theta)
            if sin_theta <= 0:
                continue

            f_j = StructureFactor._scattering_factor(
                atom.type_symbol, sin_theta, wavelength
            )

            phase = 2 * np.pi * (h * atom.x + k * atom.y + l * atom.z)
            f_total += f_j * atom.occupancy * (np.cos(phase) + 1j * np.sin(phase))

        return f_total

    @staticmethod
    def _scattering_factor(element: str, sin_theta: float,
                          wavelength: float) -> float:
        """
        计算原子散射因子（简化模型）

        f = Z - 41.782 * s^2 * Σ(A_i * exp(-B_i * s^2))
        其中 s = sinθ/λ
        """
        s = sin_theta / wavelength

        z = StructureFactor.ELEMENT_SCATTER_FACTORS.get(element, 6.0)

        a_coeffs = [0.4, 0.3, 0.2, 0.1]
        b_coeffs = [2.0, 4.0, 8.0, 16.0]

        decay = sum(a * np.exp(-b * s**2) for a, b in zip(a_coeffs, b_coeffs))
        f = z - 41.782 * s**2 * decay

        return max(f, 0.1)

    @staticmethod
    def calculate_intensity(h: int, k: int, l: int, atoms: List[AtomSite],
                           cell: CellParametersCif, two_theta: float,
                           multiplicity: int = 1, wavelength: float = 1.5406) -> float:
        """
        计算衍射强度

        I(hkl) = |F(hkl)|^2 * L * P * A * M

        其中：
          L = Lorentz factor
          P = Polarization factor
          A = Absorption factor
          M = Multiplicity
        """
        f = StructureFactor.calculate_f(h, k, l, atoms, cell, two_theta, wavelength)

        intensity = abs(f)**2

        lorentz_pol = 1 / (np.sin(np.radians(two_theta / 2))**2)
        intensity *= lorentz_pol * 0.5

        if multiplicity > 0:
            intensity *= multiplicity

        return intensity


def parse_cif(filepath: str) -> CifStructure:
    """便捷函数：解析 CIF 文件"""
    parser = CifParser()
    return parser.parse_file(filepath)


def parse_cif_content(content: str) -> CifStructure:
    """便捷函数：解析 CIF 内容"""
    parser = CifParser()
    return parser.parse(content)
