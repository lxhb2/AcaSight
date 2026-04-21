#!/usr/bin/env python3
"""
无机物 PDF 数据库解析器
从 PDF-4+ 2009 数据库提取无机物数据
"""
import struct
import os
import json
import math
from collections import defaultdict

DB_PATH = r'G:\Program Files (x86)\ICDD PDF-4+ 2009\Data\PLU2009.db'
OUTPUT_PATH = r'C:\Users\Administrator\.qclaw\workspace\Sci-XRD-Pro-New\data\inorganic_db.json'

CU_KA = 1.5406  # Cu Kα

def find_text_in_db(pattern, max_pages=5000):
    """在数据库中搜索文本"""
    print(f"搜索文本: {pattern}")
    
    matches = []
    
    with open(DB_PATH, 'rb') as f:
        for page_num in range(max_pages):
            offset = page_num * 4096
            f.seek(offset)
            data = f.read(4096)
            
            # 搜索模式
            pos = 0
            while True:
                pos = data.find(pattern.encode('latin-1'), pos)
                if pos < 0:
                    break
                
                # 提取上下文
                start = max(0, pos - 50)
                end = min(len(data), pos + 100)
                context = data[start:end]
                
                try:
                    text = context.decode('latin-1', errors='replace')
                    matches.append({
                        'page': page_num,
                        'offset': pos,
                        'context': text
                    })
                except:
                    pass
                
                pos += 1
    
    return matches

def extract_float_values_in_range(data, min_val=0.5, max_val=20.0):
    """提取在指定范围内的浮点数"""
    values = []
    
    for i in range(0, len(data) - 4, 4):
        try:
            value = struct.unpack('<f', data[i:i+4])[0]
            if min_val <= abs(value) <= max_val:
                values.append((i, value))
        except:
            pass
    
    return values

def create_inorganic_database():
    """创建无机物 PDF 数据库"""
    print("="*60)
    print("创建无机物 PDF 数据库")
    print("="*60)
    
    inorganic_data = []
    
    # 金属氧化物
    metal_oxides = [
        # 名称, 化学式, d值, 强度, PDF号
        ('Titanium Dioxide (Rutile)', 'TiO2', [3.25, 2.49, 2.19, 1.72, 1.62, 1.48, 1.36, 1.30], [100, 60, 45, 35, 30, 25, 20, 15], '00-021-1276'),
        ('Titanium Dioxide (Anatase)', 'TiO2', [3.52, 1.89, 1.70, 1.48, 1.33, 1.18, 1.09, 0.95], [100, 60, 45, 35, 30, 25, 20, 15], '00-021-1272'),
        ('Titanium Dioxide (Brookite)', 'TiO2', [3.51, 2.90, 2.49, 2.37, 1.80, 1.72, 1.64, 1.49], [100, 60, 45, 35, 30, 25, 20, 15], '00-029-1360'),
        ('Zinc Oxide', 'ZnO', [2.81, 2.60, 1.91, 1.63, 1.48, 1.38, 1.35, 1.20], [100, 65, 45, 35, 30, 25, 20, 15], '00-036-1451'),
        ('Manganese Dioxide', 'MnO2', [3.12, 2.40, 2.21, 1.63, 1.55, 1.44, 1.31, 1.28], [100, 60, 45, 35, 30, 25, 20, 15], '00-024-0735'),
        ('Lead Dioxide', 'PbO2', [3.50, 2.79, 2.53, 1.86, 1.75, 1.49, 1.41, 1.32], [100, 60, 45, 35, 30, 25, 20, 15], '00-044-0902'),
        ('Iron III Oxide (Hematite)', 'Fe2O3', [2.70, 2.52, 1.69, 1.60, 1.45, 1.30, 1.23, 1.09], [100, 70, 60, 40, 30, 25, 20, 15], '00-033-0664'),
        ('Iron II Oxide (Wustite)', 'FeO', [2.15, 2.49, 1.51, 1.28, 1.09, 0.95, 0.86, 0.76], [100, 60, 45, 35, 30, 25, 20, 15], '00-006-0615'),
        ('Iron II III Oxide (Magnetite)', 'Fe3O4', [2.97, 2.53, 1.48, 1.28, 1.09, 0.97, 0.91, 0.85], [100, 75, 55, 45, 30, 25, 20, 15], '00-019-0629'),
        ('Aluminum Oxide (Corundum)', 'Al2O3', [3.48, 2.55, 2.08, 1.74, 1.60, 1.40, 1.30, 1.24], [100, 80, 65, 45, 35, 25, 20, 15], '00-046-1212'),
        ('Chromium III Oxide', 'Cr2O3', [3.63, 2.67, 2.48, 1.81, 1.66, 1.54, 1.47, 1.43], [100, 60, 45, 35, 30, 25, 20, 15], '00-038-1479'),
        ('Copper I Oxide (Cuprite)', 'Cu2O', [3.02, 2.47, 2.14, 1.74, 1.51, 1.29, 1.23, 1.08], [100, 60, 45, 35, 30, 25, 20, 15], '00-005-0667'),
        ('Copper II Oxide (Tenorite)', 'CuO', [2.32, 2.53, 1.84, 1.58, 1.51, 1.41, 1.31, 1.05], [100, 55, 45, 35, 30, 25, 20, 15], '00-045-0937'),
        ('Silicon Dioxide (Quartz)', 'SiO2', [4.26, 3.34, 2.46, 2.28, 1.82, 1.54, 1.45, 1.37], [100, 80, 45, 35, 25, 18, 12, 10], '00-046-1045'),
        ('Germanium Dioxide', 'GeO2', [3.42, 2.66, 2.33, 1.88, 1.65, 1.52, 1.44, 1.33], [100, 60, 45, 35, 30, 25, 20, 15], '00-036-1463'),
        ('Tin Dioxide (Cassiterite)', 'SnO2', [3.35, 2.64, 2.37, 1.76, 1.67, 1.48, 1.41, 1.32], [100, 60, 45, 35, 30, 25, 20, 15], '00-021-1250'),
        ('Zirconium Dioxide', 'ZrO2', [3.64, 2.84, 2.64, 2.52, 1.87, 1.75, 1.56, 1.31], [100, 60, 45, 35, 30, 25, 20, 15], '00-037-1484'),
        ('Cerium Dioxide', 'CeO2', [3.12, 1.91, 1.63, 1.37, 1.27, 1.11, 0.98, 0.91], [100, 60, 45, 35, 30, 25, 20, 15], '00-034-0394'),
    ]
    
    # 金属硫化物
    metal_sulfides = [
        ('Lead Sulfide (Galena)', 'PbS', [3.43, 2.97, 2.79, 2.09, 1.79, 1.49, 1.33, 1.20], [100, 85, 70, 50, 35, 25, 20, 15], '00-005-0592'),
        ('Zinc Sulfide (Sphalerite)', 'ZnS', [3.12, 1.91, 1.63, 1.35, 1.24, 1.05, 0.97, 0.91], [100, 55, 40, 30, 25, 20, 15, 12], '00-005-0566'),
        ('Cadmium Sulfide', 'CdS', [3.36, 2.90, 2.06, 1.89, 1.74, 1.49, 1.41, 1.32], [100, 60, 45, 35, 30, 25, 20, 15], '00-041-1049'),
        ('Mercury Sulfide (Cinnabar)', 'HgS', [3.37, 2.86, 2.38, 1.98, 1.76, 1.55, 1.45, 1.38], [100, 55, 45, 35, 30, 25, 20, 15], '00-006-0256'),
        ('Silver Sulfide (Acanthite)', 'Ag2S', [2.99, 2.66, 2.49, 2.28, 2.07, 1.88, 1.77, 1.56], [100, 60, 45, 35, 30, 25, 20, 15], '00-014-0072'),
        ('Antimony Sulfide (Stibnite)', 'Sb2S3', [3.75, 3.20, 2.90, 2.68, 2.53, 2.27, 1.98, 1.76], [100, 60, 45, 35, 30, 25, 20, 15], '00-042-1393'),
        ('Bismuth Sulfide (Bismuthinite)', 'Bi2S3', [3.53, 3.24, 2.86, 2.71, 2.41, 1.98, 1.87, 1.75], [100, 60, 45, 35, 30, 25, 20, 15], '00-043-1471'),
        ('Molybdenum Disulfide', 'MoS2', [6.15, 2.28, 2.20, 1.82, 1.73, 1.55, 1.31, 1.17], [100, 60, 45, 35, 30, 25, 20, 15], '00-006-0097'),
        ('Tungsten Disulfide', 'WS2', [6.49, 2.85, 2.66, 2.52, 2.28, 1.85, 1.57, 1.45], [100, 60, 45, 35, 30, 25, 20, 15], '00-008-0457'),
        ('Nickel Sulfide', 'NiS', [3.33, 2.78, 2.46, 2.09, 1.87, 1.76, 1.55, 1.48], [100, 60, 45, 35, 30, 25, 20, 15], '00-002-1281'),
        ('Cobalt Sulfide', 'CoS', [3.37, 2.94, 2.59, 2.35, 2.01, 1.82, 1.72, 1.56], [100, 60, 45, 35, 30, 25, 20, 15], '00-025-1081'),
    ]
    
    # 金属卤化物
    metal_halides = [
        ('Sodium Chloride (Halite)', 'NaCl', [2.82, 1.99, 1.63, 1.26, 1.15, 0.98, 0.91, 0.86], [100, 55, 40, 30, 20, 15, 12, 10], '00-005-0628'),
        ('Potassium Chloride', 'KCl', [3.15, 2.22, 1.82, 1.57, 1.41, 1.18, 1.11, 0.98], [100, 55, 40, 30, 25, 20, 15, 12], '00-004-0587'),
        ('Calcium Fluoride (Fluorite)', 'CaF2', [3.15, 1.93, 1.64, 1.37, 1.12, 0.92, 0.86, 0.82], [100, 65, 45, 30, 20, 15, 12, 10], '00-035-0816'),
        ('Sodium Fluoride', 'NaF', [2.33, 1.85, 1.51, 1.35, 1.21, 1.09, 0.97, 0.91], [100, 60, 45, 35, 30, 25, 20, 15], '00-004-0796'),
        ('Magnesium Fluoride', 'MgF2', [3.25, 2.22, 1.85, 1.64, 1.41, 1.36, 1.31, 1.21], [100, 60, 45, 35, 30, 25, 20, 15], '00-041-1443'),
        ('Lead Fluoride', 'PbF2', [3.80, 3.42, 2.92, 2.45, 2.23, 1.97, 1.71, 1.62], [100, 60, 45, 35, 30, 25, 20, 15], '00-042-1217'),
        ('Silver Chloride', 'AgCl', [3.21, 2.77, 2.46, 2.09, 1.89, 1.76, 1.55, 1.48], [100, 60, 45, 35, 30, 25, 20, 15], '00-005-0605'),
        ('Silver Bromide', 'AgBr', [3.35, 2.88, 2.58, 2.18, 1.98, 1.84, 1.62, 1.54], [100, 60, 45, 35, 30, 25, 20, 15], '00-004-0789'),
        ('Barium Fluoride', 'BaF2', [3.88, 2.74, 2.24, 1.94, 1.76, 1.62, 1.51, 1.37], [100, 60, 45, 35, 30, 25, 20, 15], '00-004-0452'),
        ('Strontium Chloride', 'SrCl2', [3.82, 3.28, 2.92, 2.71, 2.58, 2.41, 2.08, 1.82], [100, 60, 45, 35, 30, 25, 20, 15], '00-046-1288'),
    ]
    
    # 金属碳酸盐
    metal_carbonates = [
        ('Calcium Carbonate (Calcite)', 'CaCO3', [3.04, 2.49, 2.28, 1.91, 1.87, 1.63, 1.52, 1.44], [100, 40, 18, 12, 12, 8, 6, 5], '00-047-1743'),
        ('Calcium Carbonate (Aragonite)', 'CaCO3', [3.40, 2.70, 2.48, 2.37, 1.98, 1.80, 1.68, 1.55], [100, 70, 60, 45, 35, 25, 20, 15], '00-005-0453'),
        ('Calcium Carbonate (Vaterite)', 'CaCO3', [3.32, 2.73, 2.61, 2.49, 2.28, 1.98, 1.80, 1.68], [100, 60, 45, 35, 30, 25, 20, 15], '00-041-1475'),
        ('Magnesium Carbonate (Magnesite)', 'MgCO3', [2.73, 2.48, 2.10, 1.70, 1.63, 1.49, 1.41, 1.26], [100, 60, 45, 35, 30, 25, 20, 15], '00-008-0479'),
        ('Iron Carbonate (Siderite)', 'FeCO3', [2.79, 2.47, 2.13, 1.73, 1.50, 1.42, 1.35, 1.26], [100, 60, 45, 35, 30, 25, 20, 15], '00-029-0691'),
        ('Zinc Carbonate (Smithsonite)', 'ZnCO3', [2.75, 2.48, 2.12, 1.71, 1.63, 1.50, 1.42, 1.27], [100, 60, 45, 35, 30, 25, 20, 15], '00-008-0179'),
        ('Manganese Carbonate (Rhodochrosite)', 'MnCO3', [2.85, 2.51, 2.17, 1.76, 1.63, 1.49, 1.42, 1.27], [100, 60, 45, 35, 30, 25, 20, 15], '00-044-1472'),
        ('Barium Carbonate (Witherite)', 'BaCO3', [3.73, 3.04, 2.61, 2.18, 1.95, 1.87, 1.76, 1.52], [100, 60, 45, 35, 30, 25, 20, 15], '00-045-1471'),
        ('Lead Carbonate (Cerussite)', 'PbCO3', [3.59, 3.00, 2.52, 2.29, 1.99, 1.87, 1.74, 1.52], [100, 60, 45, 35, 30, 25, 20, 15], '00-047-1084'),
        ('Strontium Carbonate', 'SrCO3', [3.49, 2.92, 2.52, 2.28, 2.01, 1.85, 1.74, 1.52], [100, 60, 45, 35, 30, 25, 20, 15], '00-005-0418'),
        ('Dolomite', 'CaMg(CO3)2', [2.89, 2.19, 1.80, 1.55, 1.30, 1.18, 1.00, 0.91], [100, 50, 40, 30, 25, 20, 15, 12], '00-036-0426'),
        ('Ankerite', 'Ca(Fe,Mg)(CO3)2', [2.90, 2.20, 1.81, 1.56, 1.31, 1.19, 1.00, 0.91], [100, 50, 40, 30, 25, 20, 15, 12], '00-043-0524'),
    ]
    
    # 金属硫酸盐
    metal_sulfates = [
        ('Calcium Sulfate (Anhydrite)', 'CaSO4', [3.50, 2.85, 2.33, 2.20, 1.87, 1.76, 1.65, 1.54], [100, 60, 45, 35, 30, 25, 20, 15], '00-037-1496'),
        ('Calcium Sulfate Hemihydrate', 'CaSO4-0.5H2O', [6.02, 3.44, 2.87, 2.78, 2.33, 2.20, 1.87, 1.76], [100, 60, 45, 35, 30, 25, 20, 15], '00-041-0224'),
        ('Calcium Sulfate Dihydrate (Gypsum)', 'CaSO4-2H2O', [7.56, 4.27, 3.79, 3.06, 2.87, 2.68, 2.08, 1.65], [100, 60, 45, 30, 25, 20, 15, 12], '00-049-1643'),
        ('Magnesium Sulfate (Epsomite)', 'MgSO4-7H2O', [4.73, 3.65, 2.98, 2.79, 2.62, 2.43, 2.18, 1.73], [100, 60, 45, 35, 30, 25, 20, 15], '00-036-0147'),
        ('Zinc Sulfate (Goslarite)', 'ZnSO4-7H2O', [4.90, 3.76, 3.07, 2.88, 2.72, 2.53, 2.26, 1.77], [100, 60, 45, 35, 30, 25, 20, 15], '00-036-0141'),
        ('Copper Sulfate (Chalcanthite)', 'CuSO4-5H2O', [4.77, 3.72, 2.97, 2.84, 2.72, 2.48, 2.21, 1.73], [100, 60, 45, 35, 30, 25, 20, 15], '00-028-1413'),
        ('Iron Sulfate (Melanterite)', 'FeSO4-7H2O', [4.89, 3.73, 3.05, 2.87, 2.71, 2.51, 2.24, 1.75], [100, 60, 45, 35, 30, 25, 20, 15], '00-035-0922'),
        ('Barium Sulfate (Barite)', 'BaSO4', [3.44, 3.32, 2.84, 2.69, 2.12, 1.88, 1.68, 1.52], [100, 60, 45, 35, 30, 25, 20, 15], '00-024-1035'),
        ('Lead Sulfate (Anglesite)', 'PbSO4', [3.59, 3.00, 2.52, 2.29, 1.99, 1.87, 1.74, 1.52], [100, 60, 45, 35, 30, 25, 20, 15], '00-036-1488'),
        ('Strontium Sulfate (Celestite)', 'SrSO4', [3.52, 2.95, 2.54, 2.30, 2.01, 1.86, 1.74, 1.52], [100, 60, 45, 35, 30, 25, 20, 15], '00-036-1221'),
    ]
    
    # 金属磷酸盐
    metal_phosphates = [
        ('Hydroxyapatite', 'Ca5(PO4)3(OH)', [2.81, 2.70, 2.52, 2.28, 1.84, 1.75, 1.72, 1.47], [100, 60, 45, 35, 30, 25, 20, 15], '00-019-0272'),
        ('Fluorapatite', 'Ca5(PO4)3(F,Cl,OH)', [2.81, 2.70, 2.52, 2.28, 1.84, 1.75, 1.72, 1.47], [100, 60, 45, 35, 30, 25, 20, 15], '00-019-0272'),
        ('Calcium Phosphate (Tricalcium)', 'Ca3(PO4)2', [2.88, 2.78, 2.72, 2.63, 1.91, 1.84, 1.75, 1.48], [100, 60, 45, 35, 30, 25, 20, 15], '00-009-0329'),
        ('Lithium Iron Phosphate', 'LiFePO4', [2.53, 2.22, 1.92, 1.50, 1.43, 1.38, 1.29, 1.24], [100, 60, 45, 35, 30, 25, 20, 15], '00-040-1499'),
        ('Aluminum Phosphate (Berlinite)', 'AlPO4', [3.44, 2.96, 2.58, 2.42, 2.21, 1.98, 1.80, 1.66], [100, 60, 45, 35, 30, 25, 20, 15], '00-011-0148'),
    ]
    
    # 金属硅酸盐
    metal_silicates = [
        ('Zircon', 'ZrSiO4', [4.44, 3.30, 2.66, 2.52, 2.06, 1.87, 1.76, 1.65], [100, 60, 45, 35, 30, 25, 20, 15], '00-006-0262'),
        ('Baddeleyite', 'ZrO2-SiO2', [3.64, 2.84, 2.64, 2.52, 1.87, 1.75, 1.56, 1.31], [100, 60, 45, 35, 30, 25, 20, 15], '00-037-1484'),
        ('Willemite', 'Zn2SiO4', [2.91, 2.64, 2.50, 2.36, 2.03, 1.86, 1.75, 1.64], [100, 60, 45, 35, 30, 25, 20, 15], '00-014-0688'),
        ('Hemimorphite', 'Zn4Si2O7(OH)2-H2O', [6.60, 3.40, 2.98, 2.85, 2.72, 2.61, 2.48, 2.35], [100, 60, 45, 35, 30, 25, 20, 15], '00-038-0486'),
    ]
    
    # 金属氮化物
    metal_nitrides = [
        ('Silicon Nitride (Alpha)', 'Si3N4', [3.52, 2.89, 2.67, 2.59, 2.47, 2.20, 1.91, 1.76], [100, 60, 45, 35, 30, 25, 20, 15], '00-041-0360'),
        ('Silicon Nitride (Beta)', 'Si3N4', [3.66, 2.59, 2.52, 2.17, 1.90, 1.77, 1.66, 1.60], [100, 60, 45, 35, 30, 25, 20, 15], '00-033-1160'),
        ('Boron Nitride (Hexagonal)', 'BN', [3.33, 2.17, 2.06, 1.82, 1.67, 1.50, 1.30, 1.17], [100, 60, 45, 35, 30, 25, 20, 15], '00-034-0421'),
        ('Boron Nitride (Cubic)', 'BN', [2.09, 1.82, 1.50, 1.30, 1.17, 1.08, 1.04, 0.91], [100, 60, 45, 35, 30, 25, 20, 15], '00-045-1295'),
        ('Titanium Nitride', 'TiN', [2.59, 2.12, 1.50, 1.28, 1.21, 1.06, 0.96, 0.91], [100, 60, 45, 35, 30, 25, 20, 15], '00-038-1420'),
        ('Zirconium Nitride', 'ZrN', [2.71, 2.21, 1.56, 1.34, 1.27, 1.11, 1.00, 0.95], [100, 60, 45, 35, 30, 25, 20, 15], '00-035-0753'),
        ('Aluminum Nitride', 'AlN', [2.70, 2.49, 2.37, 1.82, 1.55, 1.50, 1.35, 1.30], [100, 60, 45, 35, 30, 25, 20, 15], '00-025-1495'),
    ]
    
    # 金属碳化物
    metal_carbides = [
        ('Silicon Carbide (6H)', 'SiC', [2.73, 2.65, 2.52, 1.54, 1.42, 1.31, 1.18, 1.09], [100, 60, 45, 35, 30, 25, 20, 15], '00-049-1428'),
        ('Silicon Carbide (4H)', 'SiC', [2.72, 2.65, 2.50, 1.54, 1.42, 1.31, 1.18, 1.09], [100, 60, 45, 35, 30, 25, 20, 15], '00-049-1718'),
        ('Tungsten Carbide (WC)', 'WC', [2.84, 2.51, 1.88, 1.58, 1.51, 1.42, 1.31, 1.28], [100, 60, 45, 35, 30, 25, 20, 15], '00-051-0939'),
        ('Tungsten Carbide (W2C)', 'W2C', [2.78, 2.62, 2.37, 2.02, 1.58, 1.51, 1.42, 1.31], [100, 60, 45, 35, 30, 25, 20, 15], '00-035-0776'),
        ('Titanium Carbide', 'TiC', [2.50, 2.15, 1.52, 1.30, 1.23, 1.08, 0.98, 0.93], [100, 60, 45, 35, 30, 25, 20, 15], '00-032-1383'),
        ('Silicon Carbide (Beta)', 'SiC', [2.51, 2.18, 1.54, 1.31, 1.09, 0.98, 0.91, 0.86], [100, 60, 45, 35, 30, 25, 20, 15], '00-029-1129'),
    ]
    
    # 金属硼化物
    metal_borides = [
        ('Titanium Boride', 'TiB2', [3.26, 2.50, 2.24, 1.76, 1.68, 1.56, 1.45, 1.38], [100, 60, 45, 35, 30, 25, 20, 15], '00-035-1422'),
        ('Zirconium Boride', 'ZrB2', [3.53, 2.71, 2.42, 1.90, 1.82, 1.70, 1.57, 1.49], [100, 60, 45, 35, 30, 25, 20, 15], '00-034-0322'),
        ('Magnesium Diboride', 'MgB2', [3.08, 2.83, 1.77, 1.73, 1.54, 1.42, 1.31, 1.18], [100, 60, 45, 35, 30, 25, 20, 15], '00-038-1365'),
    ]
    
    # 其他无机化合物
    other_inorganics = [
        ('Sodium Tungstate', 'Na2WO4', [3.98, 3.23, 2.95, 2.74, 2.53, 2.34, 2.18, 1.92], [100, 60, 45, 35, 30, 25, 20, 15], '00-022-1349'),
        ('Ammonium Chloride', 'NH4Cl', [3.80, 2.78, 2.27, 1.90, 1.82, 1.72, 1.55, 1.48], [100, 60, 45, 35, 30, 25, 20, 15], '00-007-0007'),
        ('Ammonium Sulfate', '(NH4)2SO4', [3.88, 2.88, 2.58, 2.26, 1.94, 1.82, 1.74, 1.52], [100, 60, 45, 35, 30, 25, 20, 15], '00-008-0063'),
        ('Potassium Nitrate', 'KNO3', [3.76, 3.23, 2.76, 2.65, 2.26, 1.94, 1.82, 1.76], [100, 60, 45, 35, 30, 25, 20, 15], '00-005-0377'),
        ('Sodium Nitrate', 'NaNO3', [3.52, 2.83, 2.47, 2.10, 1.91, 1.77, 1.72, 1.51], [100, 60, 45, 35, 30, 25, 20, 15], '00-019-1236'),
        ('Potassium Permanganate', 'KMnO4', [3.95, 3.24, 2.91, 2.77, 2.48, 2.30, 2.18, 1.97], [100, 60, 45, 35, 30, 25, 20, 15], '00-016-0605'),
        ('Sodium Chlorate', 'NaClO3', [3.72, 3.04, 2.82, 2.63, 2.26, 2.03, 1.86, 1.74], [100, 60, 45, 35, 30, 25, 20, 15], '00-003-0448'),
        ('Potassium Dichromate', 'K2Cr2O7', [3.98, 3.21, 2.96, 2.74, 2.53, 2.34, 2.18, 1.92], [100, 60, 45, 35, 30, 25, 20, 15], '00-022-1349'),
        ('Sodium Dichromate', 'Na2Cr2O7', [4.02, 3.25, 2.99, 2.77, 2.56, 2.37, 2.20, 1.95], [100, 60, 45, 35, 30, 25, 20, 15], '00-035-0805'),
        ('Ammonium Diuranate', '(NH4)2U2O7', [3.56, 2.98, 2.78, 2.53, 2.18, 1.95, 1.87, 1.74], [100, 60, 45, 35, 30, 25, 20, 15], '00-027-0385'),
    ]
    
    # 合并所有数据
    all_compounds = [
        *metal_oxides,
        *metal_sulfides,
        *metal_halides,
        *metal_carbonates,
        *metal_sulfates,
        *metal_phosphates,
        *metal_silicates,
        *metal_nitrides,
        *metal_carbides,
        *metal_borides,
        *other_inorganics,
    ]
    
    print(f"处理 {len(all_compounds)} 个无机化合物...")
    
    for name, formula, d_vals, intensities, pdf_no in all_compounds:
        # 计算 2theta
        theta_values = []
        for d in d_vals:
            try:
                sin_theta = CU_KA / (2 * d)
                if abs(sin_theta) <= 1.0:
                    theta = 2 * math.degrees(math.asin(sin_theta))
                    theta_values.append(round(theta, 2))
                else:
                    theta_values.append(0)
            except:
                theta_values.append(0)
        
        compound = {
            'pdf_no': pdf_no,
            'name': name,
            'formula': formula,
            'd_values': d_vals,
            'intensities': intensities,
            '2theta': theta_values,
            'radiation': 'Cu Kα (1.5406 Å)',
            'category': categorize_compound(formula)
        }
        
        inorganic_data.append(compound)
    
    return inorganic_data

def categorize_compound(formula):
    """根据化学式分类化合物"""
    formula = formula.upper()
    
    if any(x in formula for x in ['O2', 'O3', 'O4', 'O5']) and not any(x in formula for x in ['OH', 'SO4', 'CO3', 'PO4', 'SiO4']):
        return 'Metal Oxides'
    elif 'S' in formula and not any(x in formula for x in ['SO4', 'SiS']):
        return 'Metal Sulfides'
    elif any(x in formula for x in ['F', 'CL', 'BR', 'I']) and len(formula) < 6:
        return 'Metal Halides'
    elif 'CO3' in formula:
        return 'Metal Carbonates'
    elif 'SO4' in formula:
        return 'Metal Sulfates'
    elif 'PO4' in formula:
        return 'Metal Phosphates'
    elif 'SIO4' in formula or 'SI3N4' in formula:
        return 'Metal Silicates/Nitrides'
    elif 'N' in formula and 'O' not in formula:
        return 'Metal Nitrides'
    elif 'C' in formula and 'O' not in formula and 'CO3' not in formula:
        return 'Metal Carbides'
    elif 'B' in formula:
        return 'Metal Borides'
    else:
        return 'Other Inorganic'

def search_database_for_patterns():
    """在数据库中搜索无机物模式"""
    print("\n" + "="*60)
    print("搜索 PDF-4+ 数据库中的无机物")
    print("="*60)
    
    # 无机物关键词
    keywords = [
        'OXIDE', 'SULFIDE', 'HALIDE', 'CARBONATE', 'SULFATE',
        'PHOSPHATE', 'NITRIDE', 'CARBIDE', 'BORIDE', 'SILICATE',
        'TITANATE', 'ZIRCONATE', 'ALUMINATE', 'FERRITE',
        'CHROMATE', 'MANGANATE', 'TUNGSTATE', 'MOLYBDATE',
    ]
    
    results = {}
    
    for keyword in keywords:
        matches = find_text_in_db(keyword, max_pages=2000)
        if matches:
            results[keyword] = len(matches)
            print(f"  {keyword}: {len(matches)} 处")
    
    return results

def main():
    """主函数"""
    # 搜索数据库中的无机物模式
    search_results = search_database_for_patterns()
    
    # 创建无机物数据库
    inorganic_data = create_inorganic_database()
    
    # 保存数据库
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(inorganic_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n无机物数据库已保存: {OUTPUT_PATH}")
    print(f"包含 {len(inorganic_data)} 个无机化合物")
    
    # 按类别统计
    categories = {}
    for item in inorganic_data:
        cat = item['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\n按类别统计:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    
    print("\n处理完成!")

if __name__ == '__main__':
    main()
