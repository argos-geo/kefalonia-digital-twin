// T117: geo-locale default. Returns the visitor country from Cloudflare's edge metadata.
export async function onRequest(context) {
  const cf = context.request.cf || {};
  return new Response(JSON.stringify({ country: cf.country || null }), {
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
  });
}
