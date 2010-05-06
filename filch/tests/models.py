from django.db import models

from filch.fields import DenormManyToManyField


class Location(models.Model):
    name = models.CharField(max_length=50)


class Group(models.Model):
    name = models.CharField(max_length=50)
    location = models.ForeignKey(Location)


class Person(models.Model):
    name = models.CharField(max_length=50)
    groups = models.ManyToManyField(Group)
    group_list = DenormManyToManyField('groups',
        attrs=('name', 'location__name'))
