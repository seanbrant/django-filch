from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import connection
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
        self.person = Person.objects.get(pk=self.person.pk)
        self.assertEquals(self.person.group_list,
            [
                {'location': {'name': 'Chicago'}, 'name': 'Djangonauts'},
            ])

        self.group1.delete()
        self.person = Person.objects.get(pk=self.person.pk)
        self.assertEquals(self.person.group_list, [])

    def test_main_model_update_error(self):
        person = Person.objects.create(name='Sean')
        person.save()
        person.groups.add(self.group1)
        person.groups.add(self.group2)
        person.save()
        self.assertEquals(person.group_list, [{'name': 'PyChi', 'location': {'name': 'Chicago'}}, {'name': 'WhiteSoxsFan', 'location': {'name': 'Chicago'}}])
        person = Person.objects.get(id=person.id)
        person.name = 'Matt'
        person.save()
        person.groups.clear()
        person.groups.add(self.group1)
        person.groups.add(self.group2)
        person.save()
        self.assertEquals(person.group_list, [{'name': 'PyChi', 'location': {'name': 'Chicago'}}, {'name': 'WhiteSoxsFan', 'location': {'name': 'Chicago'}}])

    def test_multiple_instances(self):
        person1 = Person.objects.create(name="Maria")
        person2 = Person.objects.create(name="Juan")

        person1.groups.add(self.group1)

        self.assertEqual(person1.group_list, [{'name': 'PyChi', 'location': {'name': 'Chicago'}}])

    def test_disconnect_signals(self):
        field = Person._meta.get_field("group_list")
        field.disconnect_signals()

        person = Person.objects.create(name="Maria")

        person.groups.add(self.group1)

        self.assertEqual(person.group_list, [])

        field.connect_signals()

    def test_update_queryset(self):
        _old_debug = settings.DEBUG
        settings.DEBUG = True

        field = Person._meta.get_field("group_list")
        field.disconnect_signals()

        person1 = Person.objects.create(name="Maria")
        person2 = Person.objects.create(name="Juan")

        person1.groups.add(self.group1)
        person2.groups.add(self.group2)

        self.assertEqual(person1.group_list, [])
        self.assertEqual(person2.group_list, [])

        connection.queries = []
        field.update_queryset(Person.objects.all())
        self.assertEqual(len(connection.queries), 5)

        person1 = Person.objects.get(pk=person1.pk)
        person2 = Person.objects.get(pk=person2.pk)
        self.assertEqual(person1.group_list, [{'name': 'PyChi', 'location': {'name': 'Chicago'}}])
        self.assertEqual(person2.group_list, [{'name': 'WhiteSoxsFan', 'location': {'name': 'Chicago'}}])

        field.connect_signals()
        settings.DEBUG = _old_debug

class GenericResolutionManagerTestCase(TestCase):

    def setUp(self):
        self.author = User.objects.create(
            username='Sean',
            email='test@test.com',
        )
        self.article1 = Article.objects.create(
            name='Django 1.2 released!',
            author=self.author,
        )
        self.article2 = Article.objects.create(
            name='Filch is a real query saver',
            author=self.author,
        )
        self.article3 = Article.objects.create(
            name='Unpublished!',
            is_published=False,
            author=self.author,
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
        self.assertEquals(len(items), 4)

    def test_get_content_objects_with_annotate(self):
        items = HomepageItem.objects \
            .filter(slot=self.slot1).get_content_objects(annotate=('slot__name',))
        for item in items:
            self.assertTrue(hasattr(item, 'slot'))
