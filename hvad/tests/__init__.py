from hvad.tests.admin import (NormalAdminTests, AdminEditTests, 
    AdminNoFixturesTests, AdminDeleteTranslationsTests, AdminRelationTests,
    TranslatableInlineAdminTests)
from hvad.tests.basic import (OptionsTest, BasicQueryTest, AlternateCreateTest, CreateTest, GetTest, 
    TranslatedTest, DeleteLanguageCodeTest, GetByLanguageTest, DescriptorTests, 
    DefinitionTests, TableNameTest, GetOrCreateTest)
from hvad.tests.dates import LatestTests, DatesTests
from hvad.tests.docs import DocumentationTests
from hvad.tests.fallbacks import FallbackTests
from hvad.tests.fieldtranslator import FieldtranslatorTests
from hvad.tests.forms import FormTests
from hvad.tests.ordering import OrderingTest
from hvad.tests.query import (FilterTests, IterTests, UpdateTests, 
    ValuesListTests, ValuesTests, DeleteTests, GetTranslationFromInstanceTests, 
    AggregateTests, NotImplementedTests, ExcludeTests, ComplexFilterTests)
from hvad.tests.related import (NormalToNormalFKTest, StandardToTransFKTest, 
    TripleRelationTests, ManyToManyTest, ForwardDeclaringForeignKeyTests)
from hvad.tests.forms_inline import TestBasicInline
from hvad.tests.views import ViewsTest
from hvad.tests.limit_choices_to import LimitChoicesToTests
from hvad.tests.serialization import PicklingTest
