function UnknownToString(ukn: string | unknown) {
  return typeof ukn === "string" ? ukn : "";
}

export const useStaticRoutes = () => {
  const { $config } = useNuxtApp();
  const prefix = `${$config.public.SUB_PATH}/api`.replace("//", "/");

  // Methods to Generate reference urls for assets/images *
  function recipeImage(recipeId: string, version: string | unknown = "", key: string | number = 1) {
    return `${prefix}/media/recipes/${recipeId}/images/original.webp?rnd=${key}&version=${UnknownToString(version)}`;
  }

  function recipeSmallImage(recipeId: string, version: string | unknown = "", key: string | number = 1) {
    return `${prefix}/media/recipes/${recipeId}/images/min-original.webp?rnd=${key}&version=${UnknownToString(
      version,
    )}`;
  }

  function recipeTinyImage(recipeId: string, version: string | unknown = "", key: string | number = 1) {
    return `${prefix}/media/recipes/${recipeId}/images/tiny-original.webp?rnd=${key}&version=${UnknownToString(
      version,
    )}`;
  }

  function recipeTimelineEventImage(recipeId: string, timelineEventId: string) {
    return `${prefix}/media/recipes/${recipeId}/images/timeline/${timelineEventId}/original.webp`;
  }

  function recipeTimelineEventSmallImage(recipeId: string, timelineEventId: string) {
    return `${prefix}/media/recipes/${recipeId}/images/timeline/${timelineEventId}/min-original.webp`;
  }

  function recipeTimelineEventTinyImage(recipeId: string, timelineEventId: string) {
    return `${prefix}/media/recipes/${recipeId}/images/timeline/${timelineEventId}/tiny-original.webp`;
  }

  function recipeAssetPath(recipeId: string, assetName: string) {
    return `${prefix}/media/recipes/${recipeId}/assets/${assetName}`;
  }

  function itemImage(groupId: string | null | undefined, kind: "food" | "tool", name: string | null | undefined, size: "tiny" | "small" | "original" = "tiny") {
    if (!groupId || !name?.trim()) {
      return "";
    }

    const fileName = size === "original" ? "original.webp" : size === "small" ? "min-original.webp" : "tiny-original.webp";
    return `${prefix}/media/item-images/${groupId}/${kind}/${fileName}?name=${encodeURIComponent(name.trim())}`;
  }

  return {
    recipeImage,
    recipeSmallImage,
    recipeTinyImage,
    recipeTimelineEventImage,
    recipeTimelineEventSmallImage,
    recipeTimelineEventTinyImage,
    recipeAssetPath,
    itemImage,
  };
};
