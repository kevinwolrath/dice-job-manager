from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    colour_brands,
    colour_types,
    dice_job_number_colours,
    health,
    material_stock,
    material_types,
    production_methods,
)
from app.core.config import get_settings

app = FastAPI(title="dice-stock-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(material_types.router)
app.include_router(production_methods.router)
app.include_router(colour_types.router)
app.include_router(colour_brands.router)
app.include_router(material_stock.router)
app.include_router(dice_job_number_colours.router)
