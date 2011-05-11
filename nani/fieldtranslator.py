from django.db.models.sql.constants import QUERY_TERMS

TRANSLATIONS = 1
TRANSLATED = 2
NORMAL = 3


MODEL_INFO = {}


def _build_model_info(model):
    """
    Builds the model information dictinary for get_model_info
    """
    from nani.models import BaseTranslationModel, TranslatableModel
    info = {}
    if issubclass(model, BaseTranslationModel):
        info['type'] = TRANSLATIONS
        info['shared'] = model._meta.shared_model._meta.get_all_field_names() + ['pk']
        info['translated'] = model._meta.get_all_field_names()
    elif issubclass(model, TranslatableModel):
        info['type'] = TRANSLATED
        info['shared'] = model._meta.get_all_field_names() + ['pk']
        info['translated'] = model._meta.translations_model._meta.get_all_field_names()
    else:
        info['type'] = NORMAL
        info['shared'] = model._meta.get_all_field_names() + ['pk']
        info['translated'] = []
    if 'id' in info['translated']:
        info['translated'].remove('id')
    return info

def get_model_info(model):
    """
    Returns a dictionary with 'translated' and 'shared' as keys, and a list of
    respective field names as values. Also has a key 'type' which is either 
    TRANSLATIONS, TRANSLATED or NORMAL
    """
    if model not in MODEL_INFO:
        MODEL_INFO[model] = _build_model_info(model)
    return MODEL_INFO[model]

def _get_model_from_field(starting_model, fieldname):
    # TODO: m2m handling
    field, model, direct, _ = starting_model._meta.get_field_by_name(fieldname)
    if model:
        return model
    elif direct:
        return field.rel.to
    else:
        return field.model

def translate(querykey, starting_model):
    """
    Translates a querykey starting from a given model to be 'translation aware'.
    """
    bits = querykey.split('__')
    translated_bits = []
    model = starting_model
    language_joins = []
    max_index = len(bits) - 1
    for index, bit in enumerate(bits):
        model_info = get_model_info(model)
        if bit in QUERY_TERMS:
            translated_bits.append(bit)
        elif model_info['type'] == NORMAL:
            translated_bits.append(bit)
        elif model_info['type'] == TRANSLATED:
            if bit in model_info['translated']:
                translated_bits.append(model._meta.translations_accessor)
                path = '__'.join(translated_bits)
                language_joins.append('%s__language_code' % path)
                translated_bits.append(bit)
            else:
                path = '__'.join(translated_bits + [model._meta.translations_accessor])
                language_joins.append('%s__language_code' % path)
                translated_bits.append(bit)
        else:
            if bit in model_info['translated']:
                translated_bits.append(bit)
            else:
                path = '__'.join(translated_bits)
                language_joins.append('%s__language_code' % path)
                translated_bits.append('master')
                translated_bits.append(bit)
        # do we really want to get the next model? Is there a next model?
        if index < max_index:
            next = bits[index + 1]
            if next not in QUERY_TERMS:
                model = _get_model_from_field(model, bit)
    return '__'.join(translated_bits), language_joins
