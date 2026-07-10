import { Organizer, type RecipeOrganizer } from "~/lib/api/types/non-generated";

const suggestions = {
  en: {
    [Organizer.Category]: [
      "Breakfast", "Brunch", "Lunch", "Dinner", "Appetizers", "Soups", "Salads", "Main dishes",
      "Side dishes", "Desserts", "Baking", "Breads", "Pasta", "Rice", "Vegetarian", "Vegan",
      "Gluten free", "Quick meals", "Drinks", "Sauces", "Preserves", "Grill", "Holidays", "Kids",
      "Meal prep", "Healthy", "Seafood", "Meat", "Poultry",
    ],
    [Organizer.Tag]: [
      "Easy", "Intermediate", "Advanced", "Quick", "Budget", "Seasonal", "Summer", "Winter", "Spicy",
      "Sweet", "Savory", "Comfort food", "Michelin", "Restaurant", "Chef", "Family", "Entertaining",
      "Freezer friendly", "One pot", "No bake", "Low carb", "High protein", "Dairy free", "Kosher",
      "Italian", "French", "Greek", "Asian", "Middle Eastern", "Mediterranean",
    ],
    [Organizer.Tool]: [
      "Chef knife", "Cutting board", "Frying pan", "Pot", "Saucepan", "Oven", "Mixer", "Food processor",
      "Blender", "Kitchen scale", "Measuring cups", "Measuring spoons", "Whisk", "Spatula", "Wooden spoon",
      "Peeler", "Grater", "Colander", "Baking sheet", "Baking dish", "Kitchen thermometer", "Rolling pin",
      "Piping bag", "Pasta machine", "Grill", "Pressure cooker", "Slow cooker", "Air fryer",
      "Mortar and pestle", "Mandoline",
    ],
  },
  he: {
    [Organizer.Category]: [
      "ארוחת בוקר", "בראנץ'", "ארוחת צהריים", "ארוחת ערב", "מנות פתיחה", "מרקים", "סלטים", "מנות עיקריות",
      "תוספות", "קינוחים", "אפייה", "לחמים", "פסטה", "אורז", "צמחוני", "טבעוני", "ללא גלוטן",
      "ארוחות מהירות", "משקאות", "רטבים", "שימורים וכבושים", "גריל", "חגים", "ילדים", "הכנה מראש",
      "בריא", "דגים ופירות ים", "בשר", "עוף",
    ],
    [Organizer.Tag]: [
      "קל", "בינוני", "מתקדם", "מהיר", "חסכוני", "עונתי", "קיץ", "חורף", "חריף", "מתוק", "מלוח",
      "אוכל מנחם", "מישלן", "מסעדה", "שף", "משפחתי", "אירוח", "מתאים להקפאה", "סיר אחד", "ללא אפייה",
      "דל פחמימות", "עשיר בחלבון", "ללא חלב", "כשר", "איטלקי", "צרפתי", "יווני", "אסייתי", "מזרח תיכוני",
      "ים תיכוני",
    ],
    [Organizer.Tool]: [
      "סכין שף", "קרש חיתוך", "מחבת", "סיר", "קלחת", "תנור", "מיקסר", "מעבד מזון", "בלנדר",
      "משקל מטבח", "כוסות מדידה", "כפות מדידה", "מטרפה", "מרית", "כף עץ", "קולפן", "פומפייה", "מסננת",
      "תבנית אפייה", "כלי אפייה", "מדחום מטבח", "מערוך", "שקית זילוף", "מכונת פסטה", "גריל", "סיר לחץ",
      "סיר בישול איטי", "אייר פרייר", "מכתש ועלי", "מנדולינה",
    ],
  },
} as const;

export interface OrganizerSuggestion {
  name: string;
  __presetSuggestion: true;
}

export function organizerSuggestions(type: RecipeOrganizer, locale: string): OrganizerSuggestion[] {
  const language = locale.toLowerCase().startsWith("he") ? "he" : "en";
  const languageSuggestions = suggestions[language] as Partial<Record<RecipeOrganizer, readonly string[]>>;
  const values = languageSuggestions[type] || [];
  return values.map(name => ({ name, __presetSuggestion: true }));
}
