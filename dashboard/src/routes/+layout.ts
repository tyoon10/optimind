// Client-rendered SPA: pages hydrate in the browser (we use localStorage + OAuth),
// the shell is prerendered to static HTML. The /api/oauth/token POST endpoint is not
// a page, so it's excluded from prerendering and deploys as a Pages Function.
export const ssr = false;
export const prerender = true;
export const trailingSlash = "never";
