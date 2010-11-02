from django.db import models
from django.db.models.related import RelatedObject
from django.utils.functional import curry

from filch.utils import dumps, loads, convert_lookup_to_dict


class DenormManyToManyFieldDescriptor(object):
    """Field descriptor for denormalizing bits of data from a 
    many-to-many relationship.
    """

    def __init__(self, field):
        self.field = field

    def __get__(self, instance, owner):
        items = instance.__dict__[self.field.name]
        if isinstance(items, basestring) or items is None:
            try:
                items = loads(items)
                if not isinstance(items, list):
                    raise ValueError
                instance.__dict__[self.field.name] = items
            except ValueError:
                raise ValueError("You can only pass in a python list " \
                    "or json formated array. You passed in %s" % items)
        # We iterate over the items and only return the values
        # not the keys.
        return instance.__dict__[self.field.name]

    def __set__(self, instance, value):
        instance.__dict__[self.field.name] = value


class DenormManyToManyField(models.TextField):

    def __init__(self, from_field, attrs, *args, **kwargs):
        self.from_field = from_field
        self.attrs = attrs

        # If attrs was passed in as a string and not a list
        # lets convert it for use later.
        if isinstance(self.attrs, basestring):
            self.attrs = list(self.attrs)

        kwargs['default'] = []
        kwargs['editable'] = False
        super(DenormManyToManyField, self).__init__(*args, **kwargs)

    def get_prep_value(self, value):
        if not isinstance(value, basestring):
            value = dumps(value)
        return super(DenormManyToManyField, self).get_prep_value(value)

    def _resolve(self, instance, attr):
        # _resolve supports lookups that span relations. So we
        # split attr by '__' and iterate over that.
        current = instance
        for attr in  attr.split('__'):
            current = getattr(current, attr, None)
            if current is None:
                return current
        if callable(current):
            return current()
        return current

    def _prepare(self, instance):
        # The default prepare just iterates over self.attrs
        # and trys and get the value from the instance. You
        # do more custom stuff if you pass attrs as a
        # callable and it will be called with an instance
        # as its only argument.
        if callable(self.attrs):
            return self.attrs(instance)

        return dict([convert_lookup_to_dict(attr, self._resolve(instance, attr))
                     for attr 
                     in self.attrs])

    def _update(self, **kwargs):
        # If its been created it's not related. We can also ignore
        # any pre change actions.
        action = kwargs.get('action', None)
        related_name = kwargs.get('related_name', None)
        deleting = kwargs.get('deleting', False)

        if kwargs.get('created') or action and 'pre_' in action:
            return

        if action:
            self._update_instance(kwargs["instance"])
        elif related_name:
            if deleting:
                remove = [kwargs["instance"]]
            else:
                remove = []
            for instance in getattr(kwargs["instance"], related_name).all():
                self._update_instance(instance, remove)

    def _update_instance(self, instance, remove=None):
        if remove is None:
            remove = []
        objects = getattr(instance, self.from_field).all()
        items = [self._prepare(o) for o in objects
                 if o not in remove]

        instance.__dict__[self.name] = dumps(items)
        instance.__class__.objects \
            .filter(pk=instance.pk) \
            .update(**{self.name: instance.__dict__[self.name]})

    def _connect(self, instance, **kwargs):
        # We need to access the from_field from the class
        # otherwise we get the many-to-many descriptor
        # which throws a primary key error.
        related = getattr(instance.__class__, self.from_field)

        # Connect the signal that listens for changes on the
        # many-to-many through model.
        models.signals.m2m_changed.connect(self._update, related.through)

        # Connect the signal that listens for post save and post
        # delete on the many-to-many to model.
        related_name = RelatedObject(None, instance.__class__, related.field).get_accessor_name()
        models.signals.post_save.connect(curry(self._update,
                                               related_name=related_name),
                                         related.field.rel.to,
                                         weak=False)
        models.signals.pre_delete.connect(curry(self._update,
                                                related_name=related_name,
                                                deleting=True),
                                          related.field.rel.to,
                                          weak=False)

    def contribute_to_class(self, cls, name):
        super(DenormManyToManyField, self).contribute_to_class(cls, name)

        setattr(cls, name, DenormManyToManyFieldDescriptor(self))

        # We need access to the from_field but it is not guaranteed
        # until after the model has been initialized.
        models.signals.post_init.connect(self._connect, cls)

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        from south.modelsinspector import introspector

        field_class = "django.db.models.fields.TextField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)
