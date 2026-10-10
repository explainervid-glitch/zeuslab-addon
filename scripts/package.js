// Zip the addon into dist/ZeusLab-v<version>.zip, ready for Blender's
// "Install from Disk". No external dependencies: uses Node's built-in zlib.
//
// The archive keeps a top-level "ZeusLab/" folder because the addon
// preferences bl_idname and the updater both rely on that folder name.

const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const ROOT = path.resolve(__dirname, "..");
const ADDON_NAME = "ZeusLab";
const DIST_DIR = path.join(ROOT, "dist");

// Paths (relative to ROOT, forward slashes) and patterns left out of the zip.
const EXCLUDE_DIRS = new Set([
  ".git",
  ".vscode",
  ".idea",
  "dist",
  "node_modules",
  "scripts",
  "__pycache__",
]);
const EXCLUDE_FILES = new Set([
  "package.json",
  "package-lock.json",
  ".gitignore",
  ".DS_Store",
  "Thumbs.db",
]);
const EXCLUDE_PATTERNS = [
  /\.pyc$/i,
  /\.pyo$/i,
  /\.blend\d+$/i, // Blender auto backups (.blend1, .blend2, ...)
  /\.backup\d*$/i,
  /\.log$/i,
];

function readVersion() {
  try {
    const data = JSON.parse(fs.readFileSync(path.join(ROOT, "version.json"), "utf8"));
    if (Array.isArray(data.version)) return data.version.join(".");
  } catch (_) {}
  // Fallback: parse bl_info["version"] from __init__.py
  const init = fs.readFileSync(path.join(ROOT, "__init__.py"), "utf8");
  const m = init.match(/"version"\s*:\s*\(([^)]*)\)/);
  return m ? m[1].split(",").map((s) => s.trim()).join(".") : "0.0.0";
}

function isExcluded(name, isDir) {
  if (isDir) return EXCLUDE_DIRS.has(name);
  if (EXCLUDE_FILES.has(name)) return true;
  return EXCLUDE_PATTERNS.some((re) => re.test(name));
}

function collectFiles(dir, rel = "") {
  const out = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  entries.sort((a, b) => a.name.localeCompare(b.name));
  for (const entry of entries) {
    if (isExcluded(entry.name, entry.isDirectory())) continue;
    const abs = path.join(dir, entry.name);
    const relPath = rel ? `${rel}/${entry.name}` : entry.name;
    if (entry.isDirectory()) out.push(...collectFiles(abs, relPath));
    else if (entry.isFile()) out.push({ abs, rel: relPath });
  }
  return out;
}

// --- Minimal ZIP writer (deflate, no zip64) --------------------------------

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  return table;
})();

function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function dosDateTime(date) {
  const time = (date.getHours() << 11) | (date.getMinutes() << 5) | (date.getSeconds() >> 1);
  const day = ((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
  return { time, day };
}

function buildZip(files) {
  const localParts = [];
  const centralParts = [];
  let offset = 0;

  for (const file of files) {
    const data = fs.readFileSync(file.abs);
    const compressed = zlib.deflateRawSync(data, { level: 9 });
    const useDeflate = compressed.length < data.length;
    const body = useDeflate ? compressed : data;
    const method = useDeflate ? 8 : 0;
    const crc = crc32(data);
    const name = Buffer.from(file.name, "utf8");
    const { time, day } = dosDateTime(fs.statSync(file.abs).mtime);

    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4); // version needed
    local.writeUInt16LE(0x0800, 6); // UTF-8 names
    local.writeUInt16LE(method, 8);
    local.writeUInt16LE(time, 10);
    local.writeUInt16LE(day, 12);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(body.length, 18);
    local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(name.length, 26);
    local.writeUInt16LE(0, 28);
    localParts.push(local, name, body);

    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4); // version made by
    central.writeUInt16LE(20, 6); // version needed
    central.writeUInt16LE(0x0800, 8);
    central.writeUInt16LE(method, 10);
    central.writeUInt16LE(time, 12);
    central.writeUInt16LE(day, 14);
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(body.length, 20);
    central.writeUInt32LE(data.length, 24);
    central.writeUInt16LE(name.length, 28);
    central.writeUInt32LE(offset, 42);
    centralParts.push(central, name);

    offset += local.length + name.length + body.length;
  }

  const centralSize = centralParts.reduce((sum, b) => sum + b.length, 0);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(files.length, 8);
  end.writeUInt16LE(files.length, 10);
  end.writeUInt32LE(centralSize, 12);
  end.writeUInt32LE(offset, 16);

  return Buffer.concat([...localParts, ...centralParts, end]);
}

// --- Main -------------------------------------------------------------------

function main() {
  const version = readVersion();
  const files = collectFiles(ROOT).map((f) => ({ ...f, name: `${ADDON_NAME}/${f.rel}` }));
  if (files.length === 0) throw new Error("No files to package.");

  fs.mkdirSync(DIST_DIR, { recursive: true });
  const outPath = path.join(DIST_DIR, `${ADDON_NAME}-v${version}.zip`);
  const zip = buildZip(files);
  fs.writeFileSync(outPath, zip);

  console.log(`Packaged ${files.length} files`);
  console.log(`${path.relative(ROOT, outPath)} (${(zip.length / 1024).toFixed(1)} KB)`);
}

main();
