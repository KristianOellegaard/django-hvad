from nani.tests.admin import NormalAdminTests
from nani.tests.basic import (OptionsTest, BasicQueryTest, CreateTest, GetTest, 
    TranslatedTest, DeleteLanguageCodeTest, GetByLanguageTest, FallbackTest)
from nani.tests.dates import LatestTests
from nani.tests.query import (FilterTests, IterTests, UpdateTests, 
    ValuesListTests, ValuesTests, DeleteTests)
from nani.tests.related import (NormalToNormalFKTest, TransToNormalFKTest, 
    TransToTransFKTest, NormalToTransFKTest, StandardToTransFKTest)
from nani.tests.forms import FormTests