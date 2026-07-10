export const RECIPE_VIDEO_EXTENSIONS = [
  "3g2",
  "3gp",
  "amv",
  "asf",
  "avi",
  "divx",
  "dv",
  "f4v",
  "flv",
  "m1v",
  "m2ts",
  "m2v",
  "m4v",
  "mkv",
  "mod",
  "mov",
  "mp4",
  "mpe",
  "mpeg",
  "mpg",
  "mts",
  "mxf",
  "nut",
  "ogm",
  "ogv",
  "rm",
  "rmvb",
  "roq",
  "tod",
  "ts",
  "vob",
  "webm",
  "wmv",
  "y4m",
] as const;

export const RECIPE_VIDEO_ACCEPT = [
  "video/*",
  ...RECIPE_VIDEO_EXTENSIONS.map(extension => `.${extension}`),
].join(",");

const VIDEO_FILE_PATTERN = new RegExp(`\\.(${RECIPE_VIDEO_EXTENSIONS.join("|")})$`, "i");

export function isRecipeVideoFile(fileName?: string | null) {
  return Boolean(fileName && VIDEO_FILE_PATTERN.test(fileName));
}

export function recipeVideoMimeType(fileName?: string | null) {
  const extension = fileName?.split(".").pop()?.toLowerCase();
  if (extension === "webm") return "video/webm";
  if (extension === "mov") return "video/quicktime";
  if (extension === "ogv" || extension === "ogm") return "video/ogg";
  if (extension === "mkv") return "video/x-matroska";
  if (extension === "avi") return "video/x-msvideo";
  if (extension === "wmv") return "video/x-ms-wmv";
  return "video/mp4";
}
