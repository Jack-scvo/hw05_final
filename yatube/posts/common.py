from django.core.paginator import Paginator


def paginator(posts, num_of_posts, request):
    """Функция пагинатор."""
    paginator = Paginator(posts, num_of_posts)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
