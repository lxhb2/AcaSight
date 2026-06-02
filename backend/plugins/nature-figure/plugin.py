"""
Nature Figure Plugin
Nature标准实验结果图 — 绘制符合Nature期刊标准的实验结果图，支持Python和R代码生成

Nature期刊图表标准:
- 最小300 DPI
- Arial/Helvetica字体
- 5-7pt标签字号
- 色盲友好调色板
- 规范的轴标签(含单位)
"""

from app.services.plugin_system import AcaSightPlugin


NATURE_STANDARDS = {
    "nature": {
        "min_dpi": 300,
        "fonts": ["Arial", "Helvetica"],
        "label_size_pt": (5, 7),
        "color_palette": "colorblind_friendly",
        "axis_label_required": True,
        "units_required": True,
        "max_figure_width_inches": 7.0,
        "max_figure_height_inches": 9.5,
    },
    "science": {
        "min_dpi": 300,
        "fonts": ["Arial", "Helvetica"],
        "label_size_pt": (5, 7),
        "color_palette": "colorblind_friendly",
        "axis_label_required": True,
        "units_required": True,
        "max_figure_width_inches": 7.0,
        "max_figure_height_inches": 9.5,
    },
    "cell": {
        "min_dpi": 300,
        "fonts": ["Arial", "Helvetica", "sans-serif"],
        "label_size_pt": (6, 8),
        "color_palette": "colorblind_friendly",
        "axis_label_required": True,
        "units_required": True,
        "max_figure_width_inches": 7.5,
        "max_figure_height_inches": 9.0,
    },
}

COLORBLIND_PALETTE = [
    "#0072B2",
    "#E69F00",
    "#009E73",
    "#CC79A7",
    "#56B4E9",
    "#D55E00",
    "#F0E442",
    "#000000",
]

FIGURE_TEMPLATES = {
    "bar": {
        "description": "Bar chart with error bars",
        "default_style": "nature",
        "required_data_keys": ["categories", "values", "errors"],
    },
    "line": {
        "description": "Line chart with confidence intervals",
        "default_style": "nature",
        "required_data_keys": ["x", "y"],
    },
    "scatter": {
        "description": "Scatter plot with regression line",
        "default_style": "nature",
        "required_data_keys": ["x", "y"],
    },
    "box": {
        "description": "Box plot with individual data points",
        "default_style": "nature",
        "required_data_keys": ["categories", "values"],
    },
    "heatmap": {
        "description": "Heatmap with color bar",
        "default_style": "nature",
        "required_data_keys": ["matrix"],
    },
    "violin": {
        "description": "Violin plot with median and quartiles",
        "default_style": "nature",
        "required_data_keys": ["categories", "values"],
    },
}


class NatureFigurePlugin(AcaSightPlugin):
    """Nature标准实验结果图插件"""

    async def on_load(self, config: dict) -> None:
        await super().on_load(config)
        self.register_hook("pre_chart", self.pre_chart_template)
        self.register_hook("post_chart", self.post_chart_validate)
        self._default_journal = config.get("default_journal", "nature")
        self._default_dpi = config.get("default_dpi", 300)

    async def on_enable(self) -> None:
        pass

    async def on_disable(self) -> None:
        pass

    async def on_unload(self) -> None:
        pass

    async def pre_chart_template(self, figure_type: str = "bar", style: str = "nature", **kwargs) -> dict:
        """
        pre_chart 钩子处理器 — 提供Nature风格模板

        Returns:
            dict: 包含模板配置、调色板、字体规范等
        """
        template = FIGURE_TEMPLATES.get(figure_type)
        if not template:
            return {
                "template_found": False,
                "error": f"Unknown figure type: {figure_type}",
                "available_types": list(FIGURE_TEMPLATES.keys()),
            }

        standards = NATURE_STANDARDS.get(style, NATURE_STANDARDS["nature"])

        return {
            "template_found": True,
            "figure_type": figure_type,
            "style": style,
            "template": template,
            "standards": standards,
            "color_palette": COLORBLIND_PALETTE,
            "font_family": standards["fonts"][0],
            "label_size_range": standards["label_size_pt"],
            "min_dpi": standards["min_dpi"],
            "max_dimensions": {
                "width_inches": standards["max_figure_width_inches"],
                "height_inches": standards["max_figure_height_inches"],
            },
        }

    async def post_chart_validate(self, figure_data: dict, journal: str = "nature", **kwargs) -> dict:
        """
        post_chart 钩子处理器 — 验证生成的图表是否符合Nature标准

        Args:
            figure_data: 包含图表元信息 (dpi, font, colors, dimensions, labels)
            journal: 目标期刊标准

        Returns:
            dict: 验证结果，包含通过/失败项及建议
        """
        validation = self.validate_figure_standards(figure_data, journal)
        return validation

    async def generate_nature_figure(self, data: dict, figure_type: str, style: str = "nature") -> dict:
        """
        生成Nature标准图表规格

        Args:
            data: 图表数据
            figure_type: 图表类型 (bar, line, scatter, box, heatmap, violin)
            style: 期刊风格 (nature, science, cell)

        Returns:
            dict: 完整的图表规格，包含数据、样式、模板和验证结果
        """
        template_result = await self.pre_chart_template(figure_type=figure_type, style=style)

        if not template_result.get("template_found"):
            return {
                "success": False,
                "error": template_result.get("error"),
                "available_types": template_result.get("available_types", []),
            }

        template = template_result["template"]
        missing_keys = []
        for key in template["required_data_keys"]:
            if key not in data:
                missing_keys.append(key)

        if missing_keys:
            return {
                "success": False,
                "error": f"Missing required data keys: {missing_keys}",
                "required_keys": template["required_data_keys"],
            }

        standards = template_result["standards"]

        figure_spec = {
            "success": True,
            "figure_type": figure_type,
            "style": style,
            "data": data,
            "render_config": {
                "dpi": standards["min_dpi"],
                "font_family": standards["fonts"][0],
                "label_size_pt": standards["label_size_pt"][1],
                "title_size_pt": standards["label_size_pt"][1] + 2,
                "tick_size_pt": standards["label_size_pt"][0],
                "color_palette": COLORBLIND_PALETTE,
                "figure_width": min(
                    data.get("width", 3.5), standards["max_figure_width_inches"]
                ),
                "figure_height": min(
                    data.get("height", 3.0), standards["max_figure_height_inches"]
                ),
                "axis_label_required": standards["axis_label_required"],
                "units_required": standards["units_required"],
            },
            "validation": self.validate_figure_standards(
                {
                    "dpi": standards["min_dpi"],
                    "font": standards["fonts"][0],
                    "label_size_pt": standards["label_size_pt"][1],
                    "colors": COLORBLIND_PALETTE,
                    "width": min(
                        data.get("width", 3.5), standards["max_figure_width_inches"]
                    ),
                    "height": min(
                        data.get("height", 3.0), standards["max_figure_height_inches"]
                    ),
                    "has_axis_labels": True,
                    "has_units": data.get("units") is not None,
                },
                journal=style,
            ),
        }

        return figure_spec

    def validate_figure_standards(self, figure_data: dict, journal: str = "nature") -> dict:
        """
        验证图表是否符合Nature期刊标准

        Args:
            figure_data: 图表元信息 (dpi, font, colors, dimensions, labels)
            journal: 目标期刊

        Returns:
            dict: 验证结果，包含各项检查的通过/失败状态
        """
        standards = NATURE_STANDARDS.get(journal, NATURE_STANDARDS["nature"])
        checks = []
        all_passed = True

        dpi = figure_data.get("dpi", 0)
        dpi_ok = dpi >= standards["min_dpi"]
        if not dpi_ok:
            all_passed = False
        checks.append({
            "rule": "min_dpi",
            "required": f">= {standards['min_dpi']}",
            "actual": dpi,
            "passed": dpi_ok,
            "suggestion": None if dpi_ok else f"Increase DPI to at least {standards['min_dpi']}",
        })

        font = figure_data.get("font", "")
        font_ok = font in standards["fonts"]
        if not font_ok:
            all_passed = False
        checks.append({
            "rule": "font_family",
            "required": f"one of {standards['fonts']}",
            "actual": font,
            "passed": font_ok,
            "suggestion": None if font_ok else f"Use one of: {', '.join(standards['fonts'])}",
        })

        label_size = figure_data.get("label_size_pt", 0)
        min_pt, max_pt = standards["label_size_pt"]
        label_ok = min_pt <= label_size <= max_pt
        if not label_ok:
            all_passed = False
        checks.append({
            "rule": "label_size",
            "required": f"{min_pt}-{max_pt} pt",
            "actual": f"{label_size} pt",
            "passed": label_ok,
            "suggestion": None if label_ok else f"Set label size between {min_pt} and {max_pt} pt",
        })

        colors = figure_data.get("colors", [])
        color_ok = len(colors) > 0
        if color_ok and standards["color_palette"] == "colorblind_friendly":
            non_hex = [c for c in colors if not (isinstance(c, str) and c.startswith("#") and len(c) == 7)]
            if non_hex:
                color_ok = False
        if not color_ok:
            all_passed = False
        checks.append({
            "rule": "color_palette",
            "required": "color-blind friendly hex colors",
            "actual": f"{len(colors)} colors",
            "passed": color_ok,
            "suggestion": None if color_ok else "Use the Nature color-blind friendly palette",
        })

        width = figure_data.get("width", 0)
        height = figure_data.get("height", 0)
        dim_ok = width <= standards["max_figure_width_inches"] and height <= standards["max_figure_height_inches"]
        if not dim_ok:
            all_passed = False
        checks.append({
            "rule": "figure_dimensions",
            "required": f"max {standards['max_figure_width_inches']}x{standards['max_figure_height_inches']} inches",
            "actual": f"{width}x{height} inches",
            "passed": dim_ok,
            "suggestion": None if dim_ok else "Reduce figure dimensions to fit journal limits",
        })

        has_labels = figure_data.get("has_axis_labels", False)
        labels_ok = has_labels or not standards["axis_label_required"]
        if not labels_ok:
            all_passed = False
        checks.append({
            "rule": "axis_labels",
            "required": "present" if standards["axis_label_required"] else "optional",
            "actual": "present" if has_labels else "missing",
            "passed": labels_ok,
            "suggestion": None if labels_ok else "Add axis labels with units",
        })

        has_units = figure_data.get("has_units", False)
        units_ok = has_units or not standards["units_required"]
        if not units_ok:
            all_passed = False
        checks.append({
            "rule": "units",
            "required": "present" if standards["units_required"] else "optional",
            "actual": "present" if has_units else "missing",
            "passed": units_ok,
            "suggestion": None if units_ok else "Add units to axis labels (e.g., 'Time (s)')",
        })

        return {
            "journal": journal,
            "all_passed": all_passed,
            "checks": checks,
            "standards_applied": standards,
        }

    async def generate_plot_code(self, data: dict, figure_type: str, language: str = "python") -> dict:
        """
        生成Python (matplotlib/seaborn) 或 R (ggplot2) 绑图代码

        Args:
            data: 图表数据
            figure_type: 图表类型
            language: "python" or "r"

        Returns:
            dict: 包含生成的代码和元信息
        """
        if language.lower() == "python":
            return self._generate_python_code(data, figure_type)
        elif language.lower() == "r":
            return self._generate_r_code(data, figure_type)
        else:
            return {
                "success": False,
                "error": f"Unsupported language: {language}",
                "supported_languages": ["python", "r"],
            }

    def _generate_python_code(self, data: dict, figure_type: str) -> dict:
        palette_str = str(COLORBLIND_PALETTE)

        common_setup = (
            f"import matplotlib.pyplot as plt\n"
            f"import seaborn as sns\n"
            f"import numpy as np\n\n"
            f"plt.rcParams.update({{\n"
            f"    'font.family': 'sans-serif',\n"
            f"    'font.sans-serif': ['Arial', 'Helvetica'],\n"
            f"    'font.size': 7,\n"
            f"    'axes.labelsize': 7,\n"
            f"    'xtick.labelsize': 5,\n"
            f"    'ytick.labelsize': 5,\n"
            f"    'figure.dpi': 300,\n"
            f"}})\n\n"
            f"NATURE_PALETTE = {palette_str}\n"
        )

        plot_code = ""

        if figure_type == "bar":
            categories = data.get("categories", ["A", "B", "C"])
            values = data.get("values", [1, 2, 3])
            errors = data.get("errors", [0.1, 0.2, 0.1])
            xlabel = data.get("xlabel", "Category")
            ylabel = data.get("ylabel", "Value")
            plot_code = (
                f"fig, ax = plt.subplots(figsize=(3.5, 3.0))\n"
                f"categories = {categories}\n"
                f"values = {values}\n"
                f"errors = {errors}\n"
                f"x_pos = np.arange(len(categories))\n\n"
                f"bars = ax.bar(x_pos, values, yerr=errors, capsize=3,\n"
                f"              color=NATURE_PALETTE[:len(categories)],\n"
                f"              edgecolor='black', linewidth=0.5)\n\n"
                f"ax.set_xlabel('{xlabel}')\n"
                f"ax.set_ylabel('{ylabel}')\n"
                f"ax.set_xticks(x_pos)\n"
                f"ax.set_xticklabels(categories)\n"
                f"sns.despine()\n"
                f"plt.tight_layout()\n"
                f"plt.savefig('figure_bar.pdf', dpi=300, bbox_inches='tight')\n"
            )
        elif figure_type == "line":
            xlabel = data.get("xlabel", "X")
            ylabel = data.get("ylabel", "Y")
            plot_code = (
                f"fig, ax = plt.subplots(figsize=(3.5, 3.0))\n"
                f"x = data.get('x', [])\n"
                f"y = data.get('y', [])\n"
                f"ci_lower = data.get('ci_lower', None)\n"
                f"ci_upper = data.get('ci_upper', None)\n\n"
                f"ax.plot(x, y, color=NATURE_PALETTE[0], linewidth=1.0)\n"
                f"if ci_lower is not None and ci_upper is not None:\n"
                f"    ax.fill_between(x, ci_lower, ci_upper,\n"
                f"                    color=NATURE_PALETTE[0], alpha=0.2)\n\n"
                f"ax.set_xlabel('{xlabel}')\n"
                f"ax.set_ylabel('{ylabel}')\n"
                f"sns.despine()\n"
                f"plt.tight_layout()\n"
                f"plt.savefig('figure_line.pdf', dpi=300, bbox_inches='tight')\n"
            )
        elif figure_type == "scatter":
            xlabel = data.get("xlabel", "X")
            ylabel = data.get("ylabel", "Y")
            plot_code = (
                f"fig, ax = plt.subplots(figsize=(3.5, 3.0))\n"
                f"x = data.get('x', [])\n"
                f"y = data.get('y', [])\n\n"
                f"ax.scatter(x, y, color=NATURE_PALETTE[0], s=20,\n"
                f"           edgecolor='black', linewidth=0.3, alpha=0.8)\n\n"
                f"if data.get('regression', False):\n"
                f"    z = np.polyfit(x, y, 1)\n"
                f"    p = np.poly1d(z)\n"
                f"    x_line = np.linspace(min(x), max(x), 100)\n"
                f"    ax.plot(x_line, p(x_line), color='black',\n"
                f"            linewidth=0.8, linestyle='--')\n\n"
                f"ax.set_xlabel('{xlabel}')\n"
                f"ax.set_ylabel('{ylabel}')\n"
                f"sns.despine()\n"
                f"plt.tight_layout()\n"
                f"plt.savefig('figure_scatter.pdf', dpi=300, bbox_inches='tight')\n"
            )
        elif figure_type == "box":
            xlabel = data.get("xlabel", "Category")
            ylabel = data.get("ylabel", "Value")
            plot_code = (
                f"fig, ax = plt.subplots(figsize=(3.5, 3.0))\n"
                f"categories = data.get('categories', [])\n"
                f"values = data.get('values', [])\n\n"
                f"bp = ax.boxplot(values, patch_artist=True,\n"
                f"               boxprops=dict(linewidth=0.8),\n"
                f"               medianprops=dict(color='black', linewidth=1.0),\n"
                f"               whiskerprops=dict(linewidth=0.8),\n"
                f"               capprops=dict(linewidth=0.8))\n\n"
                f"for patch, color in zip(bp['boxes'], NATURE_PALETTE[:len(values)]):\n"
                f"    patch.set_facecolor(color)\n"
                f"    patch.set_alpha(0.7)\n\n"
                f"ax.set_xticklabels(categories)\n"
                f"ax.set_xlabel('{xlabel}')\n"
                f"ax.set_ylabel('{ylabel}')\n"
                f"sns.despine()\n"
                f"plt.tight_layout()\n"
                f"plt.savefig('figure_box.pdf', dpi=300, bbox_inches='tight')\n"
            )
        elif figure_type == "heatmap":
            plot_code = (
                f"fig, ax = plt.subplots(figsize=(3.5, 3.0))\n"
                f"matrix = data.get('matrix', [])\n"
                f"xticklabels = data.get('xticklabels', None)\n"
                f"yticklabels = data.get('yticklabels', None)\n\n"
                f"sns.heatmap(matrix, ax=ax, cmap='viridis',\n"
                f"            xticklabels=xticklabels,\n"
                f"            yticklabels=yticklabels,\n"
                f"            linewidths=0.5, linecolor='white')\n\n"
                f"ax.set_xlabel(data.get('xlabel', ''))\n"
                f"ax.set_ylabel(data.get('ylabel', ''))\n"
                f"plt.tight_layout()\n"
                f"plt.savefig('figure_heatmap.pdf', dpi=300, bbox_inches='tight')\n"
            )
        elif figure_type == "violin":
            xlabel = data.get("xlabel", "Category")
            ylabel = data.get("ylabel", "Value")
            plot_code = (
                f"fig, ax = plt.subplots(figsize=(3.5, 3.0))\n"
                f"categories = data.get('categories', [])\n"
                f"values = data.get('values', [])\n\n"
                f"parts = ax.violinplot(values, showmeans=False,\n"
                f"                      showmedians=True, showextrema=False)\n\n"
                f"for i, pc in enumerate(parts['bodies']):\n"
                f"    pc.set_facecolor(NATURE_PALETTE[i % len(NATURE_PALETTE)])\n"
                f"    pc.set_alpha(0.7)\n"
                f"    pc.set_edgecolor('black')\n"
                f"    pc.set_linewidth(0.5)\n\n"
                f"parts['cmedians'].set_color('black')\n"
                f"parts['cmedians'].set_linewidth(1.0)\n\n"
                f"ax.set_xticks(np.arange(1, len(categories) + 1))\n"
                f"ax.set_xticklabels(categories)\n"
                f"ax.set_xlabel('{xlabel}')\n"
                f"ax.set_ylabel('{ylabel}')\n"
                f"sns.despine()\n"
                f"plt.tight_layout()\n"
                f"plt.savefig('figure_violin.pdf', dpi=300, bbox_inches='tight')\n"
            )
        else:
            return {
                "success": False,
                "error": f"Unsupported figure type: {figure_type}",
                "supported_types": list(FIGURE_TEMPLATES.keys()),
            }

        full_code = common_setup + "\n" + plot_code

        return {
            "success": True,
            "language": "python",
            "figure_type": figure_type,
            "code": full_code,
            "dependencies": ["matplotlib", "seaborn", "numpy"],
        }

    def _generate_r_code(self, data: dict, figure_type: str) -> dict:
        common_setup = (
            "library(ggplot2)\n"
            "library(dplyr)\n\n"
            "nature_theme <- theme_bw() +\n"
            "  theme(\n"
            "    text = element_text(family = 'Arial', size = 7),\n"
            "    axis.title = element_text(size = 7),\n"
            "    axis.text = element_text(size = 5),\n"
            "    panel.border = element_rect(linewidth = 0.5),\n"
            "    panel.grid = element_blank(),\n"
            "    legend.text = element_text(size = 5),\n"
            "    legend.title = element_text(size = 7)\n"
            "  )\n\n"
            "nature_palette <- c('#0072B2', '#E69F00', '#009E73',\n"
            "                    '#CC79A7', '#56B4E9', '#D55E00',\n"
            "                    '#F0E442', '#000000')\n"
        )

        xlabel = data.get("xlabel", "X")
        ylabel = data.get("ylabel", "Y")

        plot_code = ""

        if figure_type == "bar":
            plot_code = (
                f"df <- data.frame(\n"
                f"  category = {data.get('categories', [])},\n"
                f"  value = {data.get('values', [])},\n"
                f"  error = {data.get('errors', [])}\n"
                f")\n\n"
                f"p <- ggplot(df, aes(x = category, y = value, fill = category)) +\n"
                f"  geom_col(color = 'black', linewidth = 0.3) +\n"
                f"  geom_errorbar(aes(ymin = value - error, ymax = value + error),\n"
                f"                width = 0.3, linewidth = 0.3) +\n"
                f"  scale_fill_manual(values = nature_palette) +\n"
                f"  labs(x = '{xlabel}', y = '{ylabel}') +\n"
                f"  nature_theme\n\n"
                f"ggsave('figure_bar.pdf', p, width = 3.5, height = 3.0, dpi = 300)\n"
            )
        elif figure_type == "line":
            plot_code = (
                f"df <- data.frame(\n"
                f"  x = data$x,\n"
                f"  y = data$y\n"
                f")\n\n"
                f"p <- ggplot(df, aes(x = x, y = y)) +\n"
                f"  geom_line(color = nature_palette[1], linewidth = 0.5) +\n"
                f"  labs(x = '{xlabel}', y = '{ylabel}') +\n"
                f"  nature_theme\n\n"
                f"ggsave('figure_line.pdf', p, width = 3.5, height = 3.0, dpi = 300)\n"
            )
        elif figure_type == "scatter":
            plot_code = (
                f"df <- data.frame(\n"
                f"  x = data$x,\n"
                f"  y = data$y\n"
                f")\n\n"
                f"p <- ggplot(df, aes(x = x, y = y)) +\n"
                f"  geom_point(color = nature_palette[1], size = 1.5) +\n"
                f"  labs(x = '{xlabel}', y = '{ylabel}') +\n"
                f"  nature_theme\n\n"
                f"ggsave('figure_scatter.pdf', p, width = 3.5, height = 3.0, dpi = 300)\n"
            )
        elif figure_type == "box":
            plot_code = (
                f"df <- data.frame(\n"
                f"  category = rep({data.get('categories', [])}, sapply(data$values, length)),\n"
                f"  value = unlist(data$values)\n"
                f")\n\n"
                f"p <- ggplot(df, aes(x = category, y = value, fill = category)) +\n"
                f"  geom_boxplot(linewidth = 0.3, outlier.size = 0.5) +\n"
                f"  scale_fill_manual(values = nature_palette) +\n"
                f"  labs(x = '{xlabel}', y = '{ylabel}') +\n"
                f"  nature_theme\n\n"
                f"ggsave('figure_box.pdf', p, width = 3.5, height = 3.0, dpi = 300)\n"
            )
        elif figure_type == "heatmap":
            plot_code = (
                f"library(reshape2)\n\n"
                f"mat <- do.call(rbind, data$matrix)\n"
                f"df_melt <- melt(mat)\n\n"
                f"p <- ggplot(df_melt, aes(x = Var2, y = Var1, fill = value)) +\n"
                f"  geom_tile() +\n"
                f"  scale_fill_viridis_c() +\n"
                f"  labs(x = '{xlabel}', y = '{ylabel}') +\n"
                f"  nature_theme\n\n"
                f"ggsave('figure_heatmap.pdf', p, width = 3.5, height = 3.0, dpi = 300)\n"
            )
        elif figure_type == "violin":
            plot_code = (
                f"df <- data.frame(\n"
                f"  category = rep({data.get('categories', [])}, sapply(data$values, length)),\n"
                f"  value = unlist(data$values)\n"
                f")\n\n"
                f"p <- ggplot(df, aes(x = category, y = value, fill = category)) +\n"
                f"  geom_violin(linewidth = 0.3) +\n"
                f"  geom_boxplot(width = 0.1, linewidth = 0.3) +\n"
                f"  scale_fill_manual(values = nature_palette) +\n"
                f"  labs(x = '{xlabel}', y = '{ylabel}') +\n"
                f"  nature_theme\n\n"
                f"ggsave('figure_violin.pdf', p, width = 3.5, height = 3.0, dpi = 300)\n"
            )
        else:
            return {
                "success": False,
                "error": f"Unsupported figure type: {figure_type}",
                "supported_types": list(FIGURE_TEMPLATES.keys()),
            }

        full_code = common_setup + "\n" + plot_code

        return {
            "success": True,
            "language": "r",
            "figure_type": figure_type,
            "code": full_code,
            "dependencies": ["ggplot2", "dplyr"],
        }


__acasight_plugin__ = NatureFigurePlugin()
