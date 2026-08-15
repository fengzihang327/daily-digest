// 构建前把仓库根目录 data/ 同步到 public/data/ (前端运行时读取的静态数据)
import { cpSync, mkdirSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const src = resolve(root, "data");
const dest = resolve(root, "frontend/public/data");

rmSync(dest, { recursive: true, force: true });
mkdirSync(dest, { recursive: true });
cpSync(src, dest, { recursive: true });
console.log(`✓ data/ 已同步到 frontend/public/data/ (${src})`);
