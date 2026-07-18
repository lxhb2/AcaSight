"""
LaTeX 编辑器路由 — Feature 6.5

提供 LaTeX 编译、模板列表、数学公式渲染等接口。
"""

import os
import shutil
import tempfile
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
import structlog

logger = structlog.get_logger()
router = APIRouter()


# ==================== LaTeX 模板 ====================

LATEX_TEMPLATES = {
    "article": {
        "id": "article",
        "name": "学术论文 (Article)",
        "description": "标准学术论文模板，包含标题、摘要、章节",
        "content": r"""\documentclass[12pt,a4paper]{article}
\usepackage[UTF8]{ctex}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{geometry}
\geometry{margin=2.5cm}

\title{论文标题}
\author{作者姓名}
\date{\today}

\begin{document}
\maketitle

\begin{abstract}
摘要内容。本文研究了……
\end{abstract}

\section{引言}
引言部分。

\section{方法}
方法部分。

\section{结果}
结果部分。

\section{讨论}
讨论部分。

\section{结论}
结论部分。

\begin{thebibliography}{9}
\bibitem{ref1} 作者. 标题. 期刊, 年份.
\end{thebibliography}

\end{document}
""",
    },
    "report": {
        "id": "report",
        "name": "研究报告 (Report)",
        "description": "较长的文档模板，包含章节结构",
        "content": r"""\documentclass[12pt,a4paper]{report}
\usepackage[UTF8]{ctex}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{geometry}
\geometry{margin=2.5cm}

\title{研究报告标题}
\author{作者姓名}
\date{\today}

\begin{document}
\maketitle
\tableofcontents

\chapter{绪论}
\section{研究背景}
研究背景内容。

\section{研究目的}
研究目的内容。

\chapter{文献综述}
文献综述内容。

\chapter{研究方法}
\section{实验设计}
实验设计内容。

\section{数据采集}
数据采集内容。

\chapter{实验结果}
实验结果内容。

\chapter{分析与讨论}
分析与讨论内容。

\chapter{结论与展望}
结论与展望内容。

\begin{thebibliography}{9}
\bibitem{ref1} 作者. 标题. 期刊, 年份.
\end{thebibliography}

\end{document}
""",
    },
    "beamer": {
        "id": "beamer",
        "name": "学术演示 (Beamer)",
        "description": "Beamer 幻灯片模板，适合学术报告",
        "content": r"""\documentclass[aspectratio=169]{beamer}
\usepackage[UTF8]{ctex}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{booktabs}

\usetheme{Madrid}
\usecolortheme{default}

\title{演示标题}
\author{作者姓名}
\institute{机构名称}
\date{\today}

\begin{document}

\begin{frame}
\titlepage
\end{frame}

\begin{frame}{目录}
\tableofcontents
\end{frame}

\section{引言}
\begin{frame}{引言}
\begin{itemize}
  \item 第一个要点
  \item 第二个要点
  \item 第三个要点
\end{itemize}
\end{frame}

\section{方法}
\begin{frame}{研究方法}
\begin{enumerate}
  \item 步骤一
  \item 步骤二
  \item 步骤三
\end{enumerate}
\end{frame}

\section{结果}
\begin{frame}{实验结果}
\begin{center}
\begin{tabular}{lcc}
\toprule
项目 & 数值A & 数值B \\
\midrule
实验1 & 0.95 & 0.87 \\
实验2 & 0.92 & 0.91 \\
\bottomrule
\end{tabular}
\end{center}
\end{frame}

\section{结论}
\begin{frame}{结论}
\begin{block}{主要发现}
主要发现内容。
\end{block}
\begin{alertblock}{注意事项}
注意事项内容。
\end{alertblock}
\end{frame}

\begin{frame}
\centering
\Huge 谢谢！
\end{frame}

\end{document}
""",
    },
}


# ==================== 请求模型 ====================

class CompileRequest(BaseModel):
    """LaTeX 编译请求"""
    latex_source: str
    engine: Optional[str] = "xelatex"  # xelatex | pdflatex


class RenderMathRequest(BaseModel):
    """数学公式渲染请求"""
    expression: str
    display_mode: Optional[bool] = True


# ==================== 接口 ====================

@router.post("/compile")
async def compile_latex(req: CompileRequest):
    """
    编译 LaTeX 源码为 PDF

    尝试使用 xelatex/pdflatex 编译，如果 LaTeX 未安装则返回 503。
    """
    engine = req.engine or "xelatex"

    # 检查 LaTeX 引擎是否可用
    if not shutil.which(engine):
        available_engines = []
        for eng in ["xelatex", "pdflatex", "lualatex"]:
            if shutil.which(eng):
                available_engines.append(eng)

        if not available_engines:
            raise HTTPException(
                503,
                detail=(
                    "LaTeX 引擎未安装。请安装 TeX Live 或 MiKTeX。"
                    "安装后可使用 xelatex/pdflatex/lualatex 编译。"
                    "Ubuntu: sudo apt install texlive-xetex texlive-lang-chinese"
                    " | Windows: 下载 MiKTeX https://miktex.org/download"
                ),
            )
        # 回退到可用引擎
        engine = available_engines[0]
        logger.info(f"LaTeX engine fallback: using {engine}")

    # 创建临时目录编译
    work_dir = tempfile.mkdtemp(prefix="acasight_latex_")
    try:
        tex_file = os.path.join(work_dir, "main.tex")
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(req.latex_source)

        # 执行编译命令
        import subprocess
        cmd = [engine, "-interaction=nonstopmode", "-halt-on-error", "main.tex"]
        result = subprocess.run(
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )

        pdf_file = os.path.join(work_dir, "main.pdf")
        if not os.path.exists(pdf_file):
            # 编译失败，返回错误日志
            log_file = os.path.join(work_dir, "main.log")
            error_log = ""
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                    error_log = f.read()[-2000:]  # 取最后 2000 字符
            raise HTTPException(
                400,
                detail={
                    "message": "LaTeX 编译失败",
                    "engine": engine,
                    "stdout": result.stdout[-1000:] if result.stdout else "",
                    "stderr": result.stderr[-1000:] if result.stderr else "",
                    "log_tail": error_log,
                },
            )

        # 读取 PDF
        with open(pdf_file, "rb") as f:
            pdf_bytes = f.read()

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'inline; filename="output.pdf"',
                "X-LaTeX-Engine": engine,
            },
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(408, detail="LaTeX 编译超时（60秒），请检查源码是否有死循环")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LaTeX compile error: {e}")
        raise HTTPException(500, detail=f"编译过程出错: {str(e)}")
    finally:
        # 清理临时目录
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


@router.get("/templates")
async def list_templates():
    """列出可用的 LaTeX 模板"""
    templates = []
    for tid, tpl in LATEX_TEMPLATES.items():
        templates.append({
            "id": tpl["id"],
            "name": tpl["name"],
            "description": tpl["description"],
        })
    return {"templates": templates}


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """获取指定模板的完整内容"""
    if template_id not in LATEX_TEMPLATES:
        raise HTTPException(404, detail=f"模板 '{template_id}' 不存在")
    tpl = LATEX_TEMPLATES[template_id]
    return {
        "id": tpl["id"],
        "name": tpl["name"],
        "description": tpl["description"],
        "content": tpl["content"],
    }


@router.post("/render-math")
async def render_math(req: RenderMathRequest):
    """
    渲染 LaTeX 数学公式

    尝试使用 KaTeX (Python 绑定) 渲染，不可用时返回格式化的占位结果。
    """
    try:
        # 尝试使用 katex Python 包
        import katex as _katex
        html = _katex.render_to_string(
            req.expression,
            display_mode=req.display_mode,
        )
        return {"success": True, "html": html, "expression": req.expression}
    except ImportError:
        pass

    # 回退：返回样式化的占位结果
    escaped_expr = req.expression.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if req.display_mode:
        html = f'<div style="padding:8px 16px;margin:8px 0;background:var(--canvas-soft, #f8f9fa);border-radius:6px;font-family:serif;font-size:1.1em;text-align:center;overflow-x:auto;border:1px solid #e0e0e0;">{escaped_expr}</div>'
    else:
        html = f'<span style="padding:2px 6px;background:var(--canvas-soft, #f8f9fa);border-radius:3px;font-family:serif;font-size:0.95em;border:1px solid #e0e0e0;">{escaped_expr}</span>'

    return {
        "success": True,
        "html": html,
        "expression": req.expression,
        "note": "KaTeX Python 包未安装，显示原始公式。安装: pip install katex",
    }
