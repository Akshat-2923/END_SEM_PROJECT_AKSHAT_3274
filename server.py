"""DharaScope FastAPI ASGI Server Entrypoint."""

import src.config  # MUST be first to configure PROJ_DATA/PROJ_LIB before rasterio/GDAL initialize
import os
import uvicorn

from src.api.app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("server:app", host=host, port=port, reload=True)
