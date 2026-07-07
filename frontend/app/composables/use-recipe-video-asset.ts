import { useUserApi } from "~/composables/api";
import { alert } from "~/composables/use-toast";

function fileBaseName(fileName: string) {
  const lastDot = fileName.lastIndexOf(".");
  return lastDot > 0 ? fileName.substring(0, lastDot) : fileName;
}

export function useRecipeVideoAsset() {
  const api = useUserApi();
  const i18n = useI18n();

  async function attachVideoToRecipe(recipeSlug: string, videoFile: File | null) {
    if (!videoFile) {
      return true;
    }

    const { error } = await api.recipes.createAsset(recipeSlug, {
      name: fileBaseName(videoFile.name),
      icon: "mdi-play",
      file: videoFile,
      extension: videoFile.name.split(".").pop() || "",
    });

    if (error) {
      alert.error(i18n.t("events.something-went-wrong"));
      return false;
    }

    return true;
  }

  return {
    attachVideoToRecipe,
  };
}
