from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Group(models.Model):
    """Модель, хранящая данные о группе."""
    title = models.CharField('Название группы', max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField('Описание группы')

    def __str__(self) -> str:
        return f'<Group {self.title}>'


class Post(models.Model):
    """Модель, хранящая данные о постах."""
    text = models.TextField(verbose_name='Текст поста',
                            help_text='Введите текст поста')
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Автор'
    )
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL,
        blank=True, null=True, related_name='posts',
        verbose_name='Группа',
        help_text='Группа, к которой будет относиться пост'
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        ordering = ['-pub_date']
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self) -> str:
        return f'<Post {self.text[:15]}>'


class Comment(models.Model):
    """Хранит данные о комментариях."""
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Пост, к которому относится комменнтарий'
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор поста'
    )
    text = models.TextField(verbose_name='Текст комментария',
                            help_text='Введите текст комментария')
    created = models.DateTimeField(
        'Дата публикации комментария',
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Комментарий'

    def __str__(self) -> str:
        return f'<Comment {self.text[:15]}>'


class Follow(models.Model):
    """Хранит данные о подписках."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Юзер, который подписывается'
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор, на которого подписываются'
    )

    class Meta:
        verbose_name = 'Подписки'
