export async function onRequest(context) {
  const country = (context.request.cf && context.request.cf.country) || null;
  return new Response(JSON.stringify({ country }), {
    headers: { "content-type": "application/json", "cache-control": "no-store" }
  });
}
