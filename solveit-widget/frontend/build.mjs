import * as esbuild from "esbuild";

await esbuild.build({
  entryPoints: ["src/index.jsx"],
  bundle: true,
  format: "esm",
  outfile: "../src/solveit_widget/static/index.js",
  minify: true,
  jsxFactory: "h",
  jsxFragment: "Fragment",
  loader: { ".jsx": "jsx" },
});

console.log("built static/index.js");
