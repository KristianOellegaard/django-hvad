from nani.utils import get_translation

class NULL:pass

class BaseDescriptor(object):
    """
    Base descriptor class with a helper to get the translations instance.
    """
    def __init__(self, opts):
        self.opts = opts
    
    def translation(self, instance):
        cached = getattr(instance, self.opts.translations_cache, None)
        if not cached:
            cached = get_translation(instance)
            setattr(instance, self.opts.translations_cache, cached)
        return cached


class TranslatedAttribute(BaseDescriptor):
    """
    Basic translated attribute descriptor.
    
    Proxies attributes from the shared instance to the translated instance.
    """
    def __init__(self, opts, name):
        self.name = name
        super(TranslatedAttribute, self).__init__(opts)
        
    def __get__(self, instance, instance_type=None):
        if not instance:
            # Don't raise an attribute error so we can use it in admin.
            return self.opts.translations_model._meta.get_field_by_name(self.name)[0].default
        return getattr(self.translation(instance), self.name)
    
    def __set__(self, instance, value):
        if not instance:
            raise AttributeError()
        setattr(self.translation(instance), self.name, value)
    
    def __delete__(self, instance):
        if not instance:
            raise AttributeError()
        delattr(self.translation(instance), self.name)


class LanguageCodeAttribute(TranslatedAttribute):
    """
    The language_code attribute is different from other attribtues as it cannot
    be deleted. Trying to do so will always cause an attribute error.
    
    """
    def __init__(self, opts):
        super(LanguageCodeAttribute, self).__init__(opts, 'language_code')
    
    def __set__(self, instance, value):
        """
        Setting the language_code attribute is a bit odd.
        
        When changing the language_code on an instance, we try to grab the 
        existing translation and copy over the unfilled fields from that
        translation onto the instance. If no such translation exist, create one
        and copy over the fields from the instance.
        
        This is used to translate instances.
        
        This will also refresh the translations cache attribute on the instance.
        
        EG:
        
            english = MyModel.objects.get(pk=1, language_code='en')
            english.language_code = 'ja'
            english.save()
            japanese = MyModel.objects.get(pk=1, language_code='ja')
        """
        if not instance:
            raise AttributeError()
        tmodel = instance._meta.translations_model
        try:
            other_lang = get_translation(instance, value)
        except tmodel.DoesNotExist:
            other_lang = tmodel()
            for field in other_lang._meta.get_all_field_names():
                val = getattr(instance, field, NULL)
                if val is NULL:
                    continue
                if field == 'pk':
                    continue
                if field == tmodel._meta.pk.name:
                    continue
                setattr(other_lang, field, getattr(instance, field, None))
            other_lang.language_code = value
            other_lang.master = instance
        setattr(instance, instance._meta.translations_cache, other_lang)
    
    def __delete__(self, instance):
        if not instance:
            raise AttributeError()
        raise AttributeError("The 'language_code' attribute cannot be deleted!")