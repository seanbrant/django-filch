from django.db import models

from filch.utils import dumps, loads


class DenormManyToManyFieldDescriptor(object):

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
        return [v for k, v in instance.__dict__[self.field.name]]

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
        return dict([(attr, self._resolve(instance, attr)) for \
            attr in self.attrs])

    def _update(self, **kwargs):
        # If its been created it's not related. We can also ignore
        # any pre change actions.
        action = kwargs.get('action', None)
        if kwargs.get('created') or action and 'pre_' in action:
            return
        objects = getattr(self.current_instance, self.from_field).all()
        items = [[o.pk, self._prepare(o)] for o in objects]
        self.current_instance.__dict__[self.name] = dumps(items)
        self.current_instance.__class__.objects \
            .filter(pk=self.current_instance.pk) \
            .update(**{self.name: self.current_instance.__dict__[self.name]})

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
        models.signals.post_save.connect(self._update, related.field.rel.to)
        models.signals.post_delete.connect(self._update, related.field.rel.to)
        # We need a reference to the current instance for use in
        # the signal handlers.
        self.current_instance = instance

    def contribute_to_class(self, cls, name):
        super(DenormManyToManyField, self).contribute_to_class(cls, name)
        setattr(cls, name, DenormManyToManyFieldDescriptor(self))
        # We need access to the from_field but it is not guaranteed
        # until after the model has been initialized.
        models.signals.post_init.connect(self._connect, cls)
