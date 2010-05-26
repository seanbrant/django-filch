from django.db import models
from django.db.models.loading import get_model

from filch.utils import convert_lookup_to_dict


class GenericResolutionQueryset(models.query.QuerySet):

    def __init__(self, *args, **kwargs):
        super(GenericResolutionQueryset, self).__init__(*args, **kwargs)
        self.ordering = self.model._meta.ordering

    def get_content_objects(self, querysets={}, annotate=[], select_related=True):
        models = {}
        objects = {}
        results = []
        order_fields = list(self.model._meta.ordering)
        annotate_fields = list(annotate)
        extras = []
        extras.extend(order_fields)
        extras.extend(annotate_fields)
        values = self.values('pk', 'object_id', 'content_type__app_label',
            'content_type__model', *extras)
        for item in values:
            pk = item.pop('pk')
            object_id = item.pop('object_id')
            app_label = item.pop('content_type__app_label')
            model_name = item.pop('content_type__model')
            annotated = dict((k, v) for k, v in item.items() if k in annotate_fields)
            ordering = dict((k, v) for k, v in item.items() if k in order_fields)
            model = get_model(app_label, model_name)
            models.setdefault(model, {}) \
                .setdefault(object_id, []).append({
                    'ordering': ordering,
                    'annotated': annotated,
                })
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
            for pk, options_list in objs.items():
                for options in options_list:
                    try:
                        fields = objects[model][pk].__dict__.copy()
                        private_fields = dict((k, fields.pop(k)) for k in \
                            fields.keys() if k.startswith('_'))
                        obj = model(**fields)
                        obj.__temp_ordering = options['ordering']
                        for name, annotate in options['annotated'].items():
                            k, v = convert_lookup_to_dict(name, annotate)
                            setattr(obj, k, v)
                        obj.__dict__.update(private_fields)
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
