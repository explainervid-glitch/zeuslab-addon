// Bump the version, build the zip, tag it and publish a GitHub release.
//
//   npm run release -- patch|minor|major|<x.y.z> [--notes "text"] [--dry-run]
//
// Steps:
//   1. Checks: on main, clean working tree, up to date with origin, tag free, gh logged in.
//   2. Writes the new version to __init__.py (bl_info), version.json and package.json.
//      version.json also gets the changelog and a download_url that points to the
//      release asset on GitHub.
//   3. Builds dist/ZeusLab-v<version>.zip with scripts/package.js.
//   4. Commits "chore(release): v<version>", creates tag v<version>, pushes both.
//   5. Creates the GitHub release with the zip attached.
//
// Without --notes, the changelog is the list of commit subjects since the last tag.

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const BRANCH = "main";
const ADDON_NAME = "ZeusLab";

// ---------- args ----------

const args = process.argv.slice(2);
const dryRun = args.includes("--dry-run");
const notesIndex = args.indexOf("--notes");
// A literal "\n" typed in the shell becomes a real line break.
const notesArg = notesIndex >= 0 && args[notesIndex + 1] ? args[notesIndex + 1].replace(/\\n/g, "\n") : null;
const bump = args.find((a, i) => !a.startsWith("--") && (notesIndex < 0 || i !== notesIndex + 1));

if (!bump || (notesIndex >= 0 && !notesArg)) {
  console.error('Usage: npm run release -- patch|minor|major|<x.y.z> [--notes "text"] [--dry-run]');
  process.exit(1);
}

// ---------- helpers ----------

function run(cmd, cmdArgs, opts = {}) {
  return execFileSync(cmd, cmdArgs, { cwd: ROOT, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], ...opts }).trim();
}

// Commands that change git or GitHub. Printed only on --dry-run.
function act(cmd, cmdArgs) {
  console.log(`> ${cmd} ${cmdArgs.map((a) => (/\s/.test(a) ? JSON.stringify(a) : a)).join(" ")}`);
  if (!dryRun) execFileSync(cmd, cmdArgs, { cwd: ROOT, stdio: "inherit" });
}

function fail(message) {
  console.error(`Release stopped: ${message}`);
  process.exit(1);
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, file), "utf8"));
}

function writeFile(file, text) {
  if (dryRun) console.log(`(dry run) would write ${file}`);
  else fs.writeFileSync(path.join(ROOT, file), text);
}

function nextVersion(current, kind) {
  if (/^\d+\.\d+\.\d+$/.test(kind)) return kind;
  const [major, minor, patch] = current.split(".").map(Number);
  if (kind === "major") return `${major + 1}.0.0`;
  if (kind === "minor") return `${major}.${minor + 1}.0`;
  if (kind === "patch") return `${major}.${minor}.${patch + 1}`;
  fail(`unknown bump "${kind}". Use patch, minor, major or x.y.z.`);
}

function isNewer(a, b) {
  const pa = a.split(".").map(Number);
  const pb = b.split(".").map(Number);
  for (let i = 0; i < 3; i++) if (pa[i] !== pb[i]) return pa[i] > pb[i];
  return false;
}

function githubRepo() {
  const url = run("git", ["remote", "get-url", "origin"]);
  const m = url.match(/github\.com[:/]([^/]+)\/(.+?)(\.git)?$/);
  if (!m) fail(`origin is not a GitHub remote: ${url}`);
  return `${m[1]}/${m[2]}`;
}

function changelogSinceLastTag() {
  let range = [];
  try {
    range = [`${run("git", ["describe", "--tags", "--abbrev=0"])}..HEAD`];
  } catch (_) {
    // No tags yet: use the whole history.
  }
  const subjects = run("git", ["log", "--no-merges", "--format=%s", ...range])
    .split("\n")
    .filter((s) => s && !s.startsWith("chore(release)"));
  // Drop duplicate subjects, keep the newest first.
  return [...new Set(subjects)].map((s, i) => `${i + 1}. ${s}`).join("\n");
}

// ---------- checks ----------

const versionJson = readJson("version.json");
const current = versionJson.version.join(".");
const version = nextVersion(current, bump);
const tag = `v${version}`;
const repo = githubRepo();
const zipName = `${ADDON_NAME}-v${version}.zip`;

if (!isNewer(version, current)) fail(`${version} is not newer than ${current}.`);

const branch = run("git", ["rev-parse", "--abbrev-ref", "HEAD"]);
if (branch !== BRANCH) fail(`on branch "${branch}", switch to "${BRANCH}" first.`);

const dirty = run("git", ["status", "--porcelain"]);
if (dirty) fail(`working tree has uncommitted changes. Commit or stash them first.\n${dirty}`);

run("git", ["fetch", "--tags", "origin"]);
const behind = run("git", ["rev-list", "--count", `HEAD..origin/${BRANCH}`]);
if (behind !== "0") fail(`${BRANCH} is ${behind} commit(s) behind origin. Pull first.`);

if (run("git", ["tag", "--list", tag])) fail(`tag ${tag} already exists.`);

try {
  run("gh", ["auth", "status"]);
} catch (_) {
  fail("GitHub CLI is not installed or not logged in. Run: gh auth login");
}

const changelog = notesArg || changelogSinceLastTag() || `Release ${tag}`;

console.log(`Releasing ${current} -> ${version} on ${repo}${dryRun ? " (dry run)" : ""}`);
console.log(`Changelog:\n${changelog}\n`);

// ---------- bump ----------

const versionTuple = version.split(".").map(Number);

const initPath = "__init__.py";
const init = fs.readFileSync(path.join(ROOT, initPath), "utf8");
const initVersion = /("version"\s*:\s*)\([^)]*\)/;
if (!initVersion.test(init)) fail(`no "version" in bl_info of ${initPath}.`);
writeFile(initPath, init.replace(initVersion, `$1(${versionTuple.join(", ")})`));

versionJson.version = versionTuple;
versionJson.download_url = `https://github.com/${repo}/releases/download/${tag}/${zipName}`;
versionJson.changelog = changelog;
writeFile("version.json", JSON.stringify(versionJson, null, 4) + "\n");

const pkg = readJson("package.json");
pkg.version = version;
writeFile("package.json", JSON.stringify(pkg, null, 2) + "\n");

// ---------- build ----------

if (dryRun) {
  console.log("(dry run) would run scripts/package.js");
} else {
  execFileSync(process.execPath, [path.join(__dirname, "package.js")], { cwd: ROOT, stdio: "inherit" });
}
const zipPath = path.join("dist", zipName);
if (!dryRun && !fs.existsSync(path.join(ROOT, zipPath))) fail(`${zipPath} was not built.`);

// ---------- commit, tag, push, release ----------

act("git", ["add", initPath, "version.json", "package.json"]);
act("git", ["commit", "-m", `chore(release): ${tag}`]);
act("git", ["tag", "-a", tag, "-m", `${ADDON_NAME} ${tag}`]);
act("git", ["push", "origin", BRANCH, tag]);
act("gh", [
  "release", "create", tag, zipPath,
  "--repo", repo,
  "--title", `${ADDON_NAME} ${tag}`,
  "--notes", changelog,
  "--verify-tag",
]);

if (dryRun) {
  console.log("\nDry run finished. Nothing was changed.");
  process.exit(0);
}
console.log(`\nReleased ${tag}: https://github.com/${repo}/releases/tag/${tag}`);
console.log("Installed addons find this release through the GitHub API (updater/updater.py).");
