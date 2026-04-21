const fs = require('fs');
const content = fs.readFileSync('H:/HermesPortable/ConfigPanel/api-server.js', 'utf8');
const start = content.indexOf('async function handleDashboardLaunch');
const end = content.indexOf('// ============ GET/POST', start);
const func = content.substring(start, end);
console.log('=== handleDashboardLaunch function ===');
console.log(func);
