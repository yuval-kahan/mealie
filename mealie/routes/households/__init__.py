from fastapi import APIRouter

from . import (
    controller_articles,
    controller_chefs,
    controller_cookbooks,
    controller_equipment,
    controller_group_notifications,
    controller_group_recipe_actions,
    controller_household_self_service,
    controller_invitations,
    controller_linked_resources,
    controller_mealplan,
    controller_mealplan_rules,
    controller_notebooks,
    controller_pantry_items,
    controller_product_knowledge,
    controller_restaurants,
    controller_shopping_lists,
    controller_shopping_websites,
    controller_uploaded_books,
    controller_videos,
    controller_wanted_books,
    controller_webhooks,
)

router = APIRouter()

router.include_router(controller_articles.router)
router.include_router(controller_chefs.router)
router.include_router(controller_cookbooks.router)
router.include_router(controller_group_notifications.router)
router.include_router(controller_group_recipe_actions.router)
router.include_router(controller_equipment.router)
router.include_router(controller_household_self_service.router)
router.include_router(controller_invitations.router)
router.include_router(controller_linked_resources.router)
router.include_router(controller_notebooks.router)
router.include_router(controller_pantry_items.router)
router.include_router(controller_product_knowledge.router)
router.include_router(controller_restaurants.router)
router.include_router(controller_shopping_lists.router)
router.include_router(controller_shopping_lists.item_router)
router.include_router(controller_shopping_websites.router)
router.include_router(controller_uploaded_books.router)
router.include_router(controller_videos.router)
router.include_router(controller_wanted_books.router)
router.include_router(controller_webhooks.router)

# mealplan_rules must be added before mealplan due to the way the routes are defined
router.include_router(controller_mealplan_rules.router)
router.include_router(controller_mealplan.router)
