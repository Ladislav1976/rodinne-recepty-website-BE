from django.db import transaction
from rest_framework import serializers, validators

from FilkaRecepty.models import (
    CustomUser,
    Foods,
    FoodTags,
    ImageFood,
    Ingredient,
    Ingredients,
    Steps,
    TagGroups,
    Unit,
    Url,
)


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(required=False, allow_null=True)
    foods_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "upload_folder",
            "avatar",
            "is_superuser",
            "foods_count",
        )
        read_only_fields = [
            "id",
            "email",
            "is_staff",
            "is_superuser",
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.avatar:
            ret["avatar"] = f"http://127.0.0.1:8000{instance.avatar.url}"
            # ret["avatar"] = f"http://0.0.0.0:8000{instance.avatar.url}"
        else:
            ret["avatar"] = None
        return ret

    def get_avatar(self, obj):
        if obj.avatar and hasattr(obj.avatar, "url"):
            request = self.context.get("request")
            if request is not None:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

    def get_foods_count(self, obj):
        if hasattr(obj, "foods_count"):
            return obj.foods_count

        return obj.foods.count()


class UsersSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(required=False, allow_null=True)
    foods_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "upload_folder",
            "avatar",
            "is_superuser",
            "is_active",
            "foods_count",
        )
        read_only_fields = ["id", "email", "is_staff", "is_superuser"]

    def get_foods_count(self, obj):
        if hasattr(obj, "foods_count"):
            return obj.foods_count

        return obj.foods.count()


class FoodTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodTags
        unique_together = ("foodTag", "group")
        fields = ["id", "foodTag", "group"]

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = {"foodTag": data}

        return super().to_internal_value(data)

    def validate(self, data):
        name = data.get("foodTag")
        group = data.get("group")

        if not group:
            return data

        exists = FoodTags.objects.filter(foodTag__iexact=name, group=group).exists()

        if exists:
            raise serializers.ValidationError("Tento tag už v tejto skupine existuje.")

        return data


class TagGroupSerializer(serializers.ModelSerializer):
    tags = FoodTagSerializer(source="food_tags", many=True, read_only=True)

    class Meta:
        model = TagGroups

        fields = ["id", "groupName", "tags"]
        extra_kwargs = {
            "groupName": {
                "validators": [
                    validators.UniqueValidator(
                        queryset=TagGroups.objects.all(),
                        message="Skupina s týmto názvom už existuje.",
                    )
                ]
            }
        }


class StepSerializer(serializers.ModelSerializer):
    position = serializers.IntegerField()

    class Meta:
        model = Steps
        fields = ["id", "step", "position"]


class UrlSerializer(serializers.ModelSerializer):
    class Meta:
        model = Url
        fields = ["id", "url", "urlname"]


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ["id", "unit"]


class ImageFoodSerializer(serializers.ModelSerializer):
    position = serializers.IntegerField()

    class Meta:
        model = ImageFood
        fields = "__all__"


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = "__all__"


class IngredientsSerializer(serializers.ModelSerializer):
    units = serializers.PrimaryKeyRelatedField(many=True, queryset=Unit.objects.all())
    ingredientName = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    quantity = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        coerce_to_string=False,
    )
    position = serializers.IntegerField()

    class Meta:
        model = Ingredients
        fields = [
            "id",
            "quantity",
            "position",
            "units",
            "ingredientName",
        ]

        extra_kwargs = {
            "quantity": {"required": True, "allow_blank": False},
            "position": {"required": True},
        }

    def get_ingredient_details(self, obj):
        ingredients = obj.ingredientName.all()
        return IngredientSerializer(ingredients, many=True).data

    def validate_ingredientName(self, value):
        if not value or len(value) == 0:
            raise serializers.ValidationError(
                "Ingrediencia musí mať aspoň jeden názov."
            )
        return value

    def validate_units(self, value):
        if not value or len(value) == 0:
            raise serializers.ValidationError("Musíte vybrať aspoň jednu jednotku.")
        return value

    def to_internal_value(self, data):
        ingredient_strings = data.get("ingredientName", [])

        if not ingredient_strings:
            raise serializers.ValidationError(
                {"ingredientName": "Tento kľúč je povinný."}
            )

        data_for_validation = data.copy()

        if "ingredientName" in data_for_validation:
            data_for_validation.pop("ingredientName")

        validated_data = super().to_internal_value(data_for_validation)

        ingredient_objs = []
        for name in ingredient_strings:
            clean_name = name.strip()
            if clean_name:
                obj, _ = Ingredient.objects.get_or_create(ingredient=clean_name)
                ingredient_objs.append(obj)

        validated_data["ingredientName"] = ingredient_objs

        return validated_data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["units"] = UnitSerializer(instance.units.all(), many=True).data
        ret["ingredientName"] = IngredientSerializer(
            instance.ingredientName.all(), many=True
        ).data
        return ret


class FoodSerializer(serializers.ModelSerializer):
    ingredients = IngredientsSerializer(many=True)
    steps = StepSerializer(many=True)
    urls = UrlSerializer(many=True, required=False)
    user_details = UserSerializer(source="user", read_only=True)
    images = ImageFoodSerializer(many=True, read_only=True)
    foodTags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=FoodTags.objects.all()
    )

    class Meta:
        model = Foods
        fields = [
            "id",
            "name",
            "date",
            "foodTags",
            "user",
            "user_details",
            "ingredients",
            "steps",
            "urls",
            "images",
        ]
        extra_kwargs = {"user": {"write_only": True}}

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["foodTags"] = FoodTagSerializer(instance.foodTags.all(), many=True).data
        return ret

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop("ingredients", [])
        steps_data = validated_data.pop("steps", [])
        urls_data = validated_data.pop("urls", [])
        tags_data = validated_data.pop("foodTags", [])

        self._validate_required_fields(ingredients_data, steps_data, tags_data)

        food = Foods.objects.create(**validated_data)
        food.foodTags.set(tags_data)

        self._save_related_data(food, ingredients_data, steps_data, urls_data)

        return food

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop("ingredients", None)
        steps_data = validated_data.pop("steps", None)
        tags_data = validated_data.pop("foodTags", None)
        urls_data = validated_data.pop("urls", None)

        self._validate_required_fields(ingredients_data, steps_data, tags_data)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tags_data is not None:
            instance.foodTags.set(tags_data)

        if steps_data is not None:
            instance.steps.all().delete()
            self._save_related_data(instance, steps_data=steps_data)

        if urls_data is not None:
            instance.urls.all().delete()

            self._save_related_data(instance, urls_data=urls_data)

        if ingredients_data is not None:
            instance.ingredients.all().delete()

            self._save_related_data(instance, ingredients_data=ingredients_data)

        return Foods.objects.prefetch_related(
            "ingredients__units", "ingredients__ingredientName", "foodTags", "steps"
        ).get(pk=instance.pk)

    def _validate_required_fields(self, ingredients, steps, tags):
        errors = {}
        if ingredients is not None and len(ingredients) == 0:
            errors["ingredients"] = "Recept musí obsahovať aspoň jednu ingredienciu."
        if steps is not None and len(steps) == 0:
            errors["steps"] = "Postup nemôže byť prázdny."
        if tags is not None and len(tags) == 0:
            errors["foodTags"] = "Musíte vybrať aspoň jeden tag."
        if errors:
            raise serializers.ValidationError(errors)

    def _save_related_data(
        self, food_instance, ingredients_data=None, steps_data=None, urls_data=None
    ):
        if steps_data:
            for step in steps_data:
                Steps.objects.create(food=food_instance, **step)

        if urls_data:
            for url in urls_data:
                Url.objects.create(food=food_instance, **url)

        if ingredients_data:
            for ing in ingredients_data:
                unit_objs = ing.pop("units", [])

                names_objs = ing.pop("ingredientName", [])

                ing_obj = Ingredients.objects.create(food=food_instance, **ing)

                if unit_objs:
                    ing_obj.units.set(unit_objs)

                if names_objs:
                    ing_obj.ingredientName.set(names_objs)


class FoodListSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    foodTags = FoodTagSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = Foods
        fields = ["id", "name", "date", "foodTags", "user", "thumbnail_url"]

    def get_thumbnail_url(self, obj):
        first_image = obj.images.all().first()
        if first_image and first_image.thumbnail:
            url = first_image.thumbnail.url
            request = self.context.get("request")

            if url.startswith("http"):
                return url

            if request is not None:
                return request.build_absolute_uri(url)

            return f"http://127.0.0.1:8000{url}"
            # return f"http://0.0.0.0:8000{url}"
        return None


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={"input_type": "password"}, write_only=True)
