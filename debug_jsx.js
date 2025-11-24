const fs = require('fs');

const content = fs.readFileSync('/app/frontend/src/pages/MobileHousekeeping.js', 'utf8');
const lines = content.split('\n');

let divStack = [];
let openCount = 0;
let closeCount = 0;

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  const lineNum = i + 1;
  
  // Find opening divs (more precise)
  const openDivMatches = line.match(/<div(?:\s[^>]*)?>(?!.*<\/div>)/g);
  if (openDivMatches) {
    openDivMatches.forEach(match => {
      divStack.push({ line: lineNum, content: line.trim() });
      openCount++;
      console.log(`Opening div at line ${lineNum}: ${line.trim()}`);
    });
  }
  
  // Find closing divs
  const closeDivMatches = line.match(/<\/div>/g);
  if (closeDivMatches) {
    closeDivMatches.forEach(() => {
      closeCount++;
      if (divStack.length > 0) {
        const opened = divStack.pop();
        console.log(`Closing div at line ${lineNum} (opened at line ${opened.line}): ${line.trim()}`);
      } else {
        console.log(`Extra closing div at line ${lineNum}: ${line.trim()}`);
      }
    });
  }
}

console.log(`\nSummary:`);
console.log(`Total opening divs: ${openCount}`);
console.log(`Total closing divs: ${closeCount}`);
console.log(`Remaining unclosed divs: ${divStack.length}`);
divStack.forEach(div => {
  console.log(`Unclosed div at line ${div.line}: ${div.content}`);
});