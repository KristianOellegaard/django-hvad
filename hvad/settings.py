from django.conf import settings as djsettings
from django.core import checks
from django.test.signals import setting_changed
from django.utils.functional import SimpleLazyObject, empty
from collections import namedtuple

__all__ = ('hvad_settings', )

#===============================================================================

_default_settings = {
    'LANGUAGES': djsettings.LANGUAGES,
    'FALLBACK_LANGUAGES': None,     # dynamic default
    'TABLE_NAME_FORMAT': '%s_translation',
    'AUTOLOAD_TRANSLATIONS': True,
    'USE_DEFAULT_QUERYSET': False,
}

#===============================================================================

class HvadSettingsChecks:
    # Legacy setting, remove extended error description in hvad 1.9 """
    @staticmethod
    def check_TABLE_NAME_SEPARATOR(value):
        return (
            checks.Error('Obsolete setting HVAD["TABLE_NAME_SEPARATOR"]',
                hint='TABLE_NAME_SEPARATOR has been superceded by TABLE_NAME_FORMAT. '
                     'Set it to "%%s%stranslation" to keep the old behavior' % value,
                obj='TABLE_NAME_SEPARATOR',
                id='hvad.settings.E01',
            ),
        )

    @staticmethod
    def check_LANGUAGES(value):
        errors = []
        if (not isinstance(value, (tuple, list)) or
            not all(isinstance(item, tuple) for item in value) or
            not all(len(item) == 2 for item in value) or
            not all(isinstance(item[0], str) for item in value)):
            errors.append(checks.Error('HVAD["LANGUAGES"] must be a sequence of (code, name)'
                                       'tuples describing languages',
                                       obj='LANGUAGES', id='hvad.settings.E02'))
        return errors

    @staticmethod
    def check_FALLBACK_LANGUAGES(value):
        errors = []
        if (not isinstance(value, (tuple, list)) or
            not all(isinstance(item, str) for item in value)):
            errors.append(checks.Error('HVAD["FALLBACK_LANGUAGES"] must be a sequence of '
                                       'language codes',
                                       obj='FALLBACK_LANGUAGES', id='hvad.settings.E03'))
        return errors

    @staticmethod
    def check_TABLE_NAME_FORMAT(value):
        errors = []
        if value.count('%s') != 1:
            errors.append(checks.Error('HVAD["TABLE_NAME_FORMAT"] must contain exactly '
                                       'one string specifier ("%s")',
                                       obj='TABLE_NAME_FORMAT', id='hvad.settings.E04'))
        return errors

    @staticmethod
    def check_AUTOLOAD_TRANSLATIONS(value):
        errors = []
        if not isinstance(value, bool):
            errors.append(checks.Warning('HVAD["AUTOLOAD_TRANSLATIONS"] should be True or False',
                                         obj='AUTOLOAD_TRANSLATIONS', id='hvad.settings.W02'))
        return errors

    @staticmethod
    def check_USE_DEFAULT_QUERYSET(value):
        errors = []
        if not isinstance(value, bool):
            errors.append(checks.Warning('HVAD["USE_DEFAULT_QUERYSET"] should be True or False',
                                         obj='USE_DEFAULT_QUERYSET', id='hvad.settings.W03'))
        return errors


@checks.register(checks.Tags.models)
def check(app_configs, **kwargs):
    errors = []

    # Check for old hvad settings in global namespace
    for key in dir(djsettings):
        if key.startswith('HVAD_'):
            errors.append(checks.Critical('HVAD setting in global namespace',
                hint='HVAD settings are now namespaced in the HVAD dict.',
                obj=key,
                id='hvad.settings.C01',
            ))

    hvad_settings = getattr(djsettings, 'HVAD', {})
    for key, value in hvad_settings.items():
        try:
            checker = getattr(HvadSettingsChecks, 'check_%s' % key)
        except AttributeError:
            errors.append(checks.Warning('Unknown setting HVAD[%r]' % key, obj=key,
                                         id='hvad.settings.W01'))
        else:
            errors.extend(checker(value))
    return errors


def _build():
    # Generate final values
    user_settings = getattr(djsettings, 'HVAD', {})
    hvad_settings = _default_settings.copy()
    hvad_settings.update({
        'FALLBACK_LANGUAGES': tuple(code for code, name in
                                    user_settings.get('LANGUAGES', djsettings.LANGUAGES)),
    })
    hvad_settings.update(user_settings)

    # Ensure settings are frozen
    hvad_settings['LANGUAGES'] = tuple(hvad_settings['LANGUAGES'])
    hvad_settings['FALLBACK_LANGUAGES'] = tuple(hvad_settings['FALLBACK_LANGUAGES'])
    return namedtuple('HvadSettings', hvad_settings.keys())(*hvad_settings.values())

hvad_settings = SimpleLazyObject(_build)

def invalidate_settings(**kwargs):
    hvad_settings._wrapped = empty
setting_changed.connect(invalidate_settings)
