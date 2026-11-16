// Repo docs (*.md, cron prompts) are working notes for builders, not site
// pages. Pages serves the repo root, so answer them with a plain 404.
// Pages _redirects ignores a 404 status, so this lives in Functions.
const PRIVATE_DOC = /(\.md$)|(^\/cron_prompts\/)/i;

export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (PRIVATE_DOC.test(url.pathname)) {
    return new Response("Not found", {
      status: 404,
      headers: { "content-type": "text/plain; charset=utf-8", "x-robots-tag": "noindex" },
    });
  }
  return context.next();
}
