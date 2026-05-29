import fs from 'fs';
import path from 'path';

const files = ['config.js', 'common.js'];
const distDir = 'dist';

if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir, { recursive: true });
}

// Read Vite/System environment variables for API URL injection
const viteApiUrl = process.env.VITE_API_URL || 'https://nexus-multi-agent-analysis-platform.onrender.com';

files.forEach(file => {
  try {
    const srcPath = file;
    const destPath = path.join(distDir, file);

    if (file === 'config.js') {
      // Injects VITE_API_URL build environment variable into production config.js
      let content = fs.readFileSync(srcPath, 'utf8');
      content = content.replace('__VITE_API_URL__', viteApiUrl);
      fs.writeFileSync(destPath, content, 'utf8');
      console.log(`✓ Successfully injected env & copied config.js to ${distDir}/`);
    } else {
      fs.copyFileSync(srcPath, destPath);
      console.log(`✓ Successfully copied ${file} to ${distDir}/`);
    }
  } catch (err) {
    console.error(`✗ Error processing ${file}:`, err);
  }
});
