import * as esbuild from "esbuild";
import { readFileSync } from "node:fs";

const outfile = "../src/solveit_widget/static/index.js";

await esbuild.build({
  entryPoints: ["src/index.jsx"],
  bundle: true,
  format: "esm",
  outfile,
  minify: true,
  jsxFactory: "h",
  jsxFragment: "Fragment",
  loader: { ".jsx": "jsx" },
});

// anywidget (>=0.9) requires a DEFAULT export implementing { render }/{ initialize }.
// A bare named `export function render` fails with "does not appear to be a valid
// anywidget". Assert the bundle ships a default export so this can't regress silently.
const built = readFileSync(outfile, "utf8");
if (!/\bas default\b|\bdefault:/.test(built)) {
  throw new Error(
    "Build produced no default export — anywidget will reject this bundle. " +
      "Ensure index.jsx ends with `export default { render }`.",
  );
}

console.log("built static/index.js (default export verified)");
