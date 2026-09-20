from __future__ import annotations

from typing import Any
from app.service.importRecipes.utils import (
    normalize_text,
    normalize_instruction_step,
    normalize_int,
    normalize_items,
    parse_time,
)


def _normalize_recipe(raw: dict[str, Any]) -> dict[str, Any] | None:
    name = normalize_text(raw.get("name") or raw.get("title") or raw.get("headline"))
    if not name:
        return None

    description = normalize_text(raw.get("description") or "")
    instructions = (
        raw.get("recipeInstructions")
        or raw.get("instructions")
        or raw.get("directions")
        or raw.get("method")
    )

    def _extract_steps(entry: Any) -> list[str]:
        if isinstance(entry, dict):
            nested = entry.get("itemListElement") or entry.get("steps")
            if isinstance(nested, list):
                res = []
                section_name = normalize_text(entry.get("name"))
                if section_name:
                    res.append(f"### {section_name}")
                for sub in nested:
                    res.extend(_extract_steps(sub))
                return res

            raw_text = (
                entry.get("text")
                or entry.get("instruction")
                or entry.get("value")
                or entry.get("description")
            )
            text = normalize_instruction_step(raw_text)
            return [text] if text else []
        elif isinstance(entry, str):
            text = normalize_instruction_step(entry)
            return [text] if text else []
        return []

    if isinstance(instructions, list):
        steps = []
        for entry in instructions:
            steps.extend(_extract_steps(entry))

        if steps:
            formatted_steps = []
            idx = 1
            for step in steps:
                if step.startswith("### "):
                    formatted_steps.append(f"\n{step}")
                else:
                    formatted_steps.append(f"{idx}. {step}")
                    idx += 1
            description = (description + "\n\n" if description else "") + "\n".join(
                formatted_steps
            ).strip()
    else:
        instructions_text = normalize_text(instructions)
        if instructions_text:
            description = (
                description + "\n\n" if description else ""
            ) + instructions_text

    recipe: dict[str, Any] = {
        "name": name,
        "description": description,
        "cook_time": parse_time(raw, "cook_time", "cookTime"),
        "prep_time": parse_time(raw, "prep_time", "prepTime"),
        "time": parse_time(raw, "time", "total_time", "totalTime"),
        "yields": normalize_int(
            raw.get("yields")
            or raw.get("servings")
            or raw.get("persons_served")
            or raw.get("recipeYield")
        ),
        "source": normalize_text(raw.get("source") or raw.get("url")),
        "cuisine": normalize_text(raw.get("cuisine") or raw.get("recipeCuisine")),
        "items": normalize_items(
            raw.get("items") or raw.get("ingredients") or raw.get("recipeIngredient")
        ),
    }

    if recipe["time"] is None:
        prep = recipe.get("prep_time") or 0
        cook = recipe.get("cook_time") or 0
        if (prep + cook) > 0:
            recipe["time"] = prep + cook

    photo = normalize_text(
        raw.get("photo") or raw.get("image") or raw.get("preview_picture")
    )
    if photo:
        recipe["photo"] = photo
    photo_data = raw.get("photo_data") or raw.get("photo_large")
    if photo_data and isinstance(photo_data, str) and len(photo_data.strip()) > 20:
        recipe["photo_data"] = photo_data.strip()
    photos = [
        normalize_text(photo)
        for photo in (raw.get("photos") or raw.get("images") or [])
        if normalize_text(photo)
    ]
    if photos:
        recipe["photos"] = photos

    raw_tags = (
        raw.get("tags") or raw.get("categories") or raw.get("recipeCategory") or []
    )
    if isinstance(raw_tags, str):
        raw_tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
    elif isinstance(raw_tags, dict):
        raw_tags = [raw_tags]
    elif not isinstance(raw_tags, list):
        raw_tags = [raw_tags] if raw_tags else []

    def _extract_tag_name(val: Any) -> str:
        if isinstance(val, dict):
            return normalize_text(
                val.get("name")
                or val.get("title")
                or val.get("tag")
                or val.get("value")
            )
        return normalize_text(val)

    tags = []
    for tag in raw_tags:
        tag_name = _extract_tag_name(tag)
        if tag_name and tag_name not in tags:
            tags.append(tag_name)
    if tags:
        recipe["tags"] = tags

    nutrition = raw.get("nutrition")
    if isinstance(nutrition, dict):
        recipe["nutrition"] = nutrition

    return recipe


def json_extract_recipes(payload: Any) -> list[dict[str, Any]]:
    recipes: list[dict[str, Any]] = []

    def add_if_valid(entry: Any):
        if isinstance(entry, dict):
            normalized = _normalize_recipe(entry)
            if normalized:
                recipes.append(normalized)

    if isinstance(payload, dict):
        candidates = (
            payload.get("recipes") or payload.get("data") or payload.get("@graph")
        )
        if isinstance(candidates, list):
            for entry in candidates:
                add_if_valid(entry)
        else:
            add_if_valid(payload)

    elif isinstance(payload, list):
        for entry in payload:
            add_if_valid(entry)

    return recipes
