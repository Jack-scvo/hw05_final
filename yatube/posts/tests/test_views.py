import shutil
import tempfile
import time

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from . import paginator_test, context_test
from ..models import Post, Group, Follow

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug_2',
            description='Тестовое описание 2'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_page_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
            'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.user.username}):
            'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}):
            'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}):
            'posts/create_post.html'
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_main_page_context(self):
        """Тестируем контекст главной страницы."""
        response = self.authorized_client.get(reverse('posts:index'))
        context_test.ContextTest().context_test(response=response,
                                                post=self.post)

    def test_create_post_page_context(self):
        """Тестируем контекст страницы создания поста."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(
                    form_field, expected,
                    'Поле формы не соответствует ожидаемому')

    def test_group_list_page_context(self):
        """Тестируем контекст страницы группы."""
        response = self.authorized_client.get(reverse(
            'posts:group_list',
            kwargs={'slug': self.group.slug}))
        context_test.ContextTest().context_test(response=response,
                                                post=self.post)

    def test_profile_page_context(self):
        """Тестируем контекст страницы профиля."""
        response = self.authorized_client.get(reverse(
            'posts:profile',
            kwargs={'username': self.user.username}))
        context_test.ContextTest().context_test(response=response,
                                                post=self.post)

    def test_post_detail_page_context(self):
        """Тестируем контекст страницы поста."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}))
        post_object = response.context['post']
        self.assertEqual(
            post_object.text, self.post.text,
            'Текст поста не соответствует ожидаемому')
        self.assertEqual(
            post_object.author, self.post.author,
            'Автор поста не соответствует ожидаемому')
        self.assertEqual(
            post_object.group, self.post.group,
            'Группа поста не соответствует ожидаемой')

    def test_edit_post_page_context(self):
        """Тестируем контекст страницы редактирования поста."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(
                    form_field, expected,
                    'Поле формы не соответствует ожидаемому')
        post_id = response.context['post_id']
        self.assertEqual(post_id, self.post.pk,
                         'Редактируем не тот пост')

    def test_created_post_appearance(self):
        """Тестируем появление созданного поста."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.pk, self.post.pk,
                         'Нового поста нет на главной странице')
        response = self.authorized_client.get(reverse(
            'posts:profile',
            kwargs={'username': self.user.username}))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.pk, self.post.pk,
                         'Нового поста нет на странице профиля')
        response = self.authorized_client.get(reverse(
            'posts:group_list',
            kwargs={'slug': self.group.slug}))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.pk, self.post.pk,
                         'Нового поста нет на странице группы')
        response = self.authorized_client.get(reverse(
            'posts:group_list',
            kwargs={'slug': self.group_2.slug}))
        post_2 = Post.objects.create(
            text='Тестовый текст 2',
            author=self.user,
            group=self.group_2
        )
        for post_object in response.context['page_obj']:
            self.assertNotEqual(post_object.pk, self.post.pk,
                                'Новый пост на странице другой группы')
        post_2.delete()


class PaginatorTestViews(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.posts = []
        for i in range(15):
            cls.posts.append(Post(
                text=i,
                author=cls.user,
                group=cls.group
            ))
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_paginator_main_page(self):
        """Тест пагинатора на главной странице."""
        path = reverse('posts:index')
        paginator_test.PaginatorTest().paginator_test(path=path,
                                                      client=self.client)

    def test_paginator_group_page(self):
        """Тест пагинатора на странице группы."""
        path = reverse('posts:group_list', kwargs={'slug': self.group.slug})
        paginator_test.PaginatorTest().paginator_test(path=path,
                                                      client=self.client)

    def test_paginator_profile_page(self):
        """Тест пагинатора на странице профиля."""
        path = reverse('posts:profile',
                       kwargs={'username': self.user.username})
        paginator_test.PaginatorTest().paginator_test(path=path,
                                                      client=self.client)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesImagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_image_in_post_context(self):
        """Картинка передается в контексте страниц."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        post = Post.objects.create(
            text='Тестовый текст поста с картинкой',
            author=self.user,
            group=self.group,
            image=uploaded
        )
        pages_names = {
            reverse('posts:index'): 'index',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
            'group_list',
            reverse('posts:profile',
                    kwargs={'username': self.user.username}):
            'profile'
        }
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': post.pk}))
        self.assertIsNotNone(response.context.get('post').image,
                             'Картинка не загрузилась на странице post_detail')
        for page, page_name in pages_names.items():
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertIsNotNone(
                    response.context['page_obj'][0].image,
                    f'Картинка не загрузилась на странице {page_name}')


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_cache_index_page(self):
        """Созданный пост не появляется на главной странице 20 с."""
        form_data = {
            'text': 'Текст',
            'group': self.group.pk
        }
        self.authorized_client.get(reverse('posts:index'))
        res_0 = cache.get(make_template_fragment_key('index_page', [1]))
        self.authorized_client.post(reverse('posts:post_create'),
                                    data=form_data, follow=True)
        time.sleep(5)
        res = cache.get(make_template_fragment_key('index_page', [1]))
        time.sleep(20)
        self.authorized_client.get(reverse('posts:index'))
        res_1 = cache.get(make_template_fragment_key('index_page', [1]))
        self.assertEqual(res_0, res, 'Пост появился раньше 20 с')
        self.assertNotEqual(res_0, res_1, 'Пост не появился через 20 с')


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_1 = User.objects.create_user(username='auth_1')
        cls.user_2 = User.objects.create_user(username='auth_2')
        cls.guest = User.objects.create_user(username='unauth')

    def setUp(self):
        self.authorized_client_1 = Client()
        self.authorized_client_1.force_login(self.user_1)
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(self.user_2)
        self.guest_client = Client()

    def test_auth_user_following(self):
        """Авторизованый юзер может подписаться и
        отписаться от другого авторизованного юзера."""
        count = Follow.objects.count()
        self.authorized_client_1.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user_2.username})
        )
        self.assertEqual(Follow.objects.count(), count + 1,
                         'Подписка не создана')
        self.authorized_client_1.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.user_2.username})
        )
        self.assertEqual(Follow.objects.count(), count,
                         'Подписка не удалена')
        self.guest_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user_2.username})
        )
        self.assertEqual(Follow.objects.count(), count,
                         'Неавторизованный юзер смог подписаться')

    def test_new_post_in_timeline(self):
        """Новая запись в ленте."""
        user = User.objects.create_user(username='author')
        authorized_client = Client()
        authorized_client.force_login(user)
        post = Post.objects.create(
            text='Тестовый текст',
            author=user,
        )
        self.authorized_client_1.get(
            reverse('posts:profile_follow',
                    kwargs={'username': user.username})
        )
        response = self.authorized_client_1.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(response.context['page_obj'][0].pk, post.pk,
                         'Пост не появился в ленте подписанного юзера')
        response = self.authorized_client_2.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(len(response.context['page_obj']), 0,
                         'Пост появился в ленте неподписанного юзера')
