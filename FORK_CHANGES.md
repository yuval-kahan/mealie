# שינויים שבוצעו ב-fork

עודכן לאחרונה: 2026-07-07

מסמך זה מתעד את ההתאמות שבוצעו ב-fork המקומי של Mealie, כדי שיהיה קל להבין מה נוסף לפני העלאה ל-GitHub.

## תקציר

ה-fork מוסיף ל-Mealie יכולות AI נוחות יותר, יצירת מתכון מטקסט חופשי, תמיכה רחבה בהעלאת וידאו למתכונים, תצוגת מדיה עליונה בתוך עמוד המתכון, ניהול API מהיר מהתפריט הצדדי, ניווט מהיר לספרים/קטגוריות/תגיות, ומחיקה מהירה של מתכונים מרשימת המתכונים.

## ניהול ספקי AI ו-API

- נוסף חלון API מהיר בתפריט הצדדי, מתחת להגדרות, כדי לפתוח ולנהל ספקי AI בלי להיכנס למסכי הגדרות עמוקים.
- נוספה רשימת ספקים מוכנה לבחירה:
  - OpenAI
  - Google Gemini
  - Anthropic Claude
  - Custom / Local OpenAI-compatible
- בחירת ספק מעדכנת אוטומטית:
  - שם ספק ברירת מחדל
  - Base URL
  - רשימת מודלים
  - מודל ברירת מחדל
- נוספה רשימת מודלים מובנית לכל ספק גדול.
- במודלים של Google Gemini נוספו הערות ליד המודל לגבי חינם / בתשלום ועלויות משוערות, כדי שיהיה קל לבחור מודל מתאים.
- נוספה תמיכה בכמה API keys עבור Google Gemini.
  אפשר להפריד מפתחות בשורה חדשה או בפסיק.
- עבור Gemini, המפתח הראשון משמש לקריאות בפועל, וכל המפתחות נבדקים לפני שמירה.
- נוספה בדיקת API key לפני שמירה.
  הבדיקה נעשית דרך endpoints של רשימת מודלים / גישה לספק, כדי להימנע מקריאת generation רגילה שעלולה לעלות כסף.
- אם המפתח לא תקין, אי אפשר לשמור את הספק.
- במסך עריכת ספק קיים מוצג האם הספק הוא ברירת המחדל או לא.
- ניתן לראות, לערוך, למחוק ולבחור ספקים קיימים מתוך חלון ה-API המהיר.

קבצים מרכזיים:

- `frontend/app/components/Domain/Group/GroupAIProviderDialog.vue`
- `frontend/app/components/Domain/Group/GroupAIProviderSettingsEditor.vue`
- `frontend/app/components/Layout/LayoutParts/AppSidebar.vue`
- `frontend/app/composables/use-ai-providers.ts`
- `mealie/services/openai/openai.py`
- `mealie/routes/groups/controller_group_ai_providers.py`
- `mealie/routes/admin/admin_management_ai_providers.py`
- `mealie/repos/repository_ai_provider.py`
- `mealie/schema/group/ai_providers.py`

## יצירת מתכון מטקסט חופשי בעזרת AI

- נוספה אפשרות ליצור מתכון מטקסט חופשי, למשל כתבה, טקסט שהועתק מאתר, או מתכון בעברית/אנגלית.
- נוסף כפתור מהיר בתפריט הצדדי: "יצירה מטקסט".
- הכפתור פותח popup מהיר שבו מדביקים את הטקסט וה-AI מפרק אותו למתכון מסודר.
- נוסף גם route ייעודי ליצירה מטקסט: `/r/create/text`.
- ה-AI מחזיר מבנה מסודר לפי schema, ולא טקסט חופשי.
- השדות הנתמכים כוללים:
  - שם מתכון
  - תיאור
  - כמות / מנות
  - זמני הכנה / בישול / זמן כולל
  - מרכיבים עם כותרות קבוצות
  - הוראות הכנה
  - הערות
  - קטגוריות
  - תגיות
  - כלים / ציוד
- נוספה אפשרות לתרגם את המתכון לשפת הממשק בזמן היצירה.
- נוספה אפשרות להריץ parsing למרכיבים אחרי הייבוא.
- קטגוריות, תגיות וכלים שה-AI מחזיר נוצרים או ממוחזרים אוטומטית לפי מה שכבר קיים בקבוצה.
- נוסף prompt ייעודי שמנחה את ה-AI לא לדלג על תוכן שימושי, לא להמציא מידע, ולשמור ציוד/הגשה/מקור בהערות או בכלים לפי הצורך.

קבצים מרכזיים:

- `frontend/app/components/Domain/Recipe/RecipeCreateFromTextForm.vue`
- `frontend/app/pages/g/[groupSlug]/r/create/text.vue`
- `frontend/app/pages/g/[groupSlug]/r/create.vue`
- `frontend/app/components/Layout/DefaultLayout.vue`
- `frontend/app/lib/api/user/recipes/recipe.ts`
- `mealie/routes/recipe/recipe_crud_routes.py`
- `mealie/services/recipe/recipe_service.py`
- `mealie/schema/openai/recipe.py`
- `mealie/services/openai/prompts/recipes/parse-recipe-text.txt`

## תמיכה בווידאו במתכונים

- נוספה אפשרות להעלות קבצי וידאו למתכון.
- סיומות וידאו נתמכות:
  - `mp4`
  - `webm`
  - `mov`
  - `m4v`
  - `ogv`
- השרת מגיש וידאו כ-inline media עם MIME type מתאים, כך שהדפדפן יכול להציג נגן במקום להוריד את הקובץ.
- נוספה קומפוננטת העלאת וידאו משותפת לשימוש בכל מסכי היצירה.
- נוסף helper שמאפשר לצרף וידאו למתכון אחרי יצירה.
- וידאו נתמך במסכי היצירה הבאים:
  - יצירה ידנית
  - יצירה מטקסט
  - יבוא מ-URL
  - יבוא URL מרובה
  - יבוא HTML / JSON
  - יצירה מתמונה
  - יבוא ZIP
- בייבוא URL מרובה נוספה תמיכה בווידאו לכל שורה, כולל endpoint multipart ייעודי ושיוך הווידאו למתכון הנכון לאחר סיום הייבוא.

קבצים מרכזיים:

- `frontend/app/components/Domain/Recipe/RecipeVideoAssetUpload.vue`
- `frontend/app/composables/use-recipe-video-asset.ts`
- `frontend/app/pages/g/[groupSlug]/r/create/new.vue`
- `frontend/app/pages/g/[groupSlug]/r/create/text.vue`
- `frontend/app/pages/g/[groupSlug]/r/create/url.vue`
- `frontend/app/pages/g/[groupSlug]/r/create/bulk.vue`
- `frontend/app/pages/g/[groupSlug]/r/create/html.vue`
- `frontend/app/pages/g/[groupSlug]/r/create/image.vue`
- `frontend/app/pages/g/[groupSlug]/r/create/zip.vue`
- `mealie/routes/media/media_recipe.py`
- `mealie/routes/recipe/recipe_crud_routes.py`
- `mealie/services/scraper/recipe_bulk_scraper.py`

## תצוגת מדיה בראש עמוד המתכון

- התמונות והווידאו של המתכון מוצגים עכשיו בראש עמוד המתכון, באזור הכותרת, ולא רק בכרטיס "נכסים" בצד.
- הווידאו מוצג כנגן אמיתי עם controls של הדפדפן:
  - Play / Pause
  - פס התקדמות
  - Volume
  - Fullscreen
- נוספה גלריית מדיה עליונה שמציגה:
  - תמונת מתכון ראשית
  - תמונות שהועלו כנכסים
  - וידאו שהועלה כנכס
- כרטיס "נכסים" בצד מסנן תמונות ווידאו, כדי למנוע כפילות. הוא נשאר לקבצים רגילים כמו PDF, טקסט וכו'.
- נוסף סליידר אחד ששולט על הגודל של כל המדיה יחד.
- ברירת המחדל של הסליידר היא הגודל הקטן ביותר.
- המדיה מוצגת בפריסה צמודה אחד ליד השני, עם מרווח קטן.
- בחירת גודל המדיה נשמרת בדפדפן באמצעות localStorage.

קבצים מרכזיים:

- `frontend/app/components/Domain/Recipe/RecipeMediaAssets.vue`
- `frontend/app/components/Domain/Recipe/RecipeAssets.vue`
- `frontend/app/components/Domain/Recipe/RecipePage/RecipePage.vue`
- `frontend/app/components/Domain/Recipe/RecipePage/RecipePageParts/RecipePageInfoCard.vue`
- `frontend/app/components/Domain/Recipe/RecipePage/RecipePageParts/RecipePageOrganizers.vue`

## שיפורי רשימת מתכונים ופעולות מהירות

- נוספה אפשרות למחוק מתכון מתוך תפריט שלוש הנקודות בכרטיס מתכון, בלי להיכנס לעמוד המתכון עצמו.
- פעולה זו נוספה גם לתצוגות כרטיסים שונות של מתכונים.

קבצים מרכזיים:

- `frontend/app/components/Domain/Recipe/RecipeContextMenu/RecipeContextMenu.vue`
- `frontend/app/components/Domain/Recipe/RecipeContextMenu/RecipeContextMenuContent.vue`
- `frontend/app/components/Domain/Recipe/RecipeCard.vue`
- `frontend/app/components/Domain/Recipe/RecipeCardMobile.vue`
- `frontend/app/components/Domain/Recipe/RecipeCardSection.vue`
- `frontend/app/components/Domain/Recipe/RecipeExplorerPage/RecipeExplorerPage.vue`

## ניווט מהיר לספרים, קטגוריות ותגיות

- נוסף סרגל ניווט משני שנצמד לסרגל הצד הראשי, בלי להחליף את הניווט הקיים.
- הסרגל מותאם לכיוון השפה דרך Vuetify RTL/LTR.
  בעברית הוא יושב בצד הימני/התחלתי של הממשק, ובאנגלית בצד השמאלי/התחלתי.
- הסרגל יכול להציג:
  - ספרי בישול / Cookbooks
  - קטגוריות
  - תגיות
- ניתן למזער ולהגדיל את הסרגל בלחיצה על אייקון הניווט המהיר.
- מצב המזעור נשמר מקומית בדפדפן, כך שהוא נשאר גם לאחר רענון.
- המשתמש יכול לבחור מתוך כפתור ההגדרות של הסרגל מה להציג ומה להסתיר.
- בתוך הגדרות הניווט המהיר נוספה גרירה ושחרור לשינוי סדר הסעיפים, למשל תגיות לפני ספרים או קטגוריות לפני תגיות.
- סדר הסעיפים נשמר מקומית בדפדפן וממשיך להשפיע גם אחרי רענון.
- ברירת המחדל מציגה ספרי בישול, וניתן להפעיל קטגוריות ותגיות לפי הצורך.
- לחיצה על ספר פותחת את עמוד ה-Cookbook.
- לחיצה על קטגוריה או תגית מסננת את עמוד המתכונים לפי אותו פריט.
- דף המתכונים עודכן כך ששינוי query מה-sidebar מסנכרן את החיפוש גם כשהמשתמש כבר נמצא בדף המתכונים, בלי צורך ברענון.

קבצים מרכזיים:

- `frontend/app/components/Layout/LayoutParts/AppOrganizerSidebar.vue`
- `frontend/app/components/Layout/LayoutParts/AppSidebar.vue`
- `frontend/app/components/Layout/DefaultLayout.vue`
- `frontend/app/composables/use-users/preferences.ts`
- `frontend/app/composables/use-recipe-explorer-search.ts`
- `frontend/app/types/application-types.ts`
- `frontend/app/lang/messages/he-IL.json`
- `frontend/app/lang/messages/en-US.json`

## שיפורי ממשק ותרגום

- נוספו מחרוזות תרגום בעברית ובאנגלית עבור:
  - יצירה מטקסט
  - העלאת וידאו
  - גודל וידאו / מדיה
  - הגדרות API וספקי AI
  - בדיקת API key
  - הודעות Gemini מרובות מפתחות
  - ניווט מהיר לספרים, קטגוריות ותגיות
- שופר צבע הטקסט של כפתור "יצירה מטקסט" בתפריט הצדדי כדי שיהיה קריא.
- נוספה גישה מהירה יותר ליצירה מטקסט, בנוסף לתפריט היצירה הרגיל.

קבצים מרכזיים:

- `frontend/app/lang/messages/he-IL.json`
- `frontend/app/lang/messages/en-US.json`
- `frontend/app/components/Layout/DefaultLayout.vue`
- `frontend/app/components/Layout/LayoutParts/AppSidebar.vue`

## פיתוח והרצה מקומית

- נוספו קבצים להרצת סביבת פיתוח מקומית ומהירה יותר.
- נוספו קבצי Docker Compose מותאמים לפיתוח/hot reload.
- נוסף script להרצת frontend מקומית.
- עודכנו הגדרות שקשורות לסיומות שורה וקבצי shell כדי להפחית בעיות Windows/Linux.

קבצים מרכזיים:

- `dev-frontend.ps1`
- `docker-compose.custom.yml`
- `docker-compose.dev-hot.yml`
- `.gitattributes`
- `docker/entry.sh`
- `docker/healthcheck.sh`
- `docker/setup_nltk_data.sh`

## API ו-endpoints חדשים/מורחבים

- נוסף endpoint ליצירת מתכון מטקסט:
  - `POST /api/recipes/create/text`
- נוסף endpoint לייבוא URL מרובה עם קבצי וידאו:
  - `POST /api/recipes/create/url/bulk/assets`
- הורחב endpoint נכסי מתכון כך שיקבל גם קבצי וידאו:
  - `POST /api/recipes/{slug}/assets`
- נוספה בדיקת גישה לספק AI לפני שמירה, כדי לאמת API key בלי לבצע generation רגיל.

## הערות חשובות

- רשימות המודלים בספקי AI הן רשימות מובנות בקוד. מומלץ לעדכן אותן מדי פעם כי ספקי AI משנים מודלים, שמות ותמחור.
- בדיקת API key מנסה להימנע מקריאת generation בתשלום, אבל ספקים חיצוניים עדיין יכולים להטיל rate limits או לשנות מדיניות.
- תמיכת `MOV` בדפדפן תלויה בקידוד של הקובץ. אם קובץ `MOV` מסוים לא מתנגן ב-Chrome, ייתכן שצריך להוסיף בעתיד המרה אוטומטית ל-`MP4`.
- גודל המדיה בראש המתכון נשמר כרגע בדפדפן של המשתמש, לא כשדה קבוע במתכון.
- התמיכה הישירה ב-Anthropic מיועדת בעיקר לפיצ'רי טקסט. תמונה ואודיו נשארים תלויים בספקים שתומכים בפורמט המתאים.

## ביקורת יציבות, RAM ו-CPU

- בוצעה סקירת `git diff` ממוקדת לנקודות שעלולות ליצור הצטברות משאבים:
  - timers
  - watchers
  - event listeners
  - object URLs
  - localStorage גדל
  - HTTP/API clients
  - משימות רקע והעלאות קבצים
- נוסף ניקוי מפורש ל-`AsyncOpenAI` אחרי קריאות chat completion ותמלול אודיו, כדי למנוע הצטברות connection pools או חיבורי HTTP פתוחים אחרי הרבה פעולות AI.
- בדיאלוג ספקי AI נוסף ניקוי ל-debounce timer של בדיקת API key כאשר הדיאלוג נסגר או הקומפוננטה יורדת מהמסך.
- תוצאות validation ישנות של API key מבוטלות לוגית אם הדיאלוג נסגר או אם המשתמש שינה את הנתונים בזמן שהבדיקה עדיין רצה.
- בניווט המהיר עודכן state של dropdowns כך שהוא נבנה מחדש לפי הסעיפים הנוכחיים, במקום לצבור מפתחות ישנים אם שמות/קבוצות משתנים.
- בנכסי מתכון נוסף ניקוי של הגדרות גודל וידאו מ-localStorage כאשר asset וידאו נמחק.
- וידאו בעמוד המתכון משתמש ב-`preload="metadata"` ולא טוען את כל הקובץ מראש.
- לא נמצאו `ObjectURL` חדשים ללא `revokeObjectURL` בשינויים שנוספו.
- העלאות וידאו מרובות לייבוא URL נשמרות זמנית בתיקיית temp ונמחקות ב-`finally` לאחר סיום משימת הייבוא.

## בדיקות שבוצעו

במהלך העבודה הורצו בדיקות frontend נקודתיות וגם build מלא:

- `npm exec eslint -- ...`
- `npm run build`
- `python -m py_compile ...` לקבצי backend שנגעו ב-AI/ייבוא/מתכונים
- `git diff --check`
- בדיקות JSON לקבצי תרגום
- בדיקות זמינות מקומית ל-frontend/backend (`200` ב-localhost)

ה-build עובר, אך קיימות אזהרות קיימות של הפרויקט לגבי chunk size / circular re-export / Vuetify CSS minify. האזהרות אינן קשורות ישירות לשינויים של ה-fork ולא עצרו את ה-build.
