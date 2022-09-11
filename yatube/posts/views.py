from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect

from .forms import PostForm, CommentForm
from .models import Group, Post, Follow
from .common import paginator

User = get_user_model()

NUM_OF_POSTS: int = 10


def index(request):
    """Отображает главную страницу."""
    template = 'posts/index.html'
    posts = Post.objects.select_related('author').all()
    page_obj = paginator(posts, NUM_OF_POSTS, request)
    context = {'page_obj': page_obj}
    return render(request, template, context)


def group_posts(request, slug):
    """Отображает страницу группы."""
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('author').all()
    page_obj = paginator(posts, NUM_OF_POSTS, request)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    """Страница профиля."""
    template = 'posts/profile.html'
    author = get_object_or_404(User, username=username)
    following = True
    if request.user.is_authenticated:
        if author.following.filter(user=request.user).exists():
            following = True
        else:
            following = False
        posts = author.posts.all()
        page_obj = paginator(posts, NUM_OF_POSTS, request)
        context = {
            'page_obj': page_obj,
            'author': author,
            'following': following
        }
        return render(request, template, context)
    else:
        posts = author.posts.all()
        page_obj = paginator(posts, NUM_OF_POSTS, request)
        context = {
            'page_obj': page_obj,
            'author': author,
            'following': following
        }
        return render(request, template, context)


def post_detail(request, post_id):
    """Страница поста."""
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, pk=post_id)
    comments = post.comments.all()
    form = CommentForm()
    if request.method == 'POST':
        if form.is_valid():
            form = form.save(commit=False)
            form.author = request.user
            form.post = post
            form.save()
        return redirect('posts:post_detail', post_id=post_id)
    context = {
        'post': post,
        'comments': comments,
        'form': form
    }
    return render(request, template, context)


@login_required
def post_create(request):
    """Создание поста."""
    template = 'posts/create_post.html'
    username = request.user.username
    form = PostForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('posts:profile', username)
        return render(request, template, {'form': form})
    context = {'form': form}
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    """Редактирование поста."""
    template = 'posts/create_post.html'
    user = request.user
    post = get_object_or_404(Post, pk=post_id)
    if user != post.author:
        return redirect('posts:post_detail', post_id)
    is_edit = True
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post)
    if form.is_valid():
        post.save()
        return redirect('posts:post_detail', post_id)
    return render(request, template, {
        'form': form,
        'is_edit': is_edit,
        'post_id': post_id})


@login_required
def add_comment(request, post_id):
    """Создание комментария."""
    form = CommentForm(request.POST or None)
    post = get_object_or_404(Post, pk=post_id)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    page_obj = paginator(posts, NUM_OF_POSTS, request)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    follows = author.following.all()
    if follows.filter(user=request.user).exists():
        return redirect('posts:follow_index')
    if author != request.user:
        Follow.objects.create(
            user=request.user,
            author=author
        )
    return redirect('posts:follow_index')


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(author=author, user=request.user).delete()
    return redirect('posts:follow_index')
