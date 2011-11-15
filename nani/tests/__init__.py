from nani.tests.admin import (NormalAdminTests, AdminEditTests, 
    AdminNoFixturesTests, AdminDeleteTranslationsTests, AdminRelationTests,
    TranslatableInlineAdminTests)
from nani.tests.basic import (OptionsTest, BasicQueryTest, CreateTest, GetTest, 
    TranslatedTest, DeleteLanguageCodeTest, GetByLanguageTest, DescriptorTests, 
    DefinitionTests, TableNameTest)
from nani.tests.dates import LatestTests, DatesTests
from nani.tests.docs import DocumentationTests
from nani.tests.fallbacks import FallbackTests
from nani.tests.fieldtranslator import FieldtranslatorTests
from nani.tests.forms import FormTests
from nani.tests.ordering import OrderingTest
from nani.tests.query import (FilterTests, IterTests, UpdateTests, 
    ValuesListTests, ValuesTests, DeleteTests, GetTranslationFromInstanceTests, 
    AggregateTests, NotImplementedTests, ExcludeTests, ComplexFilterTests)
from nani.tests.related import (NormalToNormalFKTest, StandardToTransFKTest, 
    TripleRelationTests)
from nani.tests.forms_inline import TestBasicInline
from nani.tests.views import ViewsTest
from nani.tests.limit_choices_to import LimitChoicesToTests
