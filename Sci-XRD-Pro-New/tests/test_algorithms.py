"""
Sci-XRD-Pro - 单元测试模块
==========================================
测试核心算法模块的正确性

测试覆盖：
  1. peak_detection - 峰检测算法
  2. phase_matching - 物相匹配算法
  3. xrd_preprocessor - 预处理算法
  4. microstructure - 微观结构分析
  5. rietveld - Le Bail / Rietveld 精修
  6. cif_parser - CIF 文件解析
  7. element_constrained_search - 元素限定检索
  8. enhanced_profile - 增强峰形拟合
  9. whole_pattern_fit - 全谱拟合
"""

import unittest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBraggLaw(unittest.TestCase):
    """测试布拉格定律计算"""

    def test_d_spacing_calculation(self):
        """测试 2θ -> d 值转换"""
        from core.algorithms.rietveld import BraggLaw

        d = BraggLaw.d_spacing(two_theta=30.0, wavelength=1.5406)
        self.assertAlmostEqual(d, 2.98, places=1)

    def test_two_theta_calculation(self):
        """测试 d 值 -> 2θ 转换"""
        from core.algorithms.rietveld import BraggLaw

        two_theta = BraggLaw.two_theta(d=3.0, wavelength=1.5406)
        self.assertAlmostEqual(two_theta, 29.8, places=1)


class TestElementExtractor(unittest.TestCase):
    """测试元素提取器"""

    def test_extract_simple_formula(self):
        """测试简单化学式"""
        from core.algorithms.element_constrained_search import ElementExtractor

        elements = ElementExtractor.extract('Al2O3')
        self.assertIn('Al', elements)
        self.assertIn('O', elements)
        self.assertEqual(len(elements), 2)

    def test_extract_complex_formula(self):
        """测试复杂化学式"""
        from core.algorithms.element_constrained_search import ElementExtractor

        elements = ElementExtractor.extract('Fe0.5Cr0.5')
        self.assertIn('Fe', elements)
        self.assertIn('Cr', elements)

    def test_formula_weight(self):
        """测试分子量计算"""
        from core.algorithms.element_constrained_search import ElementExtractor

        mw = ElementExtractor.formula_weight('H2O')
        self.assertGreater(mw, 15)
        self.assertLess(mw, 20)


class TestCellParameters(unittest.TestCase):
    """测试晶胞参数"""

    def test_cell_from_dict(self):
        """Test cell creation from dict"""
        from core.algorithms.rietveld import CellParameters

        cell = CellParameters.from_dict({
            'a': 5.0, 'b': 5.0, 'c': 5.0,
            'alpha': 90, 'beta': 90, 'gamma': 90
        })
        self.assertEqual(cell.a, 5.0)
        self.assertEqual(cell.b, 5.0)
        self.assertEqual(cell.c, 5.0)


class TestMicrostructure(unittest.TestCase):
    """测试微观结构分析"""

    def test_scherrer_analysis(self):
        """测试谢乐公式"""
        from core.algorithms.microstructure import ScherrerAnalysis

        analyzer = ScherrerAnalysis(wavelength=1.5406)

        peaks = [
            {'position': 30.0, 'fwhm': 0.5, 'intensity': 100},
            {'position': 45.0, 'fwhm': 0.6, 'intensity': 80},
        ]

        result = analyzer.analyze(peaks, instrument_broadening=0.05)
        self.assertIsNotNone(result)
        self.assertEqual(result.method, 'scherrer')

    def test_williamson_hall(self):
        """测试 Williamson-Hall 分析"""
        from core.algorithms.microstructure import WilliamsonHall

        wh = WilliamsonHall(wavelength=1.5406)

        peaks = [
            {'position': 30.0, 'fwhm': 0.5, 'intensity': 100},
            {'position': 45.0, 'fwhm': 0.6, 'intensity': 80},
            {'position': 60.0, 'fwhm': 0.8, 'intensity': 60},
        ]

        result = wh.analyze(peaks)
        self.assertIsNotNone(result)
        self.assertIn(result.method, ['williamson-hall', 'williamson-hall-uniform'])


class TestCifParser(unittest.TestCase):
    """测试 CIF 解析器"""

    def test_parse_simple_cif(self):
        """测试简单 CIF 内容解析"""
        from core.algorithms.cif_parser import CifParser

        cif_content = """
data_test
_chemical_formula_sum 'Al2 O3'
_cell_length_a 4.759
_cell_length_b 4.759
_cell_length_c 12.991
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 120
_space_group_IT_number 167
_atom_site_label 'Al1'
_atom_site_type_symbol Al
_atom_site_fract_x 0.0
_atom_site_fract_y 0.0
_atom_site_fract_z 0.352
"""

        parser = CifParser()
        structure = parser.parse(cif_content)

        self.assertEqual(structure.formula, 'Al2 O3')
        self.assertGreater(structure.cell.a, 4.0)
        self.assertLess(structure.cell.a, 5.0)
        self.assertGreater(len(structure.atoms), 0)

    def test_structure_to_dict(self):
        """测试结构转换为字典"""
        from core.algorithms.cif_parser import CifParser

        cif_content = """
data_test
_chemical_formula_sum 'Si'
_cell_length_a 5.431
_cell_length_b 5.431
_cell_length_c 5.431
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
_space_group_IT_number 227
"""

        parser = CifParser()
        structure = parser.parse(cif_content)
        d = structure.to_dict()

        self.assertIn('cell', d)
        self.assertIn('space_group', d)
        self.assertEqual(d['formula'], 'Si')


class TestElementConstraint(unittest.TestCase):
    """测试元素约束检索"""

    def test_check_compatibility(self):
        """Test element compatibility check"""
        from core.algorithms.element_constrained_search import ElementConstraintSearch

        search = ElementConstraintSearch()
        search.set_detected_elements(['Cu', 'Fe', 'O'])

        phase = {'name': 'CuO', 'formula': 'CuO'}
        result = search.check_phase_compatibility(phase)

        self.assertIsNotNone(result)

    def test_filter_phases(self):
        """测试物相过滤"""
        from core.algorithms.element_constrained_search import ElementConstraintSearch

        search = ElementConstraintSearch()
        search.set_detected_elements(['Cu', 'O'])

        phases = [
            {'name': 'CuO', 'formula': 'CuO'},
            {'name': 'Fe2O3', 'formula': 'Fe2O3'},
        ]

        filtered = search.filter_database(phases)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['name'], 'CuO')


class TestEnhancedProfile(unittest.TestCase):
    """测试增强峰形拟合"""

    def test_pseudo_voigt(self):
        """Test pseudo-Voigt function"""
        from core.algorithms.enhanced_profile import PeakProfileFunctions

        x = np.array([19.5, 20.0, 20.5])
        result = PeakProfileFunctions.pseudo_voigt(x, amp=100, cen=20.0, sigma=0.1, eta=0.5)

        self.assertEqual(len(result), 3)
        self.assertGreater(result[1], result[0])

    def test_gaussian(self):
        """测试高斯函数"""
        from core.algorithms.enhanced_profile import PeakProfileFunctions

        x = np.array([20.0, 20.0, 20.0])
        result = PeakProfileFunctions.gaussian(x, amp=100, cen=20.0, sigma=0.1)

        self.assertEqual(result[0], 100)


class TestWholePatternFit(unittest.TestCase):
    """测试全谱拟合"""

    def test_ddm_quantify(self):
        """测试 DDM 定量"""
        from core.algorithms.whole_pattern_fit import DirectDerivationMethod

        ddm = DirectDerivationMethod()
        ddm.add_phase('Al2O3', 'Al2O3', z=6)
        ddm.add_phase('SiO2', 'SiO2', z=3)

        peak_areas = {'Al2O3': 1000, 'SiO2': 500}
        result = ddm.quantify(peak_areas)

        self.assertGreater(len(result), 0)
        self.assertAlmostEqual(sum(result.values()), 100, places=0)


class TestPeakDetection(unittest.TestCase):
    """测试峰检测"""

    def test_peak_class(self):
        """测试 Peak 数据类"""
        from core.algorithms.peak_detection import Peak

        peak = Peak(position=30.0, intensity=100, fwhm=0.5)
        self.assertEqual(peak.position, 30.0)
        self.assertEqual(peak.intensity, 100)


class TestXRDPreprocessor(unittest.TestCase):
    """测试 XRD 预处理"""

    def test_savgol_smooth(self):
        """Test Savitzky-Golay smoothing"""
        from core.algorithms.xrd_preprocessor import smooth_savgol

        y = np.array([1, 2, 3, 2, 1, 2, 3, 2, 1])
        result = smooth_savgol(y, window=5, polyorder=2)

        self.assertEqual(len(result), len(y))

    def test_background_snip(self):
        """Test SNIP background subtraction"""
        from core.algorithms.xrd_preprocessor import background_snip

        y = np.array([10, 15, 50, 100, 50, 15, 10, 12, 14])
        background = background_snip(y, max_half_window=3)

        self.assertEqual(len(background), len(y))


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
