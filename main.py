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


def tile_to_web_mercator(z: int, x: int, y: int):
    """Convert XYZ tile coordinates to Web Mercator (EPSG:3857) bounding box."""
    n = 2.0 ** z

    # Tile size in Web Mercator meters
    world_size = 20037508.3427892
    tile_width = 2 * world_size / n

    xmin = x * tile_width - world_size
    xmax = xmin + tile_width
    ymax = world_size - y * tile_width
    ymin = ymax - tile_width

    return xmin, ymin, xmax, ymax


@app.get("/tile/{z}/{y}/{x}")
async def get_tile(z: int, y: int, x: int):
    """
    WindMil requests tiles as /tile/[z]/[y]/[x].
    We convert to a Web Mercator bbox and call Utah County's Export Image endpoint.
    """
    xmin, ymin, xmax, ymax = tile_to_web_mercator(z, x, y)

    params = {
        "bbox": f"{xmin},{ymin},{xmax},{ymax}",
        "bboxSR": "3857",
        "size": f"{TILE_SIZE},{TILE_SIZE}",
        "imageSR": "3857",
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
