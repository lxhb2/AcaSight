// ============================================================
// Python 学习平台 - 主逻辑 (v3.0)
// 使用 Brython (纯 JavaScript Python 实现)
// ============================================================

// 课程数据 - 完整版
const courseData = {
    basePath: "/data/courses",
    courses: [
        {
            name: "【1】Python基础语法",
            icon: "📚",
            color: "linear-gradient(135deg, #00d4ff, #0099cc)",
            chapters: [
                {id: "1-1", name: "千寻的名字", file: "【1】Python基础语法/0~3关：第1个小目标：别叫我萌新/0关-千寻的名字.html"},
                {id: "1-2", name: "萌新的进化", file: "【1】Python基础语法/0~3关：第1个小目标：别叫我萌新/1关-萌新的进化.html"},
                {id: "1-3", name: "灭霸的选择", file: "【1】Python基础语法/0~3关：第1个小目标：别叫我萌新/2关-灭霸的选择.html"},
                {id: "1-4", name: "霍格沃兹的来信", file: "【1】Python基础语法/0~3关：第1个小目标：别叫我萌新/3关-霍格沃兹的来信.html"},
                {id: "1-5", name: "收纳的艺术", file: "【1】Python基础语法/4~7关：第2个小目标：做出我的第一个项目/4关-收纳的艺术.html"},
                {id: "1-6", name: "消灭该怎么的重复（上）", file: "【1】Python基础语法/4~7关：第2个小目标：做出我的第一个项目/5关-消灭该怎么的重复（上）.html"},
                {id: "1-7", name: "消灭该怎么的重复（下）", file: "【1】Python基础语法/4~7关：第2个小目标：做出我的第一个项目/6关-消灭该怎么的重复（下）.html"},
                {id: "1-8", name: "小游戏大学问", file: "【1】Python基础语法/4~7关：第2个小目标：做出我的第一个项目/7关-小游戏大学问.html"},
                {id: "1-9", name: "编程学习的两大瓶颈", file: "【1】Python基础语法/8~11关：第3个小目标：编程思维初探/8关-编程学习的两大瓶颈.html"},
                {id: "1-10", name: "喊出我的名字", file: "【1】Python基础语法/8~11关：第3个小目标：编程思维初探/9关-喊出我的名字.html"},
                {id: "1-11", name: "田忌赛马", file: "【1】Python基础语法/8~11关：第3个小目标：编程思维初探/10关-田忌赛马.html"},
                {id: "1-12", name: "杀死那只机生虫", file: "【1】Python基础语法/8~11关：第3个小目标：编程思维初探/11关-杀死那只机生虫.html"},
                {id: "1-13", name: "我有一个机器人（上）", file: "【1】Python基础语法/12~14关：第4个小目标：学会找对象/12关-我有一个机器人（上）.html"},
                {id: "1-14", name: "我有一个机器人（下）", file: "【1】Python基础语法/12~14关：第4个小目标：学会找对象/13关-我有一个机器人（下）.html"},
                {id: "1-15", name: "命中注定我克你", file: "【1】Python基础语法/12~14关：第4个小目标：学会找对象/14关-命中注定我克你.html"},
                {id: "1-16", name: "计算机的新华字典", file: "【1】Python基础语法/15~17关：第5个小目标：用Python给朋友发个邮件/15关-计算机的新华字典.html"},
                {id: "1-17", name: "哆啦A梦的百宝箱", file: "【1】Python基础语法/15~17关：第5个小目标：用Python给朋友发个邮件/16关-哆啦A梦的百宝箱.html"},
                {id: "1-18", name: "邮件还能这么发", file: "【1】Python基础语法/15~17关：第5个小目标：用Python给朋友发个邮件/17关-邮件还能怎么发.html"},
                {id: "1-19", name: "需求你造吗？我造", file: "【1】Python基础语法/18~19关：第6个小目标：完成一个迷你产品/18关-需求你造吗？我造.html"},
                {id: "1-20", name: "高效偷懒的正确姿势", file: "【1】Python基础语法/18~19关：第6个小目标：完成一个迷你产品/19关-高效偷懒的正确姿势.html"}
            ]
        },
        {
            name: "【2】Python爬虫精进",
            icon: "🕷️",
            color: "linear-gradient(135deg, #ff6b6b, #ee5a24)",
            chapters: [
                {id: "2-1", name: "重新定义上网冲浪", file: "【2】Python爬虫精进/0~1关：第1个小目标：初窥门径/0关-重新定义上网冲浪.html"},
                {id: "2-2", name: "我也可以写个网页", file: "【2】Python爬虫精进/0~1关：第1个小目标：初窥门径/1关-我也可以写个网页.html"},
                {id: "2-3", name: "爬虫初体验", file: "【2】Python爬虫精进/2~7关：第2个小目标：爬虫小成/2关-爬虫初体验.html"},
                {id: "2-4", name: "解密吴氏私厨", file: "【2】Python爬虫精进/2~7关：第2个小目标：爬虫小成/3关-解密吴氏私厨.html"},
                {id: "2-5", name: "寻找周杰伦", file: "【2】Python爬虫精进/2~7关：第2个小目标：爬虫小成/4关-寻找周杰伦.html"},
                {id: "2-6", name: "狂热粉丝", file: "【2】Python爬虫精进/2~7关：第2个小目标：爬虫小成/5关-狂热粉丝.html"},
                {id: "2-7", name: "爬到的数据存哪里？", file: "【2】Python爬虫精进/2~7关：第2个小目标：爬虫小成/6关-爬到的数据存哪里？.html"},
                {id: "2-8", name: "复习：温故而知新", file: "【2】Python爬虫精进/2~7关：第2个小目标：爬虫小成/7关-复习：温故而知新.html"},
                {id: "2-9", name: "带着小饼干登录", file: "【2】Python爬虫精进/8~10关：第3个小目标：更上层楼/8关-带着小饼干登录.html"},
                {id: "2-10", name: "指挥浏览器自动工作", file: "【2】Python爬虫精进/8~10关：第3个小目标：更上层楼/9关-指挥浏览器自动工作.html"},
                {id: "2-11", name: "让爬虫按时向你汇报", file: "【2】Python爬虫精进/8~10关：第3个小目标：更上层楼/10关-让爬虫按时向你汇报.html"},
                {id: "2-12", name: "建立爬虫军队", file: "【2】Python爬虫精进/11~15关：第4个小目标：拨云见日/11关-建立爬虫军队.html"},
                {id: "2-13", name: "吃什么不会胖？", file: "【2】Python爬虫精进/11~15关：第4个小目标：拨云见日/12关-吃什么不会胖？.html"},
                {id: "2-14", name: "各司其职的爬虫公司", file: "【2】Python爬虫精进/11~15关：第4个小目标：拨云见日/13关-各司其职的爬虫公司.html"},
                {id: "2-15", name: "出任爬虫公司CEO", file: "【2】Python爬虫精进/11~15关：第4个小目标：拨云见日/14关-出任爬虫公司CEO.html"},
                {id: "2-16", name: "逢山开路与不甘庸碌", file: "【2】Python爬虫精进/11~15关：第4个小目标：拨云见日/15关-逢山开路与不甘庸碌.html"}
            ]
        },
        {
            name: "【3】python办公自动化",
            icon: "🤖",
            color: "linear-gradient(135deg, #4caf50, #2e7d32)",
            chapters: [
                {id: "3-1", name: "导学课：快速获取文件名", file: "【3】python办公自动化/第1关：导学课：快速获取文件名/风变编程.html"},
                {id: "3-2", name: "txt文件筛选与读写", file: "【3】python办公自动化/第2关：初入职场：txt文件筛选与读写/风变编程.html"},
                {id: "3-3", name: "csv文件读写", file: "【3】python办公自动化/第2关：初入职场：txt文件筛选与读写/第2关 课后补充：读写csv文件/风变编程.html"},
                {id: "3-4", name: "openpyx基础知识", file: "【3】python办公自动化/第3关：Python,Excle：openpyx基础知识/风变编程.html"},
                {id: "3-5", name: "问题排查", file: "【3】python办公自动化/第3关：Python,Excle：openpyx基础知识/第3关 课后补充：问题排查/风变编程.html"},
                {id: "3-6", name: "表格读写", file: "【3】python办公自动化/第4关：慢即是快：表格读写/风变编程.html"},
                {id: "3-7", name: "技术改变工作：筛选匹配", file: "【3】python办公自动化/第5关：技术改变工作：筛选匹配/风变编程.html"},
                {id: "3-8", name: "批量发送email", file: "【3】python办公自动化/第5关：技术改变工作：筛选匹配/第5关 课后补充：批量发送email/风变编程.html"},
                {id: "3-9", name: "设置excel样式", file: "【3】python办公自动化/第6关：转正危机：设置excel样式/风变编程.html"},
                {id: "3-10", name: "添加excel图表", file: "【3】python办公自动化/第6关：转正危机：设置excel样式/第6关 课后补充1：添加excel图表/风变编程.html"},
                {id: "3-11", name: "绘制条形图", file: "【3】python办公自动化/第6关：转正危机：设置excel样式/第6关 课后补充2：绘制条形图/风变编程.html"}
            ]
        },
        {
            name: "【4】Python数据分析",
            icon: "📊",
            color: "linear-gradient(135deg, #9c27b0, #7b1fa2)",
            chapters: [
                {id: "4-1", name: "数据的世界", file: "【4】Python数据分析实训课/第1关 数据的世界：数据探索/风变编程.html"},
                {id: "4-2", name: "三问三答", file: "【4】Python数据分析实训课/第2关 三问三答：数据分析1/风变编程.html"},
                {id: "4-3", name: "临门一脚", file: "【4】Python数据分析实训课/第3关 临门一脚：数据可视化1/风变编程.html"},
                {id: "4-4", name: "口罩生意", file: "【4】Python数据分析实训课/第4关 口罩生意：数据清洗/风变编程.html"},
                {id: "4-5", name: "难度升级", file: "【4】Python数据分析实训课/第5关 难度升级：数据分析2/风变编程.html"},
                {id: "4-6", name: "看见数据", file: "【4】Python数据分析实训课/第6关 看见数据：数据可视化2/风变编程.html"}
            ]
        }
    ]
};

// 练习题库
const exercisesDB = {
    "1-1": {difficulty: 1, title: "print()函数和变量", items: [
        {q: "使用print()输出Hello Python", a: "print('Hello Python')", hint: "使用单引号或双引号"}
    ]},
    "1-3": {difficulty: 2, title: "条件判断", items: [
        {q: "如果age>=18打印成年", a: "age = 20\nif age >= 18:\n    print('成年')", hint: "使用if语句"}
    ]}
};

// 全局变量
let progress = JSON.parse(localStorage.getItem("windlearn_progress") || "{}");
let currentCourse = null;
let currentChapter = null;
let currentExercise = null;
let editor = null;
let aiModel = "qwen2.5:3b";
let brythonReady = false;

function init() {
    renderCourseList();
    initEditor();
    checkAI();
    document.getElementById("progressCount").textContent = Object.keys(progress).length;
    initBrython();
}

function renderCourseList() {
    const cl = document.getElementById("courseList");
    let totalChapters = 0;
    cl.innerHTML = "";
    courseData.courses.forEach((c, ci) => {
        totalChapters += c.chapters.length;
        let chaptersHtml = c.chapters.map((ch, i) => 
            '<div class="chapter-item" onclick="loadChapter(' + ci + ',' + i + ')" data-cid="' + ch.id + '">' + ch.name + '</div>'
        ).join("");
        cl.innerHTML += '<div class="course-item"><div class="course-header" onclick="toggleCourse(' + ci + ')"><div class="course-icon" style="background:' + c.color + '">' + c.icon + '</div><div class="course-info"><div class="course-name">' + c.name + '</div><div class="course-count">' + c.chapters.length + ' 章</div></div><span class="course-arrow">▶</span></div><div class="chapter-list">' + chaptersHtml + '</div></div>';
    });
    document.getElementById("chapterCount").textContent = totalChapters;
}

function toggleCourse(idx) {
    document.querySelectorAll(".course-arrow")[idx].classList.toggle("open");
    document.querySelectorAll(".chapter-list")[idx].classList.toggle("open");
}

function loadChapter(ci, chi) {
    const c = courseData.courses[ci];
    const ch = c.chapters[chi];
    currentCourse = ci;
    currentChapter = chi;
    document.querySelectorAll(".chapter-item").forEach(el => el.classList.remove("active"));
    document.querySelector('[data-cid="' + ch.id + '"]').classList.add("active");
    document.getElementById("currentTitle").textContent = ch.name;
    document.getElementById("studyFrame").src = courseData.basePath + "/" + ch.file;
    loadExercises(ch.id);
    progress[ch.id] = true;
    localStorage.setItem("windlearn_progress", JSON.stringify(progress));
    document.getElementById("progressCount").textContent = Object.keys(progress).length;
    showToast("已加载: " + ch.name);
}

function loadExercises(chapterId) {
    const el = document.getElementById("exercisesList");
    const ex = exercisesDB[chapterId];
    if (!ex) {
        el.innerHTML = '<div class="exercise-item"><div class="exercise-title">暂无练习题</div></div>';
        return;
    }
    const diffLabels = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐"};
    el.innerHTML = ex.items.map((item, idx) => 
        '<div class="exercise-item' + (idx === 0 ? ' active' : '') + '" onclick="selectExercise(this, ' + idx + ')"><div class="exercise-title">' + item.q + '</div><div class="exercise-difficulty"><span class="diff-' + ex.difficulty + '">' + diffLabels[ex.difficulty] + '</span></div></div>'
    ).join("");
}

function selectExercise(el, idx) {
    const ex = exercisesDB[document.querySelector(".chapter-item.active")?.getAttribute("data-cid")];
    if (!ex) return;
    if (el) {
        document.querySelectorAll(".exercise-item").forEach(e => e.classList.remove("active"));
        el.classList.add("active");
    }
    currentExercise = ex.items[idx];
    editor.setValue("# 题目: " + currentExercise.q + "\n# 提示: " + (currentExercise.hint || "暂无提示") + "\n\n");
    document.getElementById("outputContent").textContent = "请编写代码解答上述题目...";
}

function switchMode(mode) {
    document.querySelectorAll(".mode-tab").forEach(t => {
        const hasActive = (mode === "study" && t.textContent.includes("学习")) || (mode === "practice" && t.textContent.includes("练习"));
        t.classList.toggle("active", hasActive);
    });
    document.getElementById("studyView").classList.toggle("active", mode === "study");
    document.getElementById("practiceView").classList.toggle("active", mode === "practice");
}

function initEditor() {
    editor = CodeMirror.fromTextArea(document.getElementById("codeEditor"), {
        mode: "python",
        theme: "pythonidea",
        lineNumbers: true,
        indentUnit: 4
    });
    editor.addKeyMap({"Ctrl-Enter": runPython, "Cmd-Enter": runPython});
    document.getElementById("outputContent").textContent = "Python环境加载中...";
}

function initBrython() {
    // 动态加载 Brython
    const script = document.createElement('script');
    script.src = "/brython/brython.js";
    script.onload = function() {
        // 设置路径
        window.brython = window.__BRYTHON__;
        if (window.brython) {
            brythonReady = true;
            document.getElementById("outputContent").textContent = "✅ Python环境已就绪！可以运行代码了。";
            document.getElementById("outputStatus").textContent = "就绪";
            document.getElementById("outputStatus").className = "output-status status-ready";
            showToast("Python环境已就绪");
        }
    };
    script.onerror = function() {
        document.getElementById("outputContent").textContent = "❌ Python环境加载失败，请刷新重试";
    };
    document.head.appendChild(script);
}

function runPython() {
    const outputContent = document.getElementById("outputContent");
    const outputStatus = document.getElementById("outputStatus");
    const code = editor.getValue();
    
    if (!brythonReady) {
        outputContent.textContent = "Python环境加载中，请稍候...";
        return;
    }
    
    outputStatus.textContent = "运行中";
    outputStatus.className = "output-status status-loading";
    outputContent.textContent = ">>> " + code.split("\n").join("\n>>> ") + "\n\n";
    
    try {
        // 使用 Brython 运行代码
        brython({
            ipy_id: 'python-output',
            debug: 0
        });
        
        // 创建一个隐藏的 script 标签运行 Python 代码
        const pyCode = code.replace(/"/g, '\\"').replace(/\n/g, '\\n');
        const outputId = 'python_output_' + Date.now();
        
        // 直接在Brython环境中执行
        const brythonScript = document.createElement('script');
        brythonScript.type = 'text/python3';
        brythonScript.text = 
import sys
from browser import document, window

class Output:
    def __init__(self):
        self.output = []
    def write(self, text):
        if text.strip():
            self.output.append(text)
    def flush(self):
        pass

sys.stdout = Output()
sys.stderr = Output()

try:
    exec()
    result = ''.join(sys.stdout.output)
    if result:
        window.runResultCallback(result, '')
    else:
        window.runResultCallback('(执行完成)', '')
except Exception as e:
    window.runResultCallback(str(e), 'error')
;
        
        document.body.appendChild(brythonScript);
        
        // 设置回调
        window.runResultCallback = function(result, error) {
            if (error) {
                outputContent.textContent += "\n❌ 错误: " + error;
                outputStatus.textContent = "错误";
                outputStatus.className = "output-status status-error";
            } else {
                outputContent.textContent += result;
                outputStatus.textContent = "完成";
                outputStatus.className = "output-status status-ready";
            }
            brythonScript.remove();
        };
        
    } catch (e) {
        outputContent.textContent += "\n❌ 错误: " + e.message;
        outputStatus.textContent = "错误";
        outputStatus.className = "output-status status-error";
    }
}

async function checkAI() {
    try {
        const res = await fetch("http://localhost:11434/api/tags");
        if (res.ok) {
            const data = await res.json();
            const models = data.models || [];
            document.getElementById("aiStatus").textContent = "在线";
            document.getElementById("aiStatus").className = "ai-status online";
        }
    } catch (e) {
        document.getElementById("aiStatus").textContent = "离线";
        document.getElementById("aiStatus").className = "ai-status offline";
    }
}

async function askAI() {
    const input = document.getElementById("aiInput");
    const question = input.value.trim();
    if (!question) return;
    const chat = document.getElementById("aiChat");
    chat.innerHTML += '<div class="ai-message user">' + question + '</div>';
    chat.innerHTML += '<div class="ai-message ai">正在思考...</div>';
    input.value = "";
    chat.scrollTop = chat.scrollHeight;
    
    let context = "你是Python学习助手。请用中文回答，代码用`python包裹。\n\n";
    if (currentChapter !== null) {
        const ch = courseData.courses[currentCourse]?.chapters[currentChapter];
        if (ch) context += "当前课程: " + ch.name + "\n";
    }
    context += "\n用户问题: " + question;
    
    try {
        const res = await fetch("http://localhost:11434/api/generate", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({model: aiModel, prompt: context, stream: false})
        });
        const data = await res.json();
        const answer = data.response || "AI 响应失败";
        chat.removeChild(chat.lastChild);
        chat.innerHTML += '<div class="ai-message ai">' + answer.replace(/\n/g, "<br>") + '</div>';
    } catch (e) {
        chat.removeChild(chat.lastChild);
        chat.innerHTML += '<div class="ai-message ai">❌ AI 连接失败</div>';
    }
    chat.scrollTop = chat.scrollHeight;
}

function showToast(msg) {
    const t = document.getElementById("toast");
    t.textContent = msg;
    t.classList.add("show");
    setTimeout(() => t.classList.remove("show"), 2500);
}

window.onload = init;
