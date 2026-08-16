from pystac_client import Client

cat = Client.open("https://earth-search.aws.element84.com/v1")
search = cat.search(
    collections=["sentinel-2-l2a"],
    bbox=[20.30, 37.95, 20.90, 38.55],
    datetime="2026-05-01/2026-05-31",
    query={"eo:cloud_cover": {"lt": 30}},
)
items = sorted(search.item_collection(), key=lambda i: i.properties["eo:cloud_cover"])
print(f"May 2026 scenes, cloud<30%: {len(items)}")
for it in items[:10]:
    p = it.properties
    print(f"{p['datetime'][:10]}  cloud={p['eo:cloud_cover']:5.1f}%  id={it.id}")
