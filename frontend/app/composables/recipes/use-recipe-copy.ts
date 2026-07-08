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

  function formatRecipeIngredient(ingredient: RecipeIngredient) {
    if (ingredient.title) {
      return `${ingredient.title}:`;
    }

    if (ingredient.referencedRecipe?.name) {
      return `- ${ingredient.referencedRecipe.name}`;
    }

    const quantity = ingredient.quantity ? String(ingredient.quantity) : "";
    const unit = ingredient.unit?.abbreviation || ingredient.unit?.name || "";
    const food = ingredient.food?.name || "";
    const note = cleanRecipeText(ingredient.note);
    const line = [quantity, unit, food].filter(Boolean).join(" ").trim();

    return `- ${[line, note].filter(Boolean).join(" - ")}`;
  }

  function formatRecipeForCopy(recipe: Recipe, fallbackName = "") {
    const lines: string[] = [recipe.name || fallbackName];
    const description = cleanRecipeText(recipe.description);
    const source = cleanRecipeText(recipe.source || recipe.orgURL);

    if (description) {
      lines.push("", description);
    }

    if (source) {
      lines.push("", `${i18n.t("recipe.source")}: ${source}`);
    }

    if (recipe.createdBy) {
      lines.push(`${i18n.t("recipe.created-by")}: ${recipe.createdBy}`);
    }

    if (recipe.recipeYield) {
      lines.push(`${i18n.t("recipe.recipe-yield")}: ${recipe.recipeYield}`);
    }

    const ingredientsText = formatRecipeIngredientsForCopy(recipe);
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

  function formatRecipeIngredientsForCopy(recipe: Recipe) {
    if (!recipe.recipeIngredient?.length) {
      return "";
    }

    const lines: string[] = [i18n.t("recipe.ingredients")];
    recipe.recipeIngredient.forEach((ingredient) => {
      const formattedIngredient = formatRecipeIngredient(ingredient);
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

  function formatRecipeIngredientsAndInstructionsForCopy(recipe: Recipe) {
    return [
      formatRecipeIngredientsForCopy(recipe),
      formatRecipeInstructionsForCopy(recipe),
    ].filter(Boolean).join("\n\n").trim();
  }

  function copyRecipeText(recipe: Recipe, fallbackName = "") {
    copyText(formatRecipeForCopy(recipe, fallbackName));
  }

  return {
    copyRecipeText,
    formatRecipeForCopy,
    formatRecipeIngredientsAndInstructionsForCopy,
    formatRecipeIngredientsForCopy,
    formatRecipeInstructionsForCopy,
  };
}
