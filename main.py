import math
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

app = FastAPI()

# Utah County's public Export Image endpoint
UTAH_COUNTY_URL = (
    "https://gisaerials.utahcounty.gov/arcgis/rest/services/"
    "NewestImagery/NewestImagery_WGS84/ImageServer/exportImage"
)

TILE_SIZE = 256


def tile_to_bbox(z: int, x: int, y: int):
    """Convert XYZ tile coordinates to WGS84 bounding box (lon/lat)."""
    n = 2.0 ** z

    lon_min = x / n * 360.0 - 180.0
    lon_max = (x + 1) / n * 360.0 - 180.0

    lat_min_rad = math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
    lat_max_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))

    lat_min = math.degrees(lat_min_rad)
    lat_max = math.degrees(lat_max_rad)

    return lon_min, lat_min, lon_max, lat_max


@app.get("/tile/{z}/{y}/{x}")
async def get_tile(z: int, y: int, x: int):
    """
    WindMil requests tiles as /tile/[z]/[y]/[x].
    We convert to a bbox and call Utah County's Export Image endpoint.
    No y-flip — WindMil sends standard XYZ y coordinates.
    """
    lon_min, lat_min, lon_max, lat_max = tile_to_bbox(z, x, y)

    params = {
        "bbox": f"{lon_min},{lat_min},{lon_max},{lat_max}",
        "bboxSR": "4326",
        "size": f"{TILE_SIZE},{TILE_SIZE}",
        "imageSR": "4326",
        "format": "png",
        "pixelType": "U8",
        "noDataInterpretation": "esriNoDataMatchAny",
        "interpolation": "RSP_BilinearInterpolation",
        "f": "image",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(UTAH_COUNTY_URL, params=params)

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Failed to fetch tile from Utah County"
        )

    return Response(
        content=response.content,
        media_type="image/png"
    )


@app.get("/health")
async def health():
    """UptimeRobot pings this to keep the service awake."""
    return {"status": "ok"}
