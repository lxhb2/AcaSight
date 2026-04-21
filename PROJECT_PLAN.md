# Python Learning Platform - Project Plan

## 1. Project Overview

### 1.1 Background
- User has WindChange Programming courses (4 courses, 48+ chapters)
- Course source location: D:\BaiduNetdisk\WindChange Programming
- Requirements: Restore layout + Python editor + AI-assisted learning

### 1.2 Core Features
1. Three-column layout: Course Nav | Learning Content | Practice Module
2. Learning/Practice dual mode: Each chapter has study and practice tabs
3. AI Assistance: Based on Ollama local LLM (current: gemini-3-flash-preview)
4. Practice System: Auto-generated exercises, difficulty levels, AI answers

## 2. Technical Architecture

### 2.1 Frontend
- HTML/CSS/JS: Native development, no framework
- CodeMirror 5: Python code editor
- Pyodide: Browser-based Python runtime
- Local AI: Ollama API (http://localhost:11434)

### 2.2 Module Structure
| Module | Function |
|--------|----------|
| Course Nav | Display all courses, chapters, progress |
| Study Module | iframe loads course source |
| Practice Module | Python editor + AI assistant |
| AI Assistant | Smart Q&A based on Ollama |

## 3. Layout Structure

`
+-------------------------------------------------------------+
| Header: Logo + Course Selection                           |
+------------+--------------------------------+---------------+
| Left Nav   |        Middle Content          | Right Practice|
| (280px)    |        (flex:1)                | (350px)       |
|            |                                |               |
| Course List| +-------------------------+    | Study/Practice|
|            | | [Study] [Practice] tabs  |    | Toggle        |
|            | +-------------------------+    |               |
|            | |                         |    | Python Editor|
|            | | Course Content/Exercises |    | + AI          |
|            | |                         |    |               |
+------------+--------------------------------+---------------+
`

## 4. Practice Module Functions

### 4.1 Python Editor
- CodeMirror syntax highlighting
- Line numbers
- Auto-indent
- Ctrl+Enter to run
- Output display

### 4.2 AI Assistance
- Context-aware: AI recognizes current chapter content
- Smart Q&A: Provide answers to user questions
- Code Debugging: Help users find and fix errors

### 4.3 Exercise System
Exercise topics auto-generated based on course content:

| Difficulty | Symbol | Description |
|------------|--------|-------------|
| Beginner | * | Basic syntax, variables, print |
| Elementary | ** | Loops, conditionals, functions |
| Intermediate | *** | Lists, dicts, file operations |
| Advanced | **** | Crawler, data analysis, automation |

### 4.4 AI Model Configuration
- Current model: gemini-3-flash-preview (can change via Ollama)
- API endpoint: http://localhost:11434/api/generate

## 5. Implementation Plan

### Phase 1: Basic Framework
- [x] Create project file structure
- [x] Implement three-column layout
- [x] Course navigation

### Phase 2: Study Module
- [x] Embed course source
- [x] iframe loading

### Phase 3: Practice Module
- [x] CodeMirror integration
- [x] Pyodide runtime

### Phase 4: AI Integration (Current)
- [ ] Ollama API integration
- [ ] Context-aware functionality
- [ ] Code debugging assistance

### Phase 5: Optimization & Testing
- [ ] Function testing
- [ ] Performance optimization
- [ ] User experience improvement