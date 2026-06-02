from __future__ import annotations

import csv
import io
import json
import logging
import math
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    headers: List[str] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    instrument_type: str = "generic"
    warnings: List[str] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def col_count(self) -> int:
        return len(self.headers)


class InstrumentDetector:
    INSTRUMENT_XRD = "xrd"
    INSTRUMENT_XPS = "xps"
    INSTRUMENT_MASSSPEC = "mass_spec"
    INSTRUMENT_RAMAN = "raman"
    INSTRUMENT_FTIR = "ftir"
    INSTRUMENT_TGADSC = "tga_dsc"
    INSTRUMENT_UVVIS = "uv_vis"
    INSTRUMENT_GENERIC = "generic"

    VALID_TYPES = {
        INSTRUMENT_XRD,
        INSTRUMENT_XPS,
        INSTRUMENT_MASSSPEC,
        INSTRUMENT_RAMAN,
        INSTRUMENT_FTIR,
        INSTRUMENT_TGADSC,
        INSTRUMENT_UVVIS,
        INSTRUMENT_GENERIC,
    }

    _XRD_PATTERNS = [
        re.compile(r"2[\s\-]?theta", re.IGNORECASE),
        re.compile(r"\bangle\b", re.IGNORECASE),
        re.compile(r"\bxrd\b", re.IGNORECASE),
        re.compile(r"\bdiffraction\b", re.IGNORECASE),
        re.compile(r"\bbragg\b", re.IGNORECASE),
    ]

    _XPS_PATTERNS = [
        re.compile(r"binding\s+energy", re.IGNORECASE),
        re.compile(r"\bcps\b", re.IGNORECASE),
        re.compile(r"\bxps\b", re.IGNORECASE),
        re.compile(r"\besca\b", re.IGNORECASE),
        re.compile(r"\bsurvey\b", re.IGNORECASE),
        re.compile(r"high[\s\-]?res", re.IGNORECASE),
    ]

    _MASSSPEC_PATTERNS = [
        re.compile(r"m/z", re.IGNORECASE),
        re.compile(r"\bmass[\s/\-]to[\s/\-]charge\b", re.IGNORECASE),
        re.compile(r"\bmass\s*spec", re.IGNORECASE),
        re.compile(r"\bda\b", re.IGNORECASE),
        re.compile(r"\bcentroid\b", re.IGNORECASE),
        re.compile(r"\bprofile\s+mode\b", re.IGNORECASE),
    ]

    _RAMAN_PATTERNS = [
        re.compile(r"raman\s+shift", re.IGNORECASE),
        re.compile(r"\braman\b", re.IGNORECASE),
        re.compile(r"\bshift\s*\(\s*cm", re.IGNORECASE),
        re.compile(r"\bstokes\b", re.IGNORECASE),
        re.compile(r"\banti[\s\-]?stokes\b", re.IGNORECASE),
    ]

    _FTIR_PATTERNS = [
        re.compile(r"wavenumber", re.IGNORECASE),
        re.compile(r"transmittance", re.IGNORECASE),
        re.compile(r"\babsorbance\b", re.IGNORECASE),
        re.compile(r"\bftir\b", re.IGNORECASE),
        re.compile(r"\binfrared\b", re.IGNORECASE),
        re.compile(r"\bir\s+spec", re.IGNORECASE),
    ]

    _TGADSC_PATTERNS = [
        re.compile(r"\btemperature\b", re.IGNORECASE),
        re.compile(r"\bweight[\s\s]*[%]?\b", re.IGNORECASE),
        re.compile(r"\bheat\s+flow\b", re.IGNORECASE),
        re.compile(r"\btga\b", re.IGNORECASE),
        re.compile(r"\bdsc\b", re.IGNORECASE),
        re.compile(r"\bthermogravim", re.IGNORECASE),
        re.compile(r"\bdifferential\s+scanning", re.IGNORECASE),
    ]

    _UVVIS_PATTERNS = [
        re.compile(r"\bwavelength\b", re.IGNORECASE),
        re.compile(r"\babsorbance\b", re.IGNORECASE),
        re.compile(r"\buv[\s\-]?vis\b", re.IGNORECASE),
        re.compile(r"\btransmittance\b", re.IGNORECASE),
        re.compile(r"\breflectance\b", re.IGNORECASE),
        re.compile(r"\boptical\s+density\b", re.IGNORECASE),
    ]

    _XRD_EXTENSIONS = {".raw", ".xy", ".dat", ".asc"}
    _XPS_EXTENSIONS = {".spe", ".vgd"}
    _MASSSPEC_EXTENSIONS = {".raw", ".mzml", ".mzxml", ".cdf"}
    _RAMAN_EXTENSIONS = {".ram", ".spc", ".wdf"}
    _FTIR_EXTENSIONS = {".spa", ".spc", ".irb"}
    _TGADSC_EXTENSIONS = {".tga", ".dsc"}
    _UVVIS_EXTENSIONS = {".uv", ".spc"}

    def detect(self, content: str, filename: str) -> str:
        scores: Dict[str, float] = {}
        ext = os.path.splitext(filename)[1].lower() if filename else ""
        content_lower = content[:8192].lower()

        scores[self.INSTRUMENT_XRD] = self._score_xrd(content_lower, ext)
        scores[self.INSTRUMENT_XPS] = self._score_xps(content_lower, ext)
        scores[self.INSTRUMENT_MASSSPEC] = self._score_massspec(content_lower, ext)
        scores[self.INSTRUMENT_RAMAN] = self._score_raman(content_lower, ext)
        scores[self.INSTRUMENT_FTIR] = self._score_ftir(content_lower, ext)
        scores[self.INSTRUMENT_TGADSC] = self._score_tgadsc(content_lower, ext)
        scores[self.INSTRUMENT_UVVIS] = self._score_uvvis(content_lower, ext)

        best_type = self.INSTRUMENT_GENERIC
        best_score = 0.0
        for instr_type, score in scores.items():
            if score > best_score:
                best_score = score
                best_type = instr_type

        if best_score < 1.0:
            logger.info(
                "No strong instrument match (best=%.1f for %s), falling back to generic",
                best_score,
                best_type,
            )
            return self.INSTRUMENT_GENERIC

        logger.debug("Detected instrument type: %s (score=%.1f)", best_type, best_score)
        return best_type

    def _pattern_score(self, content: str, patterns: List[re.Pattern]) -> float:
        score = 0.0
        for pattern in patterns:
            matches = pattern.findall(content)
            if matches:
                score += min(len(matches), 3)
        return score

    def _score_xrd(self, content: str, ext: str) -> float:
        score = self._pattern_score(content, self._XRD_PATTERNS)
        if ext in self._XRD_EXTENSIONS:
            score += 2.0
        lines = content.split("\n")
        xrd_range_hits = 0
        for line in lines[:200]:
            stripped = line.strip()
            if not stripped or stripped[0] in ("#", "!", ";", "*"):
                continue
            parts = stripped.split()
            if len(parts) == 2:
                try:
                    val_str = parts[0].replace(",", ".")
                    val = float(val_str)
                    if 5.0 <= val <= 90.0:
                        xrd_range_hits += 1
                except ValueError:
                    continue
        if xrd_range_hits >= 3:
            score += 2.0
        elif xrd_range_hits >= 1:
            score += 0.5
        return score

    def _score_xps(self, content: str, ext: str) -> float:
        score = self._pattern_score(content, self._XPS_PATTERNS)
        if ext in self._XPS_EXTENSIONS:
            score += 2.0
        return score

    def _score_massspec(self, content: str, ext: str) -> float:
        score = self._pattern_score(content, self._MASSSPEC_PATTERNS)
        if ext in self._MASSSPEC_EXTENSIONS:
            score += 2.0
        return score

    def _score_raman(self, content: str, ext: str) -> float:
        score = self._pattern_score(content, self._RAMAN_PATTERNS)
        if ext in self._RAMAN_EXTENSIONS:
            score += 2.0
        lines = content.split("\n")
        for line in lines[:200]:
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    val = float(parts[0])
                    if 50.0 <= val <= 4000.0:
                        score += 0.3
                        break
                except ValueError:
                    continue
        return score

    def _score_ftir(self, content: str, ext: str) -> float:
        score = self._pattern_score(content, self._FTIR_PATTERNS)
        if ext in self._FTIR_EXTENSIONS:
            score += 2.0
        return score

    def _score_tgadsc(self, content: str, ext: str) -> float:
        score = self._pattern_score(content, self._TGADSC_PATTERNS)
        if ext in self._TGADSC_EXTENSIONS:
            score += 2.0
        return score

    def _score_uvvis(self, content: str, ext: str) -> float:
        score = self._pattern_score(content, self._UVVIS_PATTERNS)
        if ext in self._UVVIS_EXTENSIONS:
            score += 2.0
        lines = content.split("\n")
        for line in lines[:200]:
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    val = float(parts[0])
                    if 190.0 <= val <= 1100.0:
                        score += 0.3
                        break
                except ValueError:
                    continue
        return score


class DataParser:
    COMMENT_CHARS = ("#", "!", ";", "*")

    def parse(self, content: str, filename: str) -> ParseResult:
        raise NotImplementedError

    def _is_comment_line(self, line: str) -> bool:
        stripped = line.strip()
        return any(stripped.startswith(c) for c in self.COMMENT_CHARS)

    def _is_blank_line(self, line: str) -> bool:
        return len(line.strip()) == 0

    def _detect_delimiter(self, sample_lines: List[str]) -> str:
        if not sample_lines:
            return ","
        non_empty = [
            line for line in sample_lines
            if not self._is_comment_line(line) and not self._is_blank_line(line)
        ]
        if not non_empty:
            return ","
        sample_text = "\n".join(non_empty)
        try:
            dialect = csv.Sniffer().sniff(sample_text, delimiters=',\t;')
            detected = dialect.delimiter
            counts = [len(line.split(detected)) for line in non_empty]
            if max(counts) == min(counts) and min(counts) > 1:
                return detected
        except Exception:
            pass
        delimiters = ["\t", ",", ";", " "]
        best_delimiter = ","
        best_score = -float('inf')
        for d in delimiters:
            counts = []
            for line in non_empty:
                count = len(line.split(d))
                if count > 1:
                    counts.append(count)
            if not counts:
                continue
            coverage = len(counts) / len(non_empty)
            if coverage < 0.5:
                continue
            avg = sum(counts) / len(counts)
            variance = sum((c - avg) ** 2 for c in counts) / len(counts)
            if variance == 0:
                score = avg * 10 + 100
            else:
                score = avg * 10 - variance * 10
            if d == " ":
                score -= 50
            if score > best_score:
                best_score = score
                best_delimiter = d
        if best_delimiter == " ":
            return r"\s+"
        return best_delimiter

    def _clean_numeric(self, value: str) -> Optional[float]:
        if value is None:
            return None
        cleaned = value.strip()
        if re.match(r"^\d+,\d+$", cleaned):
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = re.sub(r"[^\d.\-+eE]", "", cleaned)
        if not cleaned or cleaned in ("-", "+", ".", "-.", "+."):
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _extract_unit(self, header: str) -> Tuple[str, Optional[str]]:
        match = re.search(r"\(([^)]+)\)", header)
        if match:
            unit = match.group(1).strip()
            name = re.sub(r"\s*\([^)]+\)", "", header).strip()
            return name, unit
        match = re.search(r"\[([^\]]+)\]", header)
        if match:
            unit = match.group(1).strip()
            name = re.sub(r"\s*\[[^\]]+\]", "", header).strip()
            return name, unit
        return header.strip(), None

    def _split_data_line(self, line: str, delimiter: str) -> List[str]:
        stripped = line.strip()
        if not stripped:
            return []
        if delimiter == r"\s+":
            return re.split(r"\s+", stripped)
        if delimiter == ",":
            try:
                return next(csv.reader(io.StringIO(stripped)))
            except csv.Error:
                return stripped.split(",")
        return stripped.split(delimiter)

    def _find_data_start(
        self, lines: List[str], delimiter: str
    ) -> Tuple[int, Optional[List[str]]]:
        headers = None
        data_start = 0
        for i, line in enumerate(lines):
            if self._is_comment_line(line) or self._is_blank_line(line):
                continue
            parts = self._split_data_line(line, delimiter)
            if not parts:
                continue
            numeric_count = 0
            for p in parts:
                if self._clean_numeric(p) is not None:
                    numeric_count += 1
            if numeric_count == len(parts) and numeric_count >= 2:
                data_start = i
                break
            elif numeric_count < len(parts) and len(parts) >= 2:
                headers = [p.strip().strip('"').strip("'") for p in parts]
                data_start = i + 1
                break
        return data_start, headers

    def _parse_content(
        self,
        content: str,
        default_headers: Optional[List[str]] = None,
        known_metadata_prefixes: Optional[List[str]] = None,
    ) -> ParseResult:
        result = ParseResult()
        lines = content.split("\n")
        metadata: Dict[str, Any] = {}
        known_metadata_prefixes = known_metadata_prefixes or []

        clean_lines = []
        for line in lines:
            if self._is_comment_line(line):
                stripped = line.strip()
                for c in self.COMMENT_CHARS:
                    if stripped.startswith(c):
                        content_part = stripped[len(c):].strip()
                        if content_part:
                            kv = content_part.split(None, 1)
                            if len(kv) == 2:
                                metadata[kv[0].strip()] = kv[1].strip()
                        break
                continue
            clean_lines.append(line)

        non_blank = [l for l in clean_lines if not self._is_blank_line(l)]
        if not non_blank:
            result.warnings.append("File appears to be empty")
            return result

        sample_lines = non_blank[: min(20, len(non_blank))]
        delimiter = self._detect_delimiter(sample_lines)

        data_start, headers = self._find_data_start(clean_lines, delimiter)

        rows: List[List[Any]] = []
        for i in range(data_start, len(clean_lines)):
            line = clean_lines[i]
            if self._is_blank_line(line):
                continue
            if self._is_comment_line(line):
                continue
            parts = self._split_data_line(line, delimiter)
            if not parts:
                continue
            row: List[Any] = []
            for p in parts:
                p = p.strip().strip('"').strip("'")
                num = self._clean_numeric(p)
                if num is not None:
                    row.append(num)
                else:
                    row.append(p)
            if row:
                rows.append(row)

        if not rows:
            result.warnings.append("No data rows found")
            return result

        max_cols = max(len(r) for r in rows)
        for r in rows:
            while len(r) < max_cols:
                r.append(None)

        while max_cols > 0:
            all_empty = True
            for r in rows:
                if len(r) >= max_cols:
                    val = r[max_cols - 1]
                    if val is not None and str(val).strip() != "":
                        all_empty = False
                        break
            if not all_empty:
                break
            for r in rows:
                if len(r) >= max_cols:
                    r.pop()
            max_cols -= 1

        if headers is None:
            if default_headers and len(default_headers) >= max_cols:
                headers = default_headers[:max_cols]
            else:
                headers = []
                for i in range(max_cols):
                    if default_headers and i < len(default_headers):
                        headers.append(default_headers[i])
                    else:
                        headers.append(f"Col_{i + 1}")
        else:
            while len(headers) < max_cols:
                headers.append(f"Col_{len(headers) + 1}")

        result.headers = headers
        result.rows = rows
        result.metadata = metadata

        while result.headers and not result.headers[-1].strip():
            result.headers.pop()
            for r in result.rows:
                if len(r) > len(result.headers):
                    r.pop()

        return result


class XRDParser(DataParser):
    _BRUKER_PREFIX = re.compile(r"^\*")
    _RIGAKU_PREFIX = re.compile(r"^\*|RIGAKU", re.IGNORECASE)
    _PANALYTICAL_PREFIX = re.compile(r"Configuration|Scan", re.IGNORECASE)

    def parse(self, content: str, filename: str) -> ParseResult:
        result = self._parse_content(content, default_headers=["2Theta", "Intensity"])
        result.instrument_type = InstrumentDetector.INSTRUMENT_XRD

        if result.headers == ["2Theta", "Intensity"] and result.col_count > 2:
            result.headers = ["2Theta"] + [
                f"Intensity_{i}" for i in range(1, result.col_count)
            ]

        for i, h in enumerate(result.headers):
            h_lower = h.lower()
            if "2theta" in h_lower or "2-theta" in h_lower or "angle" in h_lower:
                result.headers[i] = "2Theta"
            elif "intensity" in h_lower or "counts" in h_lower or "cps" in h_lower or "psd" in h_lower:
                result.headers[i] = "Intensity" if result.col_count == 2 else f"Intensity_{i}"

        if result.row_count > 0:
            first_val = result.rows[0][0]
            if isinstance(first_val, (int, float)):
                if first_val > 90.0:
                    result.warnings.append(
                        "First column value > 90, may not be 2Theta degrees"
                    )

        return result


class XPSParser(DataParser):
    def parse(self, content: str, filename: str) -> ParseResult:
        result = self._parse_content(
            content, default_headers=["Binding_Energy", "Counts"]
        )
        result.instrument_type = InstrumentDetector.INSTRUMENT_XPS

        is_survey = "survey" in content[:4096].lower()
        result.metadata["scan_type"] = "survey" if is_survey else "high_resolution"

        for i, h in enumerate(result.headers):
            h_lower = h.lower()
            if "binding" in h_lower or "energy" in h_lower:
                result.headers[i] = "Binding_Energy"
            elif "cps" in h_lower:
                result.headers[i] = "CPS"
            elif "counts" in h_lower:
                result.headers[i] = "Counts"
            elif i > 0:
                result.headers[i] = f"Signal_{i}"

        if result.col_count > 2:
            result.headers[0] = "Binding_Energy"
            for i in range(1, result.col_count):
                result.headers[i] = f"Signal_{i}"

        return result


class MassSpecParser(DataParser):
    def parse(self, content: str, filename: str) -> ParseResult:
        result = self._parse_content(content, default_headers=["m_z", "Intensity"])
        result.instrument_type = InstrumentDetector.INSTRUMENT_MASSSPEC

        content_lower = content[:4096].lower()
        if "centroid" in content_lower:
            result.metadata["mode"] = "centroid"
        elif "profile" in content_lower:
            result.metadata["mode"] = "profile"
        else:
            result.metadata["mode"] = "unknown"

        for i, h in enumerate(result.headers):
            h_lower = h.lower()
            if "m/z" in h_lower or "m_z" in h_lower or "mass" in h_lower:
                result.headers[i] = "m_z"
            elif "intensity" in h_lower or "counts" in h_lower:
                result.headers[i] = "Intensity"
            elif i > 0:
                result.headers[i] = f"Signal_{i}"

        if result.col_count > 2:
            result.headers[0] = "m_z"
            for i in range(1, result.col_count):
                result.headers[i] = f"Signal_{i}"

        return result


class RamanParser(DataParser):
    def parse(self, content: str, filename: str) -> ParseResult:
        result = self._parse_content(
            content, default_headers=["Raman_Shift_cm-1", "Intensity"]
        )
        result.instrument_type = InstrumentDetector.INSTRUMENT_RAMAN

        for i, h in enumerate(result.headers):
            h_lower = h.lower()
            if "shift" in h_lower or "raman" in h_lower or "cm" in h_lower:
                result.headers[i] = "Raman_Shift_cm-1"
            elif "intensity" in h_lower or "counts" in h_lower:
                result.headers[i] = "Intensity"
            elif i > 0:
                result.headers[i] = f"Spectrum_{i}"

        if result.col_count > 2:
            result.headers[0] = "Raman_Shift_cm-1"
            for i in range(1, result.col_count):
                result.headers[i] = f"Spectrum_{i}"
            result.metadata["multi_spectrum"] = True

        return result


class FTIRParser(DataParser):
    def parse(self, content: str, filename: str) -> ParseResult:
        result = self._parse_content(
            content, default_headers=["Wavenumber_cm-1", "Transmittance"]
        )
        result.instrument_type = InstrumentDetector.INSTRUMENT_FTIR

        y_label = "Transmittance"
        if result.row_count > 0:
            for row in result.rows[:50]:
                if len(row) > 1 and isinstance(row[1], (int, float)):
                    if row[1] < 0 or row[1] > 100:
                        y_label = "Absorbance"
                    break

        for i, h in enumerate(result.headers):
            h_lower = h.lower()
            if "wavenumber" in h_lower or "wave" in h_lower or "cm" in h_lower:
                result.headers[i] = "Wavenumber_cm-1"
            elif "transmit" in h_lower:
                result.headers[i] = "Transmittance"
                y_label = "Transmittance"
            elif "absorb" in h_lower:
                result.headers[i] = "Absorbance"
                y_label = "Absorbance"
            elif i > 0:
                result.headers[i] = y_label if i == 1 else f"Signal_{i}"

        if result.col_count == 2:
            result.headers[1] = y_label

        return result


class TGADSCParser(DataParser):
    def parse(self, content: str, filename: str) -> ParseResult:
        result = self._parse_content(
            content,
            default_headers=["Temperature_C", "Weight_mg", "Heat_Flow_mW"],
        )
        result.instrument_type = InstrumentDetector.INSTRUMENT_TGADSC

        for i, h in enumerate(result.headers):
            h_lower = h.lower()
            if "temp" in h_lower:
                result.headers[i] = "Temperature_C"
            elif "weight" in h_lower or "mass" in h_lower:
                result.headers[i] = "Weight_mg"
            elif "heat" in h_lower or "flow" in h_lower or "dsc" in h_lower:
                result.headers[i] = "Heat_Flow_mW"
            elif "time" in h_lower:
                result.headers[i] = "Time_min"
            elif i > 0:
                result.headers[i] = f"Signal_{i}"

        has_tga = any("weight" in h.lower() or "mass" in h.lower() for h in result.headers)
        has_dsc = any("heat" in h.lower() or "flow" in h.lower() for h in result.headers)
        result.metadata["has_tga"] = has_tga
        result.metadata["has_dsc"] = has_dsc

        return result


class UVVisParser(DataParser):
    def parse(self, content: str, filename: str) -> ParseResult:
        result = self._parse_content(
            content, default_headers=["Wavelength_nm", "Absorbance"]
        )
        result.instrument_type = InstrumentDetector.INSTRUMENT_UVVIS

        y_label = "Absorbance"
        for i, h in enumerate(result.headers):
            h_lower = h.lower()
            if "wave" in h_lower:
                result.headers[i] = "Wavelength_nm"
            elif "absorb" in h_lower:
                result.headers[i] = "Absorbance"
                y_label = "Absorbance"
            elif "transmit" in h_lower:
                result.headers[i] = "Transmittance"
                y_label = "Transmittance"
            elif "reflect" in h_lower:
                result.headers[i] = "Reflectance"
                y_label = "Reflectance"
            elif i > 0:
                result.headers[i] = f"Signal_{i}"

        if result.col_count == 2:
            result.headers[1] = y_label

        return result


class GenericParser(DataParser):
    def parse(self, content: str, filename: str) -> ParseResult:
        result = self._parse_content(content)
        result.instrument_type = InstrumentDetector.INSTRUMENT_GENERIC

        if result.col_count >= 2:
            numeric_cols = []
            for col_idx in range(result.col_count):
                numeric_count = 0
                total = 0
                for row in result.rows:
                    if col_idx < len(row) and isinstance(row[col_idx], (int, float)):
                        numeric_count += 1
                    total += 1
                if total > 0 and numeric_count / total > 0.8:
                    numeric_cols.append(col_idx)

            result.metadata["numeric_columns"] = numeric_cols

        return result


class DataPreprocessService:
    def __init__(self) -> None:
        self._detector = InstrumentDetector()
        self._parsers: Dict[str, DataParser] = {
            InstrumentDetector.INSTRUMENT_XRD: XRDParser(),
            InstrumentDetector.INSTRUMENT_XPS: XPSParser(),
            InstrumentDetector.INSTRUMENT_MASSSPEC: MassSpecParser(),
            InstrumentDetector.INSTRUMENT_RAMAN: RamanParser(),
            InstrumentDetector.INSTRUMENT_FTIR: FTIRParser(),
            InstrumentDetector.INSTRUMENT_TGADSC: TGADSCParser(),
            InstrumentDetector.INSTRUMENT_UVVIS: UVVisParser(),
            InstrumentDetector.INSTRUMENT_GENERIC: GenericParser(),
        }

    def detect_instrument(self, content: str, filename: str) -> str:
        if not content and not filename:
            logger.warning("Empty content and filename provided for detection")
            return InstrumentDetector.INSTRUMENT_GENERIC
        return self._detector.detect(content, filename)

    def parse_raw_data(
        self,
        content: str,
        filename: str,
        instrument_type: str = "auto",
    ) -> ParseResult:
        if not content:
            result = ParseResult()
            result.warnings.append("Empty content provided")
            return result

        if instrument_type == "auto":
            instrument_type = self.detect_instrument(content, filename)
            logger.info("Auto-detected instrument type: %s", instrument_type)

        if instrument_type not in InstrumentDetector.VALID_TYPES:
            logger.warning(
                "Unknown instrument type '%s', falling back to generic",
                instrument_type,
            )
            instrument_type = InstrumentDetector.INSTRUMENT_GENERIC

        parser = self._parsers.get(instrument_type, self._parsers[InstrumentDetector.INSTRUMENT_GENERIC])

        try:
            result = parser.parse(content, filename)
        except Exception as exc:
            logger.error("Parser failed for %s: %s", instrument_type, exc, exc_info=True)
            result = ParseResult()
            result.instrument_type = instrument_type
            result.warnings.append(f"Parse error: {exc}")
            fallback = self._parsers[InstrumentDetector.INSTRUMENT_GENERIC]
            try:
                result = fallback.parse(content, filename)
                result.warnings.append(
                    f"Primary parser for '{instrument_type}' failed; used generic fallback"
                )
            except Exception as fallback_exc:
                logger.error(
                    "Fallback parser also failed: %s", fallback_exc, exc_info=True
                )
                result.warnings.append(f"Fallback parse error: {fallback_exc}")

        return result

    def to_csv(self, result: ParseResult) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(result.headers)
        for row in result.rows:
            csv_row = []
            for val in row:
                if val is None:
                    csv_row.append("")
                elif isinstance(val, float):
                    if math.isnan(val) or math.isinf(val):
                        csv_row.append("")
                    else:
                        csv_row.append(val)
                else:
                    csv_row.append(val)
            writer.writerow(csv_row)
        return output.getvalue()

    def to_json(self, result: ParseResult) -> str:
        records = []
        for row in result.rows:
            record = {}
            for i, header in enumerate(result.headers):
                val = row[i] if i < len(row) else None
                if isinstance(val, float):
                    if math.isnan(val):
                        val = None
                    elif math.isinf(val):
                        val = None
                record[header] = val
            records.append(record)
        return json.dumps(records, ensure_ascii=False)

    def to_chart_data(self, result: ParseResult) -> List[Dict[str, Any]]:
        chart_data: List[Dict[str, Any]] = []
        for row in result.rows:
            point: Dict[str, Any] = {}
            for i, header in enumerate(result.headers):
                val = row[i] if i < len(row) else None
                if isinstance(val, float):
                    if math.isnan(val) or math.isinf(val):
                        val = None
                point[header] = val
            chart_data.append(point)
        return chart_data

    def get_column_info(self, result: ParseResult) -> List[Dict[str, Any]]:
        col_info: List[Dict[str, Any]] = []
        for col_idx, header in enumerate(result.headers):
            name, unit = self._parsers.get(
                result.instrument_type, self._parsers[InstrumentDetector.INSTRUMENT_GENERIC]
            )._extract_unit(header)

            numeric_values = []
            string_values = []
            for row in result.rows:
                if col_idx < len(row):
                    val = row[col_idx]
                    if isinstance(val, (int, float)):
                        if not math.isnan(val) and not math.isinf(val):
                            numeric_values.append(val)
                    elif isinstance(val, str) and val:
                        string_values.append(val)

            info: Dict[str, Any] = {
                "name": name or header,
                "index": col_idx,
                "unit": unit,
            }

            if numeric_values:
                info["type"] = "numeric"
                info["min"] = min(numeric_values)
                info["max"] = max(numeric_values)
                info["mean"] = sum(numeric_values) / len(numeric_values)
                info["count"] = len(numeric_values)
            else:
                info["type"] = "string"
                info["count"] = len(string_values)

            col_info.append(info)
        return col_info

    def preview(
        self,
        content: str,
        filename: str,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        result = self.parse_raw_data(content, filename)

        preview_rows = result.rows[:max_rows]
        col_info = self.get_column_info(result)

        return {
            "instrument_type": result.instrument_type,
            "headers": result.headers,
            "row_count": result.row_count,
            "col_count": result.col_count,
            "preview_rows": preview_rows,
            "column_info": col_info,
            "metadata": result.metadata,
            "warnings": result.warnings,
        }

    _INSTRUMENT_INFO = [
        {
            "type": InstrumentDetector.INSTRUMENT_XRD,
            "name": "XRD",
            "description": "X-Ray Diffraction",
            "extensions": [".raw", ".xy", ".dat", ".asc"],
        },
        {
            "type": InstrumentDetector.INSTRUMENT_XPS,
            "name": "XPS",
            "description": "X-Ray Photoelectron Spectroscopy",
            "extensions": [".spe", ".vgd"],
        },
        {
            "type": InstrumentDetector.INSTRUMENT_MASSSPEC,
            "name": "Mass Spec",
            "description": "Mass Spectrometry",
            "extensions": [".raw", ".mzml", ".mzxml", ".cdf"],
        },
        {
            "type": InstrumentDetector.INSTRUMENT_RAMAN,
            "name": "Raman",
            "description": "Raman Spectroscopy",
            "extensions": [".ram", ".spc", ".wdf"],
        },
        {
            "type": InstrumentDetector.INSTRUMENT_FTIR,
            "name": "FTIR",
            "description": "Fourier Transform Infrared Spectroscopy",
            "extensions": [".spa", ".spc", ".irb"],
        },
        {
            "type": InstrumentDetector.INSTRUMENT_TGADSC,
            "name": "TGA-DSC",
            "description": "Thermogravimetric Analysis / Differential Scanning Calorimetry",
            "extensions": [".tga", ".dsc"],
        },
        {
            "type": InstrumentDetector.INSTRUMENT_UVVIS,
            "name": "UV-Vis",
            "description": "Ultraviolet-Visible Spectroscopy",
            "extensions": [".uv", ".spc"],
        },
    ]

    def list_instruments(self) -> List[Dict[str, Any]]:
        return list(self._INSTRUMENT_INFO)

    def _decode_data(self, data: bytes) -> str:
        for enc in ("utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"):
            try:
                return data.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return data.decode("latin-1", errors="replace")

    def _result_to_chart_data(self, result: ParseResult) -> List[Dict[str, Any]]:
        return self.to_chart_data(result)

    def parse(
        self,
        data: bytes,
        filename: str,
        instrument_type: str = "auto",
        export_format: str = "chart_data",
    ) -> Dict[str, Any]:
        content = self._decode_data(data)
        detected_type = instrument_type
        if instrument_type == "auto":
            detected_type = self.detect_instrument(content, filename)

        result = self.parse_raw_data(content, filename, instrument_type=detected_type)
        col_info = self.get_column_info(result)

        if export_format == "csv":
            exported = self.to_csv(result)
        elif export_format == "json":
            exported = self.to_json(result)
        else:
            exported = self._result_to_chart_data(result)

        return {
            "ok": True,
            "instrument_type": result.instrument_type,
            "detected_type": detected_type,
            "filename": filename,
            "columns": col_info,
            "row_count": result.row_count,
            "data": exported,
            "metadata": result.metadata,
            "warnings": result.warnings,
        }

    def preview_bytes(
        self,
        data: bytes,
        filename: str,
        instrument_type: str = "auto",
    ) -> Dict[str, Any]:
        content = self._decode_data(data)
        detected_type = instrument_type
        if instrument_type == "auto":
            detected_type = self.detect_instrument(content, filename)

        result = self.parse_raw_data(content, filename, instrument_type=detected_type)
        col_info = self.get_column_info(result)
        preview_rows = self.to_chart_data(result)[:5]

        return {
            "ok": True,
            "instrument_type": result.instrument_type,
            "filename": filename,
            "columns": col_info,
            "preview_rows": preview_rows,
            "metadata": result.metadata,
            "warnings": result.warnings,
        }

    def export(
        self,
        data: bytes,
        filename: str,
        instrument_type: str = "auto",
        export_format: str = "csv",
    ) -> Dict[str, Any]:
        content = self._decode_data(data)
        detected_type = instrument_type
        if instrument_type == "auto":
            detected_type = self.detect_instrument(content, filename)

        result = self.parse_raw_data(content, filename, instrument_type=detected_type)

        base_name = os.path.splitext(filename)[0]
        if export_format == "csv":
            return {
                "content": self.to_csv(result),
                "filename": f"{base_name}.csv",
            }
        elif export_format == "json":
            return {
                "content": self.to_json(result),
                "filename": f"{base_name}.json",
            }
        elif export_format == "xlsx":
            return {
                "columns": self.get_column_info(result),
                "rows": self.to_chart_data(result),
                "filename": f"{base_name}.xlsx",
            }
        else:
            return {
                "content": self.to_csv(result),
                "filename": f"{base_name}.csv",
            }


_service_instance: Optional[DataPreprocessService] = None


def get_data_preprocess_service() -> DataPreprocessService:
    global _service_instance
    if _service_instance is None:
        _service_instance = DataPreprocessService()
    return _service_instance
