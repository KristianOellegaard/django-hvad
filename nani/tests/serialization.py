import pickle
from nani.test_utils.testcase import NaniTestCase
from nani.test_utils.context_managers import LanguageOverride
from testproject.app.models import Normal

class PicklingTest(NaniTestCase):
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
        with LanguageOverride('en'):
            normal = Normal.objects.create(
                shared_field="Shared",
                translated_field = "English",
            )
        serialized_repr = pickle.dumps(normal)

        unpickled = pickle.loads(serialized_repr)
        self.assertEqual(normal.shared_field, unpickled.shared_field)
        self.assertEqual(normal.language_code, unpickled.language_code)
        self.assertEqual(normal.translated_field, unpickled.translated_field)
