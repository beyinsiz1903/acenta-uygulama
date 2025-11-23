/**
 * Bundle Size Analyzer
 * Analyzes and reports on bundle size
 */
const fs = require('fs');
const path = require('path');

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
};

// Performance budgets (in bytes)
const BUDGETS = {
  'main.js': 500 * 1024,        // 500 KB
  'main.css': 100 * 1024,       // 100 KB
  'vendor.js': 300 * 1024,      // 300 KB
  total: 1 * 1024 * 1024,       // 1 MB total
};

function getFileSizeInBytes(filePath) {
  try {
    const stats = fs.statSync(filePath);
    return stats.size;
  } catch (error) {
    return 0;
  }
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function getColor(size, budget) {
  const ratio = size / budget;
  if (ratio > 1) return colors.red;
  if (ratio > 0.8) return colors.yellow;
  return colors.green;
}

function analyzeBuildFolder(buildPath) {
  const results = {
    files: [],
    totalSize: 0,
    warnings: [],
    errors: [],
  };

  // Check if build folder exists
  if (!fs.existsSync(buildPath)) {
    results.errors.push('Build folder does not exist. Run "npm run build" first.');
    return results;
  }

  // Get all files in static folder
  const staticPath = path.join(buildPath, 'static');
  
  if (fs.existsSync(staticPath)) {
    // Analyze JS files
    const jsPath = path.join(staticPath, 'js');
    if (fs.existsSync(jsPath)) {
      const jsFiles = fs.readdirSync(jsPath);
      jsFiles.forEach(file => {
        if (file.endsWith('.js')) {
          const filePath = path.join(jsPath, file);
          const size = getFileSizeInBytes(filePath);
          
          results.files.push({
            name: `js/${file}`,
            size,
            type: 'js',
          });
          results.totalSize += size;
          
          // Check against budget
          const budget = file.includes('main') ? BUDGETS['main.js'] : 
                        file.includes('vendor') ? BUDGETS['vendor.js'] : null;
          
          if (budget && size > budget) {
            results.warnings.push({
              file: `js/${file}`,
              size: formatBytes(size),
              budget: formatBytes(budget),
              excess: formatBytes(size - budget),
            });
          }
        }
      });
    }

    // Analyze CSS files
    const cssPath = path.join(staticPath, 'css');
    if (fs.existsSync(cssPath)) {
      const cssFiles = fs.readdirSync(cssPath);
      cssFiles.forEach(file => {
        if (file.endsWith('.css')) {
          const filePath = path.join(cssPath, file);
          const size = getFileSizeInBytes(filePath);
          
          results.files.push({
            name: `css/${file}`,
            size,
            type: 'css',
          });
          results.totalSize += size;
          
          // Check against budget
          if (size > BUDGETS['main.css']) {
            results.warnings.push({
              file: `css/${file}`,
              size: formatBytes(size),
              budget: formatBytes(BUDGETS['main.css']),
              excess: formatBytes(size - BUDGETS['main.css']),
            });
          }
        }
      });
    }

    // Analyze media files
    const mediaPath = path.join(staticPath, 'media');
    if (fs.existsSync(mediaPath)) {
      const mediaFiles = fs.readdirSync(mediaPath);
      mediaFiles.forEach(file => {
        const filePath = path.join(mediaPath, file);
        const size = getFileSizeInBytes(filePath);
        
        results.files.push({
          name: `media/${file}`,
          size,
          type: 'media',
        });
        results.totalSize += size;
      });
    }
  }

  // Check total size against budget
  if (results.totalSize > BUDGETS.total) {
    results.errors.push({
      message: 'Total bundle size exceeds budget',
      size: formatBytes(results.totalSize),
      budget: formatBytes(BUDGETS.total),
      excess: formatBytes(results.totalSize - BUDGETS.total),
    });
  }

  return results;
}

function printReport(results) {
  console.log('\n' + colors.blue + '='.repeat(60) + colors.reset);
  console.log(colors.blue + '📦 BUNDLE SIZE ANALYSIS REPORT' + colors.reset);
  console.log(colors.blue + '='.repeat(60) + colors.reset + '\n');

  if (results.errors.length > 0 && results.errors[0] === 'Build folder does not exist. Run "npm run build" first.') {
    console.log(colors.red + '❌ ' + results.errors[0] + colors.reset);
    return;
  }

  // Print files by type
  const filesByType = {
    js: results.files.filter(f => f.type === 'js'),
    css: results.files.filter(f => f.type === 'css'),
    media: results.files.filter(f => f.type === 'media'),
  };

  // JavaScript files
  if (filesByType.js.length > 0) {
    console.log(colors.yellow + '📜 JavaScript Files:' + colors.reset);
    filesByType.js.forEach(file => {
      const budget = file.name.includes('main') ? BUDGETS['main.js'] : 
                    file.name.includes('vendor') ? BUDGETS['vendor.js'] : null;
      const color = budget ? getColor(file.size, budget) : colors.reset;
      console.log(`  ${color}${file.name}: ${formatBytes(file.size)}${colors.reset}`);
    });
    console.log('');
  }

  // CSS files
  if (filesByType.css.length > 0) {
    console.log(colors.yellow + '🎨 CSS Files:' + colors.reset);
    filesByType.css.forEach(file => {
      const color = getColor(file.size, BUDGETS['main.css']);
      console.log(`  ${color}${file.name}: ${formatBytes(file.size)}${colors.reset}`);
    });
    console.log('');
  }

  // Media files
  if (filesByType.media.length > 0) {
    console.log(colors.yellow + '🖼️  Media Files:' + colors.reset);
    filesByType.media.forEach(file => {
      console.log(`  ${file.name}: ${formatBytes(file.size)}`);
    });
    console.log('');
  }

  // Total size
  const totalColor = getColor(results.totalSize, BUDGETS.total);
  console.log(colors.blue + '📊 Total Bundle Size: ' + totalColor + formatBytes(results.totalSize) + colors.reset);
  console.log(colors.blue + '🎯 Budget: ' + formatBytes(BUDGETS.total) + colors.reset);
  
  const remaining = BUDGETS.total - results.totalSize;
  if (remaining > 0) {
    console.log(colors.green + '✅ Remaining: ' + formatBytes(remaining) + colors.reset);
  } else {
    console.log(colors.red + '❌ Over budget by: ' + formatBytes(Math.abs(remaining)) + colors.reset);
  }
  
  console.log('');

  // Warnings
  if (results.warnings.length > 0) {
    console.log(colors.yellow + '⚠️  Warnings:' + colors.reset);
    results.warnings.forEach(warning => {
      console.log(colors.yellow + `  - ${warning.file}: ${warning.size} (budget: ${warning.budget}, excess: ${warning.excess})` + colors.reset);
    });
    console.log('');
  }

  // Errors
  if (results.errors.length > 0) {
    console.log(colors.red + '❌ Errors:' + colors.reset);
    results.errors.forEach(error => {
      console.log(colors.red + `  - ${error.message}: ${error.size} (budget: ${error.budget}, excess: ${error.excess})` + colors.reset);
    });
    console.log('');
  }

  // Recommendations
  if (results.warnings.length > 0 || results.errors.length > 0) {
    console.log(colors.magenta + '💡 Recommendations:' + colors.reset);
    console.log('  1. Enable code splitting for large components');
    console.log('  2. Use dynamic imports for routes');
    console.log('  3. Remove unused dependencies');
    console.log('  4. Enable tree shaking');
    console.log('  5. Optimize images and compress assets');
    console.log('  6. Use React.lazy() for component-level splitting');
    console.log('');
  }

  // Success message
  if (results.warnings.length === 0 && results.errors.length === 0) {
    console.log(colors.green + '✅ All bundle sizes are within budget!' + colors.reset);
    console.log('');
  }

  console.log(colors.blue + '='.repeat(60) + colors.reset + '\n');

  // Exit with error if over budget
  if (results.errors.length > 0) {
    process.exit(1);
  }
}

// Run analysis
const buildPath = path.join(__dirname, 'build');
const results = analyzeBuildFolder(buildPath);
printReport(results);
