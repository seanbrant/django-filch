from django.contrib.contenttypes.models import ContentType
from django.test import TestCase


from filch.tests.models import Group, Location, Person
from filch.tests.models import Article, HomepageItem, Press, Slot


class DenormManyToManyFieldTestCase(TestCase):

    def setUp(self):
        self.person = Person.objects.create(name='Sean')
        self.location = Location.objects.create(name='Chicago')
        self.group1 = Group.objects.create(
            name='PyChi',
            location=self.location,
        )
        self.group2 = Group.objects.create(
            name='WhiteSoxsFan',
            location=self.location,
        )

    def test_many_to_many_change(self):
        self.assertEquals(self.person.group_list, [])

        self.person.groups.add(self.group1)
        self.assertEquals(self.person.group_list,
            [
                {'location': {'name': 'Chicago'}, 'name': 'PyChi'},
            ])

        self.person.groups.add(self.group2)
        self.assertEquals(self.person.group_list,
            [
                {'location': {'name': 'Chicago'}, 'name': 'PyChi'},
                {'location': {'name': 'Chicago'}, 'name': 'WhiteSoxsFan'},
            ])

        self.person.groups.remove(self.group1)
        self.assertEquals(self.person.group_list,
            [
                {'location': {'name': 'Chicago'}, 'name': 'WhiteSoxsFan'},
            ])

        self.person.groups.clear()
        self.assertEquals(self.person.group_list, [])

    def test_related_instance_update(self):
        self.person.groups.add(self.group1)
        self.assertEquals(self.person.group_list,
            [
                {'location': {'name': 'Chicago'}, 'name': 'PyChi'},
            ])

        self.group1.name = 'Djangonauts'
        self.group1.save()
        self.assertEquals(self.person.group_list,
            [
                {'location': {'name': 'Chicago'}, 'name': 'Djangonauts'},
            ])

        self.group1.delete()
        self.assertEquals(self.person.group_list, [])


class GenericResolutionManagerTestCase(TestCase):

    def setUp(self):
        self.article1 = Article.objects.create(
            name='Django 1.2 released!',
        )
        self.article2 = Article.objects.create(
            name='Filch is a real query saver',
        )
        self.article3 = Article.objects.create(
            name='Unpublished!',
            is_published=False,
        )
        self.press1 = Press.objects.create(
            name='Django taking the world by storm',
        )
        self.slot1 = Slot.objects.create(
            name='main',
        )
        self.slot2 = Slot.objects.create(
            name='sidebar',
        )
        self.main_items1 = HomepageItem.objects.create(
            slot=self.slot1,
            content_type=ContentType.objects.get_for_model(self.article1),
            object_id=self.article1.id,
            order=1,
        )
        self.main_items2 = HomepageItem.objects.create(
            slot=self.slot1,
            content_type=ContentType.objects.get_for_model(self.press1),
            object_id=self.press1.id,
            order=2,
        )
        self.main_items3 = HomepageItem.objects.create(
            slot=self.slot1,
            content_type=ContentType.objects.get_for_model(self.article2),
            object_id=self.article2.id,
            order=3,
        )
        self.main_items4 = HomepageItem.objects.create(
            slot=self.slot1,
            content_type=ContentType.objects.get_for_model(self.article1),
            object_id=self.article1.id,
            order=4,
        )
        self.main_items5 = HomepageItem.objects.create(
            slot=self.slot1,
            content_type=ContentType.objects.get_for_model(self.article3),
            object_id=self.article3.id,
            order=5,
        )
        self.sidebar_items1 = HomepageItem.objects.create(
            slot=self.slot2,
            content_type=ContentType.objects.get_for_model(self.article1),
            object_id=self.article1.id,
            order=1,
        )
        self.sidebar_items2 = HomepageItem.objects.create(
            slot=self.slot2,
            content_type=ContentType.objects.get_for_model(self.press1),
            object_id=self.press1.id,
            order=2,
        )
        self.sidebar_items3 = HomepageItem.objects.create(
            slot=self.slot2,
            content_type=ContentType.objects.get_for_model(self.article2),
            object_id=self.article2.id,
            order=3,
        )

    def test_get_content_objects(self):
        items = HomepageItem.objects \
            .filter(slot=self.slot1).get_content_objects()
        self.assertEquals(len(items), 5)
        # make sure ordering is working :)
        self.assertEquals(items[1], self.press1)

    def test_get_content_objects_with_custom_queryset(self):
        items = HomepageItem.objects \
            .filter(slot=self.slot1).get_content_objects(querysets={
                Article: Article.published.all(),
            })
        print items
        self.assertEquals(len(items), 4)
