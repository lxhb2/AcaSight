const fs = require('fs');
const path = require('path');

const HERMES_ROOT = path.resolve(__dirname, '..');
const HERMES_HOME = path.join(HERMES_ROOT, 'data', '.hermes');
const HERMES_APP = path.join(HERMES_ROOT, 'HermesAgent', 'app');

const PY = 'C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python312\\python.exe';

const batContent = '@echo off\n' +
'chcp 65001 >nul\n' +
'title Hermes Dashboard\n' +
'cd /d "' + HERMES_APP + '"\n' +
'set HERMES_HOME=' + HERMES_HOME + '\n' +
'set HERMES_PORTABLE=1\n' +
'set PYTHONIOENCODING=utf-8\n' +
'set PYTHONLEGACYWINDOWSSTDIO=utf-8\n' +
'"' + PY + '" hermes_cli\\main.py dashboard --port 9119 --host 127.0.0.1 --no-open\n' +
'pause\n';

const batPath = path.join(HERMES_HOME, 'launch_dashboard_fixed.bat');
fs.writeFileSync(batPath, batContent, 'utf8');
console.log('Written:', batPath);
console.log('Content:');
console.log(batContent);
