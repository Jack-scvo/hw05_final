from django.test import TestCase


class ContextTest(TestCase):
    def context_test(self, *, response, post):
        first_object = response.context['page_obj'][0]
        post_text = first_object.text
        post_author = first_object.author
        post_group = first_object.group
        result_1 = self.assertEqual(
            post_text, post.text,
            'Текст поста не соответствует ожидаемому')
        result_2 = self.assertEqual(
            post_author, post.author,
            'Автор поста не соответствует ожидаемому')
        result_3 = self.assertEqual(
            post_group, post.group,
            'Группа поста не соответствует ожидаемой')
        return result_1, result_2, result_3
