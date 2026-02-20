from django.conf import settings
from django.conf.urls.static import static
from django.db import router
from django.urls import include, path
from rest_framework import routers

from . import views
from .views import (
    CookieTokenRefreshView,
    FoodListViewSet,
    FoodTagsViewSet,
    FoodViewSet,
    ForgotPassword,
    GetCSRFToken,
    ImageFoodViewSet,
    IngredientsViewSet,
    IngredientViewSet,
    RecipeEmailSubmit,
    RegisterNewAccount,
    ResetPassword,
    StepsViewSet,
    TagGroupViewSet,
    UnitViewSet,
    UrlViewSet,
    UserLogoutView,
    UsersView,
    UsersViewSet,
)

router = routers.DefaultRouter()  # noqa: F811
(router.register("foods", FoodViewSet),)
router.register("foodsList", FoodListViewSet, basename="foodsList")
router.register("foodTags", FoodTagsViewSet)
router.register("tagGroups", TagGroupViewSet)
router.register("steps", StepsViewSet)
router.register("url", UrlViewSet)
router.register("ingredients", IngredientsViewSet)
router.register("ingredient", IngredientViewSet)
router.register("unit", UnitViewSet)
router.register("imagefood", ImageFoodViewSet)
router.register("users", UsersViewSet)


urlpatterns = [
    path("", include(router.urls)),
    path("register", RegisterNewAccount.as_view(), name="register"),
    path("login", views.loginView),
    path("logout", UserLogoutView.as_view(), name="logout"),
    path("api/token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("forgot-password/", ForgotPassword.as_view(), name="forgot-password"),
    path("reset-password/", ResetPassword.as_view(), name="reset-password"),
    path("userslist/", UsersView.as_view(), name="users"),
    path("csrf_cookie/", GetCSRFToken.as_view()),
    path("recipesubmit/", RecipeEmailSubmit.as_view(), name="recipesubmit"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
