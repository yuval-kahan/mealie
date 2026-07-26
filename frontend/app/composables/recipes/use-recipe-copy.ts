import type { Recipe, RecipeIngredient } from "~/lib/api/types/recipe";
import { useCopy } from "~/composables/use-copy";

export function useRecipeCopy() {
  const i18n = useI18n();
  const { copyText } = useCopy();

  function cleanRecipeText(value?: string | null) {
    return (value || "")
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/p>/gi, "\n")
      .replace(/<[^>]+>/g, "")
      .replace(/\r\n/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  function formatScaledQuantity(quantity: RecipeIngredient["quantity"], scale: number) {
    const numericQuantity = Number(quantity);
    if (!Number.isFinite(numericQuantity) || numericQuantity === 0) {
      return "";
    }

    return String(Number((numericQuantity * scale).toFixed(6)));
  }

  function formatRecipeIngredient(ingredient: RecipeIngredient, scale = 1) {
    if (ingredient.title) {
      return `${ingredient.title}:`;
    }

    if (ingredient.referencedRecipe?.name) {
      return `- ${ingredient.referencedRecipe.name}`;
    }

    const quantity = formatScaledQuantity(ingredient.quantity, scale);
    const unit = ingredient.unit?.abbreviation || ingredient.unit?.name || "";
    const food = ingredient.food?.name || "";
    const note = cleanRecipeText(ingredient.note);
    const line = [quantity, unit, food].filter(Boolean).join(" ").trim();

    return `- ${[line, note].filter(Boolean).join(" - ")}`;
  }

  function formatRecipeForCopy(recipe: Recipe, fallbackName = "", scale = 1) {
    const lines: string[] = [recipe.name || fallbackName];
    const description = cleanRecipeText(recipe.description);
    const storedSourceTitle = recipe.extras?.sourceTitle;
    const storedSourceUrl = recipe.extras?.sourceUrl;
    const rawSource = cleanRecipeText(recipe.source || recipe.orgURL);
    const sourceUrl = (typeof storedSourceUrl === "string" ? storedSourceUrl.trim() : "")
      || rawSource.match(/https?:\/\/[^\s<>"']+/i)?.[0]
      || "";
    const sourceName = (typeof storedSourceTitle === "string" ? storedSourceTitle.trim() : "")
      || rawSource
        .replace(/\[([^\]]+)\]\(https?:\/\/[^)]+\)/gi, "$1")
        .replace(/https?:\/\/[^\s<>"']+/gi, "")
        .replace(/^[\s|,:;\-–—]+|[\s|,:;\-–—]+$/g, "")
        .trim();

    if (description) {
      lines.push("", description);
    }

    if (sourceName) {
      lines.push("", `${i18n.t("recipe.source")}: ${sourceName}`);
    }

    if (sourceUrl) {
      lines.push(`${i18n.t("recipe.source-link")}: ${sourceUrl}`);
    }

    if (recipe.createdBy) {
      lines.push(`${i18n.t("recipe.created-by")}: ${recipe.createdBy}`);
    }

    if (recipe.recipeYield) {
      lines.push(`${i18n.t("recipe.recipe-yield")}: ${recipe.recipeYield}`);
    }

    const ingredientsText = formatRecipeIngredientsForCopy(recipe, scale);
    if (ingredientsText) {
      lines.push("", ingredientsText);
    }

    const instructionsText = formatRecipeInstructionsForCopy(recipe);
    if (instructionsText) {
      lines.push("", instructionsText);
    }

    if (recipe.notes?.length) {
      lines.push("", i18n.t("recipe.notes"));
      recipe.notes.forEach((note) => {
        const text = cleanRecipeText(note.text);
        if (text) {
          lines.push(`- ${text}`);
        }
      });
    }

    return lines.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  function formatRecipeIngredientsForCopy(recipe: Recipe, scale = 1) {
    if (!recipe.recipeIngredient?.length) {
      return "";
    }

    const lines: string[] = [i18n.t("recipe.ingredients")];
    recipe.recipeIngredient.forEach((ingredient) => {
      const formattedIngredient = formatRecipeIngredient(ingredient, scale);
      if (formattedIngredient) {
        lines.push(formattedIngredient);
      }
    });

    return lines.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  function formatRecipeInstructionsForCopy(recipe: Recipe) {
    if (!recipe.recipeInstructions?.length) {
      return "";
    }

    const lines: string[] = [i18n.t("recipe.instructions")];
    recipe.recipeInstructions.forEach((instruction, index) => {
      const text = cleanRecipeText(instruction.text || instruction.summary);
      const title = cleanRecipeText(instruction.title);
      if (title) {
        lines.push(`${index + 1}. ${title}`);
      }
      if (text) {
        lines.push(title ? text : `${index + 1}. ${text}`);
      }
    });

    return lines.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  function formatRecipeIngredientsAndInstructionsForCopy(recipe: Recipe, scale = 1) {
    return [
      formatRecipeIngredientsForCopy(recipe, scale),
      formatRecipeInstructionsForCopy(recipe),
    ].filter(Boolean).join("\n\n").trim();
  }

  function copyRecipeText(recipe: Recipe, fallbackName = "", scale = 1) {
    copyText(formatRecipeForCopy(recipe, fallbackName, scale));
  }

  return {
    copyRecipeText,
    formatRecipeForCopy,
    formatRecipeIngredientsAndInstructionsForCopy,
    formatRecipeIngredientsForCopy,
    formatRecipeInstructionsForCopy,
  };
}
