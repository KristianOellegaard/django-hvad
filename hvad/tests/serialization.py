import pickle
from django.utils import translation
from hvad.test_utils.testcase import HvadTestCase
from hvad.test_utils.project.app.models import Normal

class PicklingTest(HvadTestCase):
    def test_untranslated_new_object_can_be_pickled(self):
        normal = Normal(shared_field="Shared")
        serialized_repr = pickle.dumps(normal)

        unpickled = pickle.loads(serialized_repr)
        self.assertEqual(normal.shared_field, unpickled.shared_field)

    def test_translated_new_object_can_be_pickled(self):
        normal = Normal(shared_field="Shared")
        normal.translate("en")
        normal.translated_field = "English"
        serialized_repr = pickle.dumps(normal)

        unpickled = pickle.loads(serialized_repr)
        self.assertEqual(normal.shared_field, unpickled.shared_field)
        self.assertEqual(normal.language_code, unpickled.language_code)
        self.assertEqual(normal.translated_field, unpickled.translated_field)
        
    def test_untranslated_object_can_be_pickled(self):
        normal = Normal.objects.create(
            shared_field="Shared",
        )
        serialized_repr = pickle.dumps(normal)

        unpickled = pickle.loads(serialized_repr)
        self.assertEqual(normal.shared_field, unpickled.shared_field)

    def test_translated_object_can_be_pickled(self):
        with translation.override('en'):
            normal = Normal.objects.create(
                shared_field="Shared",
                translated_field = "English",
            )
        serialized_repr = pickle.dumps(normal)

        unpickled = pickle.loads(serialized_repr)
        self.assertEqual(normal.shared_field, unpickled.shared_field)
        self.assertEqual(normal.language_code, unpickled.language_code)
        self.assertEqual(normal.translated_field, unpickled.translated_field)

    def test_queryset_can_be_pickled(self):
        normal = Normal.objects.create(
            shared_field="Shared",
        )
        qs = Normal.objects.all()
        serialized_repr = pickle.dumps(qs)

        unpickled = pickle.loads(serialized_repr)
        self.assertEqual(unpickled.model, qs.model)
        self.assertEqual(unpickled.get(pk=normal.pk), normal)

    def test_queryset_with_translated_objects_can_be_pickled(self):
        with translation.override('en'):
            normal = Normal.objects.create(
                shared_field="Shared",
                translated_field = "English",
            )
        qs = Normal.objects.all()
        serialized_repr = pickle.dumps(qs)

        unpickled = pickle.loads(serialized_repr)
        self.assertEqual(unpickled.model, qs.model)
        self.assertEqual(unpickled.get(pk=normal.pk), normal)

    def test_translated_queryset_with_translated_objects_can_be_pickled(self):
        with translation.override('en'):
            normal = Normal.objects.create(
                shared_field="Shared",
                translated_field = "English",
            )
        qs = Normal.objects.language('en').all()
        serialized_repr = pickle.dumps(qs)

        unpickled = pickle.loads(serialized_repr)
        self.assertEqual(unpickled.model, qs.model)
        self.assertEqual(unpickled.get(pk=normal.pk), normal)
