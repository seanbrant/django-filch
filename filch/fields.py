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

    def _delete(self, instance, **kwargs):
        for model_instance in getattr(instance, self.related_name).all():
            self.update_instance(model_instance, [instance])

    def _update(self, **kwargs):
        # If its been created it's not related. We can also ignore
        # any pre change actions.
        action = kwargs.get('action', None)

        if kwargs.get('created') or action and 'pre_' in action:
            return

        if action:
            self.update_instance(kwargs["instance"])
        else:
            for instance in getattr(kwargs["instance"], self.related_name).all():
                self.update_instance(instance)

    def update_instance(self, instance, remove=None, objects=None):
        if remove is None:
            remove = []
        if objects is None:
            objects = getattr(instance, self.from_field).all()

        items = [self._prepare(o) for o in objects
                 if o not in remove]

        instance.__dict__[self.name] = dumps(items)
        instance.__class__.objects.filter(pk=instance.pk).update(
            **{self.name: instance.__dict__[self.name]})

    def update_queryset(self, queryset):
        # The name of the FK from the m2m through model to self.model
        m2m_field_name = self.related.field.m2m_field_name()

        # The name of the FK from the m2m through model to the target model
        m2m_reverse_field_name = self.related.field.m2m_reverse_field_name()

        m2m_objects = self.related.through._base_manager.filter(
            **{"%s__in" % m2m_field_name: queryset}).select_related()

        m2m_objects_by_instance_id = {}
        for m2m_obj in m2m_objects:
            instance_pk = getattr(m2m_obj, "%s_id" % m2m_field_name)
            m2m_objects_by_instance_id.setdefault(instance_pk, []).append(m2m_obj)

        for instance in queryset:
            m2m_objs = m2m_objects_by_instance_id.get(instance.pk, [])
            self.update_instance(instance,
                                 objects=[getattr(o, m2m_reverse_field_name)
                                          for o in m2m_objs])


    def _connect_signals_receiver(self, sender, **kwargs):
        assert self.model is sender

        self.related = getattr(self.model, self.from_field)
        self.related_name = RelatedObject(None, self.model, self.related.field).get_accessor_name()

        self.connect_signals()

    def connect_signals(self):
        # Connect the signal that listens for changes on the
        # many-to-many through model.
        models.signals.m2m_changed.connect(self._update,
                                           self.related.through)

        # Connect the signal that listens for post save and post
        # delete on the many-to-many to model.
        models.signals.post_save.connect(self._update,
                                         self.related.field.rel.to)
        models.signals.pre_delete.connect(self._delete,
                                          self.related.field.rel.to)

    def disconnect_signals(self):
        models.signals.m2m_changed.disconnect(self._update, self.related.through)
        models.signals.post_save.disconnect(self._update, self.related.field.rel.to)
        models.signals.pre_delete.connect(self._delete, self.related.field.rel.to)

    def contribute_to_class(self, cls, name):
        super(DenormManyToManyField, self).contribute_to_class(cls, name)

        setattr(cls, name, DenormManyToManyFieldDescriptor(self))

        models.signals.class_prepared.connect(self._connect_signals_receiver, self.model)


    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        from south.modelsinspector import introspector

        field_class = "django.db.models.fields.TextField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)
