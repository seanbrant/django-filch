from django.db import models
from django.db.models.loading import get_model


class GenericResolutionQueryset(models.query.QuerySet):

    def __init__(self, *args, **kwargs):
        super(GenericResolutionQueryset, self).__init__(*args, **kwargs)
        self.ordering = self.model._meta.ordering

    def get_content_objects(self, querysets={}, select_related=True):
        models = {}
        objects = {}
        results = []
        order_fields = self.model._meta.ordering
        values = self.values('pk', 'object_id', 'content_type__app_label',
            'content_type__model', *order_fields)
        for item in values:
            pk = item.pop('pk')
            object_id = item.pop('object_id')
            app_label = item.pop('content_type__app_label')
            model_name = item.pop('content_type__model')
            ordering = item
            model = get_model(app_label, model_name)
            models.setdefault(model, {}) \
                .setdefault(object_id, []).append(ordering)
        for model, objs in models.items():
            if model in querysets:
                qs = querysets[model]
            else:
                qs = model._default_manager
            if select_related:
                qs = qs.select_related()
            object_list = qs.filter(pk__in=objs.keys())
            for obj in object_list:
                objects.setdefault(model, {})[obj.pk] = obj
        for model, objs in models.items():
            for pk, ordering in objs.items():
                for order in ordering:
                    try:
                        fields = objects[model][pk].__dict__.copy()
                        state = fields.pop('_state')
                        obj = model(**fields)
                        obj.__temp_ordering = order
                        obj._state = state
                        results.append(obj)
                    except KeyError:
                        pass
        for order in order_fields:
            results.sort(key=lambda i: i.__temp_ordering[order])
        for result in results:
            del result.__temp_ordering
        return results


class GenericResolutionManager(models.Manager):

    def get_query_set(self):
        return GenericResolutionQueryset(self.model)
