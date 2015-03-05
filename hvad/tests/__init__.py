import django
if django.VERSION < (1, 6): # Starting from django 1.6 we use DiscoverRunner instead
    from hvad.tests.admin import (ModelHelpersTests, AdminMethodsTests,
                                  NormalAdminTests, AdminEditTests,
                                  AdminNoFixturesTests, AdminDeleteTranslationsTests,
                                  AdminRelationTests, TranslatableInlineAdminTests)
    from hvad.tests.basic import (OptionsTest, BasicQueryTest, QuerysetTest, AlternateCreateTest,
                                  CreateTest, GetTest, TranslatedTest,
                                  DeleteLanguageCodeTest, GetByLanguageTest,
                                  GetAllLanguagesTest, DescriptorTests,
                                  DefinitionTests, TableNameTest, GetOrCreateTest,
                                  BooleanTests)
    from hvad.tests.dates import LatestTests, DatesTests
    from hvad.tests.docs import DocumentationTests
    from hvad.tests.fallbacks import (FallbackTests, FallbackFilterTests, FallbackCachingTests,
                                      FallbackIterTests, FallbackValuesListTests,
                                      FallbackValuesTests, FallbackInBulkTests,
                                      FallbackNotImplementedTests)
    from hvad.tests.forms import (FormDeclarationTests, FormInstantiationTests,
                                  FormValidationTests, FormCommitTests, FormsetTests)
    from hvad.tests.ordering import OrderingTest, DefaultOrderingTest
    from hvad.tests.query import (FilterTests, ExtraTests, QueryCachingTests, IterTests, UpdateTests,
        ValuesListTests, ValuesTests, InBulkTests, DeleteTests, GetTranslationFromInstanceTests,
        AggregateTests, NotImplementedTests, ExcludeTests, ComplexFilterTests,
        MinimumVersionTests)
    from hvad.tests.related import (NormalToNormalFKTest, StandardToTransFKTest,
        TripleRelationTests, ManyToManyTest, ForwardDeclaringForeignKeyTests,
        SelectRelatedTests, DeepSelectRelatedTests)
    from hvad.tests.forms_inline import TestBasicInline, TestTranslationsInline
    from hvad.tests.views import CreateViewTests, UpdateViewTests, TransitionTests
    from hvad.tests.limit_choices_to import LimitChoicesToTests
    from hvad.tests.serialization import PicklingTest
    from hvad.tests.proxy import ProxyTests
    from hvad.tests.abstract import AbstractTests
    from hvad.tests.queryset_override import (BasicTests, FilterTests, RelatedManagerTests,
                                              PrefetchRelatedTests)
    from hvad.tests.utils import TranslationAccessorTests
    from hvad.tests.contrib.restframework import (TranslatableModelSerializerTests,
                                                  TranslationsMixinTests,
                                                  CombinedTests)
