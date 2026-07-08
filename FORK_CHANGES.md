# שינויים שבוצעו ב-fork

עודכן לאחרונה: 2026-07-08

מסמך זה מתעד את ההתאמות שבוצעו ב-fork המקומי של Mealie, כדי שיהיה קל להבין מה נוסף לפני העלאה ל-GitHub.

## תקציר

ה-fork מוסיף ל-Mealie יכולות AI נוחות יותר, יצירת מתכון מטקסט חופשי/קישור/תמונה, חיפוש מתכונים עם AI בתוך המתכונים הקיימים, שדות מקור/יוצר למתכון, תמיכה רחבה בהעלאת וידאו למתכונים, תצוגת מדיה עליונה בתוך עמוד המתכון, ניהול API מהיר מהתפריט הצדדי, ניווט מהיר לספרים/קטגוריות/תגיות, ומחיקה מהירה של מתכונים מרשימת המתכונים.

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
- אם הוזנו מפתחות Gemini כפולים, הם מזוהים במסך ונשמרים פעם אחת בלבד, תוך שמירה על הסדר המקורי.
- גם צד השרת מנקה כפילויות במפתחות Gemini, כך שקריאות API ישירות לא יכולות לשמור מפתחות כפולים.
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
- נוסף כפתור מהיר בתפריט הצדדי: "יצירה עם AI".
- הכפתור פותח popup מהיר שבו ניתן לבחור בין יצירה מטקסט, יצירה מקישור, או יצירה מתמונה.
- שלושת המצבים בלעדיים: או שמדביקים טקסט, או שמדביקים קישור למתכון באינטרנט, או שמעלים תמונה/תמונות של מתכון.
- ביצירה מקישור, החלון שולח את הקישור למסלול הייבוא עם `useOpenAI`, כך שה-AI מנסה לחלץ את המתכון מהדף.
- ביצירה מתמונה, החלון שולח את התמונות ל-endpoint הקיים של יצירת מתכון מתמונה, ויכול לצרף גם וידאו למתכון שנוצר.
- בפופאפ "יצירה עם AI" נוספה גם העלאת תמונת מתכון נפרדת, לצד העלאת הווידאו. התמונה נשמרת כתמונת הכיסוי של המתכון שנוצר.
- נוסף גם route ייעודי ליצירה מטקסט: `/r/create/text`.
- ה-AI מחזיר מבנה מסודר לפי schema, ולא טקסט חופשי.
- לפני יצירת מתכון, ה-AI מחזיר גם `is_recipe`.
  אם הטקסט לא נראה כמו מתכון, או חסרים שם/רכיבים/הוראות, לא נוצר מתכון והמשתמש מקבל הודעה ברורה.
- השדות הנתמכים כוללים:
  - שם מתכון
  - תיאור
  - כמות / מנות
  - זמני הכנה / בישול / זמן כולל
  - מרכיבים עם כותרות קבוצות
  - סוג מומלץ לרכיב, למשל סוג עגבנייה, פלפל, תפוח אדמה, עשב תיבול, גבינה, נתח בשר או צורת פסטה
  - הוראות הכנה
  - הערות
  - קטגוריות
  - תגיות
  - כלים / ציוד
- נוספה אפשרות לתרגם את המתכון לשפת הממשק בזמן היצירה.
- נוספה אפשרות להריץ parsing למרכיבים אחרי הייבוא.
- קטגוריות, תגיות וכלים שה-AI מחזיר נוצרים או ממוחזרים אוטומטית לפי מה שכבר קיים בקבוצה.
- נוסף שדה אופציונלי ברמת רכיב בשם "סוג מומלץ". השדה זמין בעריכה ידנית, מוצג בעמוד המתכון ובהדפסה, ומשתתף בחיפוש הרגיל ובאינדקס חיפוש AI.
- נוסף prompt ייעודי שמנחה את ה-AI לא לדלג על תוכן שימושי, לא להמציא מידע, ולשמור ציוד/הגשה/מקור בהערות או בכלים לפי הצורך.

קבצים מרכזיים:

- `frontend/app/components/Domain/Recipe/RecipeCreateFromTextForm.vue`
- `frontend/app/pages/g/[groupSlug]/r/create/text.vue`
- `frontend/app/pages/g/[groupSlug]/r/create.vue`
- `frontend/app/components/Layout/DefaultLayout.vue`
- `frontend/app/lib/api/user/recipes/recipe.ts`
- `frontend/app/plugins/axios.ts`
- `mealie/core/exceptions.py`
- `mealie/routes/recipe/recipe_crud_routes.py`
- `mealie/schema/recipe/recipe_scraper.py`
- `mealie/services/recipe/recipe_service.py`
- `mealie/services/scraper/scraper.py`
- `mealie/schema/openai/recipe.py`
- `mealie/services/openai/prompts/recipes/parse-recipe-text.txt`

## חיפוש מתכונים עם AI

- במסך "מצא מתכון" נוספה אפשרות לחפש מתכונים בשפה חופשית בעזרת AI.
- המשתמש יכול לכתוב בקשה כמו "משהו איטלקי עם גבינות" או "ארוחת ערב בלי בשר", וה-AI מחפש בתוך המתכונים הקיימים.
- החיפוש בונה אינדקס מקומי מקוצר של המתכונים בקבוצה:
  - שם מתכון
  - תיאור
  - מקור ויוצר / שף / ספר
  - קטגוריות
  - תגיות
  - כלים
  - רכיבים עיקריים
  - הוראות והערות מקוצרות
- ה-AI מקבל רק shortlist של מועמדים מתוך האינדקס, מחזיר רק `slug` של מתכונים קיימים, והשרת מסנן כל תוצאה שלא באמת קיימת במסד.
- התוצאות מוצגות ככרטיסי מתכון רגילים, עם הסבר קצר למה ה-AI בחר כל מתכון.
- ניתן לבחור כמה תוצאות להחזיר.
- כפתור ניקוי מחזיר את המסך להצעות הרגילות לפי מרכיבים.
- נוסף אינדקס חיפוש AI מקומי ושמור במסד הנתונים.
- לכל מתכון נשמרים:
  - תקציר JSON קצר לשליחה ל-AI.
  - טקסט חיפוש מאוחד.
  - וקטור חיפוש מקומי.
  - hash ותאריך עדכון כדי לזהות מתי צריך לרענן את הקאש.
- בזמן חיפוש, השרת מעדכן רק מתכונים חדשים/משתנים באינדקס.
- רשומת אינדקס מתרעננת אוטומטית גם אחרי 24 שעות, כדי למנוע קאש ישן אם שינוי פנימי לא עדכן את timestamp של המתכון.
- השרת מדרג מקומית את המתכונים לפי הבקשה, ובונה shortlist של מועמדים רלוונטיים.
- ל-AI נשלח רק ה-shortlist ולא כל המתכונים, כדי לחסוך זמן, טוקנים ועלויות.
- ה-AI עדיין מסנן ומחזיר רק מתכונים קיימים מתוך ה-shortlist.

קבצים מרכזיים:

- `frontend/app/pages/g/[groupSlug]/recipes/finder/index.vue`
- `frontend/app/lib/api/user/recipes/recipe.ts`
- `mealie/db/models/recipe/ai_search_index.py`
- `mealie/alembic/versions/2026-07-07-20.25.00_b5c9d1a8f0e6_add_recipe_ai_search_index.py`
- `mealie/routes/recipe/recipe_crud_routes.py`
- `mealie/services/recipe/recipe_service.py`
- `mealie/schema/recipe/recipe_ai_search.py`
- `mealie/schema/openai/recipe_search.py`
- `mealie/services/openai/prompts/recipes/search-recipes.txt`

## מקור ויוצר למתכון

- נוספו למתכון שני שדות חדשים:
  - `source` - מקור חופשי, למשל אתר, בלוג, כתבה, תוכנית טלוויזיה, ספר, עמוד בספר או מגזין.
  - `createdBy` - יוצר / שף / ספר / ערוץ / ארגון שמקושר למתכון.
- השדות מוצגים בראש עמוד המתכון אם יש להם ערך.
- השדות ניתנים לעריכה במסך עריכת פרטי המתכון.
- השדות מופיעים גם בהדפסת מתכון.
- חיפוש המתכונים הרגיל יכול למצוא לפי מקור או יוצר.
- חיפוש ה-AI מקבל את השדות האלה בקטלוג, ולכן אפשר לבקש למשל "ריזוטו של שף מסוים" או "מתכון מספר מסוים".
- יצירת מתכון בעזרת AI יודעת למלא את השדות אם הטקסט כולל מקור, קרדיט, שם שף, ספר, תוכנית, בלוג או כתבה.
- ייבוא מאתר מנסה לשמור `author`/`publisher` קיימים בתור יוצר/מקור.
- נוספה migration למסד הנתונים עבור השדות והאינדקסים שלהם.

קבצים מרכזיים:

- `mealie/db/models/recipe/recipe.py`
- `mealie/alembic/versions/2026-07-07-20.10.00_f8a1c3d9e2b4_add_recipe_source_fields.py`
- `mealie/schema/recipe/recipe.py`
- `mealie/schema/openai/recipe.py`
- `mealie/services/recipe/recipe_service.py`
- `mealie/services/scraper/cleaner.py`
- `mealie/services/scraper/scraper_strategies.py`
- `frontend/app/components/Domain/Recipe/RecipePage/RecipePageParts/RecipePageInfoEditor.vue`
- `frontend/app/components/Domain/Recipe/RecipePage/RecipePageParts/RecipePageInfoCard.vue`
- `frontend/app/components/Domain/Recipe/RecipePrintView.vue`

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

## חילוץ מתכונים מספרים עם AI

- נוסף עיבוד AI לספרים שהועלו למערכת.
- ניתן להפעיל חילוץ מתכונים:
  - בזמן העלאת ספר, באמצעות סימון "חלץ מתכונים עם AI אחרי ההעלאה".
  - אחרי שהספר כבר עלה, מתוך פעולת "חלץ מתכונים עם AI" תחת הספר בניווט.
- ברירת המחדל היא חלוקה ל-10 עמודים בכל chunk, והמשתמש יכול לבחור מספר אחר בין 1 ל-100.
- העיבוד רץ ברקע, כדי שהדפדפן לא ייתקע בזמן עיבוד ספר ארוך.
- לכל ספר נשמר סטטוס חילוץ:
  - לא התחיל
  - בעיבוד
  - הסתיים
  - נכשל
- נשמרים גם מונים:
  - מספר chunks כולל
  - chunks שהושלמו
  - מתכונים שנמצאו
  - מתכונים שנשמרו
  - הודעת שגיאה אחרונה/חלקית
- בזמן עיבוד, רשימת הספרים מתרעננת אוטומטית כל כמה שניות ומציגה התקדמות ליד שם הספר.
- החילוץ תומך כרגע בפורמטים שניתן לחלץ מהם טקסט ישירות:
  - PDF
  - EPUB
  - TXT / Markdown
  - HTML / MHTML
  - DOCX
  - ODT
  - FB2 / FB2.ZIP
  - RTF בסיסי
- קבצי PDF עוברים חילוץ טקסט באמצעות `pypdf`.
- ה-AI מקבל כל chunk ומחזיר רשימת מתכונים במבנה מסודר, לא טקסט חופשי.
- המתכונים מתורגמים לעברית כחלק מהחילוץ.
- מתכונים שנמצאו נשמרים כמתכוני Mealie רגילים, דרך אותו מנגנון שכבר משמש ל"יצירה עם AI".
- מקור המתכון נשמר לפי שם הספר וטווח העמודים אם ה-AI לא מצא מקור מפורש.
- אם ספק ברירת המחדל הוא Google Gemini ויש בו כמה API keys, כל מפתח הופך ל-slot נפרד והעיבוד מחולק ביניהם במקביל. מספר הקריאות במקביל נקבע לפי מספר המפתחות הזמינים וכמות ה-chunks בספר, בלי cap קבוע של 6.
- אם ספק AI מחזיר rate limit / quota / retry-after, המפתח הספציפי נכנס ל-cooldown, ה-chunk חוזר לתור, והמערכת מנסה להמשיך עם מפתח אחר.
- לכל chunk נשמר סטטוס JSON במסד: ממתין, בעיבוד, retry, הושלם או נכשל, כולל מספר ניסיונות, ספק אחרון, שגיאה אחרונה וכמות מתכונים שנשמרו.
- ספר לא מסומן כ"הושלם" אם נשארו chunks שלא עברו. במקרה כזה הוא מסומן כ-`partial_failed`, ואפשר להפעיל חילוץ שוב כדי לנסות להשלים רק את החלקים שלא הושלמו.
- נוסף retry מדורג לכל chunk, עד 6 ניסיונות, עם שימוש בזמן המתנה שהספק מחזיר אם קיים.
- נוסף מנגנון מניעת כפילויות לפי שם מתכון + מקור/טווח עמודים, כדי ש-retry לא ייצור עותקים כפולים של אותו מתכון.
- אם ספק ברירת המחדל אינו Gemini, העיבוד עובד דרך ספק אחד.

קבצים מרכזיים:

- `mealie/services/uploaded_books/book_recipe_extractor.py`
- `mealie/routes/households/controller_uploaded_books.py`
- `mealie/db/models/household/uploaded_book.py`
- `mealie/schema/cookbook/uploaded_book.py`
- `mealie/schema/openai/recipe.py`
- `mealie/services/openai/prompts/recipes/extract-book-recipes.txt`
- `mealie/alembic/versions/2026-07-07-21.20.00_d4e5f6a7b8c9_add_uploaded_book_ai_extraction.py`
- `mealie/alembic/versions/2026-07-07-22.10.00_e7f8a9b0c1d2_add_uploaded_book_extraction_retries.py`
- `frontend/app/components/Layout/DefaultLayout.vue`
- `frontend/app/lib/api/user/uploaded-books.ts`
- `frontend/app/lib/api/types/uploaded-book.ts`

## תרגום ספרים עם AI

- נוסף מצב "תרגם ספר עם AI" בזמן העלאת ספר וגם מתוך פעולות ספר שכבר הועלה.
- בזמן העלאה ניתן לבחור פעולה אחת בלבד:
  - רק להעלות את הספר
  - חילוץ מתכונים עם AI
  - תרגום ספר עם AI
- לא ניתן להפעיל חילוץ מתכונים ותרגום ספר במקביל על אותו ספר.
- שפת ברירת המחדל לתרגום נקבעת לפי שפת האתר של המשתמש.
- ניתן לבחור שפה מתוך dropdown או להקליד שפה אחרת ידנית.
- גם בתרגום ספרים ניתן לבחור כמה עמודים לשלוח בכל chunk, ברירת מחדל 10 עמודים.
- מנגנון התרגום משתמש באותו retry/cooldown של חילוץ המתכונים:
  - Gemini multi-key
  - המתנה לפי retry-after/rate limit
  - retry מדורג לכל chunk
  - סטטוס לכל chunk
- כל chunk מתורגם ונשמר זמנית כקובץ JSON פנימי.
- הספר המתורגם נבנה רק אחרי שכל ה-chunks הושלמו בהצלחה.
- אם חלקים נכשלו, הספר לא מסומן כמתורגם ולא נוצר קובץ חלקי; הסטטוס יהיה `partial_failed`.
- התוצר כרגע הוא ספר HTML מתורגם ונקי, שנפתח בדפדפן מתוך Mealie.
- ספרים מתורגמים נשמרים כ-Uploaded Books רגילים עם סימון `is_translated_book`, וקישור לספר המקורי.
- נוסף סעיף ניווט מהיר "ספרים מתורגמים", שאפשר להפעיל/לכבות ולסדר ב-drag and drop כמו ספרים/קטגוריות/תגיות.
- קבצי HTML שהמשתמש מעלה עדיין מוגשים כהורדה, אבל HTML שנוצר על ידי התרגום מוגש inline כי הוא נבנה ומנוקה על ידי המערכת.

קבצים מרכזיים:

- `mealie/services/uploaded_books/book_recipe_extractor.py`
- `mealie/services/openai/prompts/recipes/translate-book-chunk.txt`
- `mealie/routes/households/controller_uploaded_books.py`
- `mealie/db/models/household/uploaded_book.py`
- `mealie/schema/cookbook/uploaded_book.py`
- `mealie/schema/openai/recipe.py`
- `mealie/alembic/versions/2026-07-08-00.20.00_f1a2b3c4d5e6_add_uploaded_book_translation.py`
- `frontend/app/components/Layout/DefaultLayout.vue`
- `frontend/app/components/Layout/LayoutParts/AppOrganizerSidebar.vue`
- `frontend/app/lib/api/user/uploaded-books.ts`
- `frontend/app/lib/api/types/uploaded-book.ts`

## שיפורי ממשק ותרגום

- נוספו מחרוזות תרגום בעברית ובאנגלית עבור:
  - יצירה מטקסט
  - העלאת וידאו
  - גודל וידאו / מדיה
  - הגדרות API וספקי AI
  - בדיקת API key
  - הודעות Gemini מרובות מפתחות
  - ניווט מהיר לספרים, קטגוריות ותגיות
- שופר צבע הטקסט של כפתור "יצירה עם AI" בתפריט הצדדי כדי שיהיה קריא.
- נוספה גישה מהירה יותר ליצירה עם AI מטקסט חופשי, בנוסף לתפריט היצירה הרגיל.
- מתחת לספרי בישול נוסף כפתור "העלאת ספר" שפותח popup להעלאת קבצי ספרים, והספרים שהועלו מופיעים בניווט המהיר כקישורים לפתיחה.
- העלאת ספרים תומכת בפורמטים רבים: PDF, EPUB, MOBI, AZW/AZW3/AZW4, FB2/FB2.ZIP, DJVU, CBZ/CBR/CB7/CBT, DOC/DOCX, ODT, TXT, RTF, HTML/MHTML, Markdown, LIT, PDB, ZIP/RAR/7Z.
- ניתן לבחור תיקייה שלמה של ספרים מהדפדפן ולהעלות את כל קבצי הספרים הנתמכים מתוכה. כאשר נבחר יותר מספר אחד, ההעלאה מתבצעת כהעלאה בלבד; חילוץ מתכונים או תרגום זמינים רק לספר יחיד בזמן העלאה או לכל ספר בנפרד אחרי שהוא כבר עלה.
- נוסף כפתור "מחק ספר" בתפריט של ספרים שהועלו. המחיקה מוחקת גם את רשומת הספר וגם את תיקיית הקובץ השמור; אם מוחקים ספר מקור שנוצרו ממנו ספרים מתורגמים, גם הספרים המתורגמים שלו נמחקים כדי לא להשאיר קישורים שבורים.
- תוקנה נפילה בהעלאת ספרים שנגרמה מיצירת רשומת `UploadedBook` בלי להעביר `session` למודל SQLAlchemy של Mealie.
- תוקן חוסר התאמה בין `id` הרשומה במסד לבין תיקיית הקובץ בפועל, כדי שלחיצה על ספר שהועלה תפתח את הקובץ ולא תחזיר `404 Not Found`.

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
- נוספו endpoints להעלאת ספרי בישול כקבצים אמיתיים ושמירתם במערכת:
  - `GET /api/households/uploaded-books`
  - `POST /api/households/uploaded-books`
  - `GET /api/households/uploaded-books/{book_id}/file`
  - `DELETE /api/households/uploaded-books/{book_id}`
  - `POST /api/households/uploaded-books/{book_id}/extract-recipes`
  - `POST /api/households/uploaded-books/{book_id}/translate`
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
- רענון סטטוס ספרים שהועלו קיבל guard נגד בקשות מקבילות, כדי ששרת איטי או בקשה תקועה לא יגרמו להצטברות polling requests כל 6 שניות.
- קאש ה-stores של ניווט ציבורי לפי קבוצות הוגבל ל-8 קבוצות אחרונות, כדי למנוע גידול לא מוגבל אם מדפדפים בין הרבה קבוצות ציבוריות.
- יצירת מתכון ב-streaming URL מבטלת את משימת הרקע אם חיבור ה-SSE נסגר לפני שהעבודה הסתיימה, כדי שלא תמשיך משימת AI/ייבוא ארוכה בלי לקוח שמאזין לה.
- חיפוש AI ב"מצא מתכון" קיבל מזהה ריצה כדי שתוצאה ישנה לא תדרוס תוצאה חדשה, ו-loading משתחרר גם אם הבקשה מסתיימת בצורה חריגה.
- טופס "יצירה עם AI" קיבל טיפול חריגות כללי כדי שלא יישאר במצב טעינה אם העלאת וידאו או ייבוא URL נכשלים באופן לא צפוי.
- בנכסי מתכון נוסף ניקוי של הגדרות גודל וידאו מ-localStorage כאשר asset וידאו נמחק.
- וידאו בעמוד המתכון משתמש ב-`preload="metadata"` ולא טוען את כל הקובץ מראש.
- לא נמצאו `ObjectURL` חדשים ללא `revokeObjectURL` בשינויים שנוספו.
- העלאות וידאו מרובות לייבוא URL נשמרות זמנית בתיקיית temp ונמחקות ב-`finally` לאחר סיום משימת הייבוא.
- העלאת ספרי בישול נשמרת בצ'אנקים של 1MB לתיקיית `DATA_DIR/uploaded-books`, כדי לא לקרוא ספרים גדולים לזיכרון בבת אחת.
- קבצים שעלולים להריץ תוכן בדפדפן, כמו HTML, מוגשים כהורדה ולא כ-inline preview.
- בתרגום ספרים ובחילוץ מתכונים מספרים, מפתח AI שמחזיר שגיאת הרשאה/מפתח לא תקין מושבת רק לאותה הרצה, והחלק שנכשל נשלח מחדש למפתח AI אחר אם קיים. רק אם לא נשאר אף מפתח שמיש החלק מסומן כנכשל.
- עבודות AI ארוכות על ספרים קיבלו מנגנון המשך אוטומטי דרך ה-scheduler: אם תרגום/חילוץ ספר נמצא ב-`processing` או `retrying` אחרי restart או אחרי המתנה ל-rate limit, המערכת תמשיך את החלקים שלא הסתיימו ותדלג על chunks שכבר הושלמו.
- לכל chunk שמחכה ל-rate limit נשמר `nextRetryAt` אמיתי, כך שהמערכת יודעת מתי לנסות שוב גם אם הדוקר או המחשב הופעלו מחדש.
- אם ספר הסתיים ב-`partial_failed` ולוחצים שוב על אותה פעולה עם אותם פרמטרים, המערכת ממשיכה את החלקים שנכשלו במקום למחוק עבודה שכבר הצליחה.
- שפת חילוץ מתכונים מספרים נשמרת במסד הנתונים, כדי שחידוש אוטומטי אחרי restart ימשיך באותה שפה שנבחרה.

## בדיקות שבוצעו

במהלך העבודה הורצו בדיקות frontend נקודתיות וגם build מלא:

- `npm exec eslint -- ...`
- `npm run build`
- `python -m py_compile ...` לקבצי backend שנגעו ב-AI/ייבוא/מתכונים
- `git diff --check`
- בדיקות JSON לקבצי תרגום
- בדיקות זמינות מקומית ל-frontend/backend (`200` ב-localhost)

ה-build עובר, אך קיימות אזהרות קיימות של הפרויקט לגבי chunk size / circular re-export / Vuetify CSS minify. האזהרות אינן קשורות ישירות לשינויים של ה-fork ולא עצרו את ה-build.
