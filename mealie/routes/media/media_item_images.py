from enum import StrEnum

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import UUID4
from starlette.responses import FileResponse

from mealie.core.config import get_app_dirs
from mealie.services.item_image_service import ItemImageService

router = APIRouter(prefix="/item-images")


class ItemImageKind(StrEnum):
    food = "food"
    tool = "tool"


class ItemImageType(StrEnum):
    original = "original.webp"
    small = "min-original.webp"
    tiny = "tiny-original.webp"


@router.get("/{group_id}/{kind}/{file_name}")
async def get_item_image(
    group_id: UUID4,
    kind: ItemImageKind,
    file_name: ItemImageType = ItemImageType.tiny,
    name: str = Query(..., min_length=1, max_length=250),
):
    root_dir = get_app_dirs().DATA_DIR.joinpath("item-images", str(group_id))
    image_path = ItemImageService.image_path(root_dir, kind.value, name, file_name.value).resolve()

    if not image_path.is_relative_to(root_dir.resolve()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST)

    if not image_path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    return FileResponse(image_path, media_type="image/webp")
