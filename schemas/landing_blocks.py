# schemas/landing_blocks.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal


class LandingBlockImage(BaseModel):
    type: Literal["image"] = "image"
    url: str = Field(..., max_length=1000)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("L'URL de l'image ne peut pas être vide")
        return v


class LandingBlockText(BaseModel):
    type: Literal["text"] = "text"
    content: str = Field(..., max_length=5000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Le contenu du texte ne peut pas être vide")
        return v


# A block is either an image block or a text block, distinguished by "type".
# We keep this permissive (dict) at the outer schema level and validate
# the union manually, since pydantic v1/v2 discriminated unions add
# complexity that isn't worth it for two simple variants.
class LandingBlocksUpdate(BaseModel):
    blocks: List[dict] = Field(..., max_length=50)

    @field_validator("blocks")
    @classmethod
    def validate_blocks(cls, v):
        if not isinstance(v, list):
            raise ValueError("blocks doit être une liste")

        validated = []
        for i, block in enumerate(v):
            if not isinstance(block, dict) or "type" not in block:
                raise ValueError(f"Bloc #{i + 1} invalide: 'type' est requis")

            block_type = block.get("type")
            if block_type == "image":
                validated_block = LandingBlockImage(**block)
            elif block_type == "text":
                validated_block = LandingBlockText(**block)
            else:
                raise ValueError(
                    f"Bloc #{i + 1}: type '{block_type}' invalide (attendu: 'image' ou 'text')"
                )

            validated.append(validated_block.model_dump())

        return validated


class LandingBlocksResponse(BaseModel):
    product_id: int
    blocks: List[dict]
