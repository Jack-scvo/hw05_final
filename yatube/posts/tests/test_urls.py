from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from ..models import Post, Group

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group
        )

    def setUp(self):
        self.guest_client = Client()
        self.unauth_user = User.objects.create_user(username='NoName')
        self.author_client = Client()
        self.author_client.force_login(self.user)
        self.auth_client = Client()
        self.auth_client.force_login(self.unauth_user)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.pk}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{self.post.pk}/edit/': 'posts/create_post.html'
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.author_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_unauthorized_user(self):
        """Доступ к страницам неавторизованного пользователя."""
        url_names_codes = {
            '/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.user.username}/': HTTPStatus.FOUND,
            f'/posts/{self.post.pk}/': HTTPStatus.OK,
            '/create/': HTTPStatus.FOUND,
            f'/posts/{self.post.pk}/edit/': HTTPStatus.FOUND
        }
        for address, code in url_names_codes.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, code)

    def test_authorized_user(self):
        """Доступ к страницам авторизованного пользователя(не автора)."""
        url_names_codes = {
            '/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.unauth_user.username}/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/': HTTPStatus.OK,
            '/create/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/edit/': HTTPStatus.FOUND
        }
        for address, code in url_names_codes.items():
            with self.subTest(address=address):
                response = self.auth_client.get(address)
                self.assertEqual(response.status_code, code)

    def test_unexisting_page_url(self):
        """Запрос к несуществующей странице вернёт ошибку 404."""
        address = '/unexisting_page/'
        response = self.auth_client.get(address)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_unexisted_page_template(self):
        """Запрос к несуществующей странице возвращает кастомный шаблон."""
        address = '/unexisting_page/'
        response = self.auth_client.get(address)
        self.assertTemplateUsed(response, 'core/404.html')
