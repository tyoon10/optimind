import adapter from "@sveltejs/adapter-cloudflare";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    // Cloudflare Pages: static-prerendered app + the /api/oauth/token route as a Pages Function.
    adapter: adapter(),
    // Scaffold v1 has placeholder PWA icons; don't fail prerender on missing static assets.
    prerender: { handleHttpError: "warn" },
  },
};

export default config;
