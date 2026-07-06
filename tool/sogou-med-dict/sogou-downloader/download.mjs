import { writeFileSync, readdirSync, readFileSync, existsSync } from 'fs';
import { execSync } from 'child_process';
import { join } from 'path';

const ROOT = import.meta.dirname;
const DOWN_DIR = join(ROOT, 'down');
const BASE = 'https://pinyin.sogou.com';
const CAT = '/dict/cate/index/132';
const TOTAL_PAGES = 37;

async function fetchPage(page) {
  const url = `${BASE}${CAT}/default/${page}`;
  const res = await fetch(url);
  return res.text();
}

function extractDicts(html) {
  const dicts = [];
  const blocks = html.split('class="dict_detail_block');
  for (let i = 1; i < blocks.length; i++) {
    const b = blocks[i];
    // Download URL
    const dlRe = /href="(https:\/\/pinyin\.sogou\.com\/d\/dict\/download_cell\.php\?id=(\d+)&[^"]+)"/;
    const dlMatch = b.match(dlRe);
    if (!dlMatch) continue;

    // Name
    const nameRe = /class="detail_title"><a\s+href='[^']*'>([^<]+)<\/a>/;
    const nameMatch = b.match(nameRe);

    // Downloads count
    const countRe = /下载次数：<\/div>\s*<div class="show_content">([^<]+)/s;
    const countMatch = b.match(countRe);

    // Update time
    const timeRe = /更新时间：<\/div>\s*<div class="show_content">([^<]+)/s;
    const timeMatch = b.match(timeRe);

    // Sample words
    const sampleRe = /词条样例：<\/div>\s*<div class="show_content">([^<]+)/s;
    const sampleMatch = b.match(sampleRe);

    dicts.push({
      url: dlMatch[1],
      id: dlMatch[2],
      name: nameMatch ? nameMatch[1].trim() : '',
      downloads: countMatch ? countMatch[1].trim() : '',
      updated: timeMatch ? timeMatch[1].trim() : '',
      sample: sampleMatch ? sampleMatch[1].trim() : '',
    });
  }
  return dicts;
}

async function download(dict) {
  const path = join(DOWN_DIR, `${dict.id}.scel`);
  const metaPath = join(DOWN_DIR, `${dict.id}.meta.json`);
  if (existsSync(path)) {
    console.log(`  [${dict.id}] skip (exists)`);
    return path;
  }
  try {
    const res = await fetch(dict.url);
    if (!res.ok) throw new Error(res.status);
    const buf = Buffer.from(await res.arrayBuffer());
    writeFileSync(path, buf);
    writeFileSync(metaPath, JSON.stringify({ name: dict.name, source: BASE + '/dict/detail/index/' + dict.id, downloads: dict.downloads, updated: dict.updated }, null, 2), 'utf-8');
    console.log(`  [${dict.id}] OK (${buf.length} bytes) ${dict.name}`);
    return path;
  } catch (e) {
    console.error(`  [${dict.id}] FAIL: ${e.message}`);
    return null;
  }
}

async function main() {
  console.log('=== 搜狗医学词库下载工具 ===\n');

  // 1. Crawl
  console.log(`[1/4] 爬取 ${TOTAL_PAGES} 页...`);
  const allDicts = [];
  for (let p = 1; p <= TOTAL_PAGES; p++) {
    const html = await fetchPage(p);
    const dicts = extractDicts(html);
    allDicts.push(...dicts);
    console.log(`  第 ${p}/${TOTAL_PAGES} 页: ${dicts.length} 个词库`);
    await new Promise(r => setTimeout(r, 300));
  }
  console.log(`  总计: ${allDicts.length} 个词库\n`);

  // Save full metadata
  writeFileSync(join(DOWN_DIR, 'all_metadata.json'), JSON.stringify(allDicts, null, 2), 'utf-8');

  // 2. Download
  console.log('[2/4] 下载 .scel 文件...');
  let ok = 0, fail = 0;
  for (const dict of allDicts) {
    const path = await download(dict);
    if (path) ok++; else fail++;
    await new Promise(r => setTimeout(r, 400));
  }
  console.log(`  成功: ${ok}, 失败: ${fail}\n`);

  // 3. Convert
  console.log('[3/4] 转换为 .txt...');
  const scel2txt = join(ROOT, '..', 'scel2txt', 'scel2txt.py');
  try {
    execSync(`python "${scel2txt}" "${DOWN_DIR}" "${DOWN_DIR}"`, {
      cwd: ROOT,
      stdio: 'inherit',
      timeout: 300000
    });
  } catch (e) {
    console.error('  转换出错:', e.message);
  }

  // 4. Merge & dedup
  console.log('\n[4/4] 合并去重...');
  const allWords = new Set();
  const files = readdirSync(DOWN_DIR).filter(f => f.endsWith('.txt'));
  let totalBeforeDedup = 0;
  for (const f of files) {
    const content = readFileSync(join(DOWN_DIR, f), 'utf-8');
    for (const line of content.split('\n')) {
      const word = line.trim();
      if (word && word.length > 0 && !word.startsWith('#')) {
        allWords.add(word);
        totalBeforeDedup++;
      }
    }
  }
  const sorted = [...allWords].sort();
  const outPath = join(DOWN_DIR, 'sogou_medical_merged.txt');
  writeFileSync(outPath, sorted.join('\n'), 'utf-8');
  console.log(`  去重前: ${totalBeforeDedup} 条`);
  console.log(`  去重后: ${sorted.length} 条`);
  console.log(`  输出: ${outPath}`);
}

main().catch(console.error);
