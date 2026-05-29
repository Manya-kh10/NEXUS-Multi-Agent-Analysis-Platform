import fs from 'fs';
import path from 'path';

const files = ['config.js', 'common.js'];
const distDir = 'dist';

if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir, { recursive: true });
}

files.forEach(file => {
  try {
    fs.copyFileSync(file, path.join(distDir, file));
    console.log(`✓ Successfully copied ${file} to ${distDir}/`);
  } catch (err) {
    console.error(`✗ Error copying ${file}:`, err);
  }
});
