import shutil
import tempfile

from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Post, Group

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostCreateFormTests(TestCase):
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
        cls.group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug_2',
            description='Тестовое описание 2'
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_new_post_created(self):
        """Тест формы создания поста"""
        form_data = {
            'text': 'Тестовый пост',
            'group': self.group.pk
        }
        posts_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_create'), data=form_data,
            follow=True)
        self.assertEqual(Post.objects.count(),
                         posts_count + 1, 'Пост не создался')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        post = Post.objects.get(pk=2)
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group.pk, form_data['group'])

    def test_edit_post(self):
        """Тест формы редактирования поста"""
        form_data = {
            'text': 'Отредактированный пост',
            'group': self.group_2.pk,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data, follow=True
        )
        self.assertEqual(Post.objects.get(pk=1).text,
                         form_data['text'], 'Поле текст поста не изменилось')
        self.assertEqual(
            Post.objects.get(pk=1).group.pk,
            form_data['group'], 'Поле группа поста не изменилось')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        posts = response.context['page_obj']
        for post in posts:
            with self.subTest(post=post):
                self.assertNotEqual(1, post.pk,
                                    'Пост остался на странице первой группы')


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostImageFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post_with_image(self):
        """Проверяем создание поста с картинкой."""
        posts_count = Post.objects.count()
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
        form_data = {
            'text': 'Тестовый пост с картинкой',
            'author': self.user,
            'image': uploaded
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)


class CommentTests(TestCase):
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
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_comment_appearance(self):
        """Комментарий появляется на странице поста."""
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data={'text': 'Тестовый комментарий'},
            follow=True
        )
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertIsNotNone(
            response.context['comments'][0],
            'Комментарий не появился на странице поста'
        )

    def test_unauth_user(self):
        """Неавторизованный пользователь не может комментировать."""
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data={'text': 'Тестовый комментарий'},
            follow=True
        )
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(
            len(response.context['comments']), 0,
            ('Комментарий от незарегистрированного пользователя'
             ' появился на странице поста')
        )
