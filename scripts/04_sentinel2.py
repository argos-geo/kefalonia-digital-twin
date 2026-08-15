import rioxarray
import pystac_clientplanetary_computer as pc
import stackstac

BBOX = [20.30, 37.95, 20.90, 38.55]

cat = pystac_client.Client.open("https://earth-search.aws.element84.com/v1")
search = cat.search(collections=["sentinel-2-l2a"], bbox=BBOX,
                    datetime="2026-07-01/2026-07-31",
                    query={"eo:cloud_cover": {"lt": 20}})
items = sorted(list(search.items()),
               key=lambda i: i.properties["eo:cloud_cover"])[:4]
print(f"{len(items)} scenes, cloud covers:",
      [round(i.properties["eo:cloud_cover"],1) for i in items])

stack = stackstac.stack(items, assets=["red","nir"], bounds_latlon=BBOX,
                        epsg=32634, resolution=20, chunksize=2048)
print("computing median composite (the long step, 5-15 min)...")
comp = stack.mean(dim="time", skipna=True).compute()

red = comp.sel(band="red").astype("float32")
nir = comp.sel(band="nir").astype("float32")
ndvi = ((nir - red) / (nir + red)).where((nir + red) != 0).clip(min=-1, max=1).fillna(-9999)
ndvi.rio.write_crs("EPSG:32634", inplace=True)
ndvi.rio.write_nodata(-9999, inplace=True)
ndvi.rio.to_raster("data/kefalonia_ndvi_2026-07.tif", driver="COG", compress="deflate")
comp.rio.write_crs("EPSG:32634", inplace=True)
comp.rio.to_raster("data/kefalonia_s2_2026-07.tif", driver="COG", compress="deflate")
print("saved: kefalonia_ndvi_2026-07.tif + kefalonia_s2_2026-07.tif")
