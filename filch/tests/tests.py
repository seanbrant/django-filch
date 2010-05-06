from django.test import TestCase


from filch.tests.models import Group, Location, Person


class BaseTestCase(TestCase):

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


class ManyToManyChangeTestCase(object):

    def test_many_to_many_change(self):
        self.assertEquals(self.person.group_list, [])

        self.person.groups.add(self.group1)
        self.assertEquals(self.person.group_list, [{'name': 'PyChi'}])

        self.person.groups.add(self.group2)
        self.assertEquals(self.person.group_list,
            [{'name': 'PyChi'}, {'name': 'WhiteSoxsFan'}])

        self.person.groups.remove(self.group1)
        self.assertEquals(self.person.group_list, [{'name': 'WhiteSoxsFan'}])

        self.person.groups.clear()
        self.assertEquals(self.person.group_list, [])


class RelatedInstanceUpdateTestCase(BaseTestCase):

    def test_related_instance_update(self):
        self.person.groups.add(self.group1)
        self.assertEquals(self.person.group_list, [{'name': 'PyChi'}])

        self.group1.name = 'Chicago Djangonauts'
        self.group1.save()
        self.assertEquals(self.person.group_list,
            [{'name': 'Chicago Djangonauts'}])

        self.group1.delete()
        self.assertEquals(self.person.group_list, [])
