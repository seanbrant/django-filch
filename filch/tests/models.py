from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

from filch.fields import DenormManyToManyField
from filch.managers import GenericResolutionManager


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


class Slot(models.Model):
    name = models.CharField(max_length=50)


class HomepageItem(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    order = models.PositiveIntegerField()
    slot = models.ForeignKey(Slot)

    objects = GenericResolutionManager()

    class Meta(object):
        ordering = ('order', 'slot__name')


class PublishedManager(models.Manager):

    def get_query_set(self):
        qs = super(PublishedManager, self).get_query_set()
        return qs.filter(is_published=True)


class Article(models.Model):
    name = models.CharField(max_length=50)
    is_published = models.BooleanField(default=True)

    objects = models.Manager()
    published = PublishedManager()

    def __unicode__(self):
        return self.name


class Press(models.Model):
    name = models.CharField(max_length=50)
