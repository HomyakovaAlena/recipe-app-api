"""
Test ingredients API.
"""
from decimal import Decimal

from core.models import Ingredient, Recipe
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from recipe.serializers import IngredientSerializer
from rest_framework import status
from rest_framework.test import APIClient

INGREDIENTS_URL = reverse('recipe:ingredient-list')


def create_user(email='testuser@example.com', password='testpassword'):
    """Create and return a new user."""
    return get_user_model().objects.create_user(email, password)


def detail_url(ingredient_id):
    """Create and return ingredient detail url."""
    return reverse('recipe:ingredient-detail', args=(ingredient_id,))


class PublicIngredientsApiTests(TestCase):
    """Tests unauthenticated Ingredient API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving ingredients."""
        res = self.client.get(INGREDIENTS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Tests authenticated Ingredients API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """Test retrievings a list of ingredients."""
        Ingredient.objects.create(user=self.user, name='Ingredient1')
        Ingredient.objects.create(user=self.user, name='Ingredient2')

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test ingredients list limited to authenticated user."""
        user2 = create_user(email='user2test@example.com')
        Ingredient.objects.create(user=user2, name='Fruity')

        ingredient = Ingredient.objects.create(user=self.user, name='Vanilla')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        """Test updating an ingredient."""
        ingredient = Ingredient.objects.create(user=self.user, name='Banana')

        payload = {'name': 'Cucumber'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()

        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        """Test deleting ingredient."""
        ingredient = Ingredient.objects.create(user=self.user, name='Banana')
        url = detail_url(ingredient.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        """Test listing ingredients by those assigned to recipes."""
        in1 = Ingredient.objects.create(user=self.user, name='apple')
        in2 = Ingredient.objects.create(user=self.user, name='turkey')
        rec1 = Recipe.objects.create(
            title='Turkey with apples',
            time_minutes=32,
            price=Decimal('2.4'),
            user=self.user
        )
        rec1.ingredients.add(in1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_ingredients_unique(self):
        """Test filtered ingredients return unique list."""
        ing = Ingredient.objects.create(
            user=self.user,
            name='eggs'
        )
        Ingredient.objects.create(
            user=self.user,
            name='tomato'
        )
        rec1 = Recipe.objects.create(
            title='Eggs Benedict',
            time_minutes=32,
            price=Decimal('2.4'),
            user=self.user
        )
        rec2 = Recipe.objects.create(
            title='Eggs in herbs',
            time_minutes=32,
            price=Decimal('2.4'),
            user=self.user
        )
        rec1.ingredients.add(ing)
        rec2.ingredients.add(ing)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
