from django.test import TestCase


class PaginatorTest(TestCase):
    def paginator_test(self, *, path, client):
        response = client.get(path)
        result_1 = self.assertEqual(len(
            response.context['page_obj']), 10,
            'На первой странице не 10 записей')
        response = client.get(path + '?page=2')
        result_2 = self.assertEqual(len(
            response.context['page_obj']), 5,
            'На второй странице не 5 записей')
        return result_1, result_2
