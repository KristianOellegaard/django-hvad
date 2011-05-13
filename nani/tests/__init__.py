from nani.tests.admin import (NormalAdminTests, AdminEditTests, 
    AdminNoFixturesTests)
from nani.tests.basic import (OptionsTest, BasicQueryTest, CreateTest, GetTest, 
    TranslatedTest, DeleteLanguageCodeTest, GetByLanguageTest, FallbackTest, 
    DescriptorTests, DefinitionTests)
from nani.tests.dates import LatestTests, DatesTests
from nani.tests.forms import FormTests
from nani.tests.query import (FilterTests, IterTests, UpdateTests, 
    ValuesListTests, ValuesTests, DeleteTests, GetTranslationFromInstanceTests,
    AggregateTests, NotImplementedTests, ExcludeTests, ComplexFilterTests)
from nani.tests.related import (NormalToNormalFKTest, StandardToTransFKTest, 
    TripleRelationTests)
from nani.tests.ordering import OrderingTest
from nani.tests.docs import DocumentationTests