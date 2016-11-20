from django.conf import settings as djsettings
from django.core import checks
from django.test.signals import setting_changed
from django.utils.functional import SimpleLazyObject, empty
from collections import namedtuple

__all__ = ('hvad_settings', )

#===============================================================================

_default_settings = {
    'LANGUAGES': tuple(djsettings.LANGUAGES),
    'FALLBACK_LANGUAGES': None,     # dynamic default
    'TABLE_NAME_FORMAT': '%s_translation',
    'AUTOLOAD_TRANSLATIONS': True,
    'USE_DEFAULT_QUERYSET': False,
}

#===============================================================================

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

    # Check for unknown settings
    hvad_settings = getattr(djsettings, 'HVAD', {})
    for key in hvad_settings:
        if key == 'TABLE_NAME_SEPARATOR':   # remove in 1.9
            errors.append(checks.Error('Obsolete setting HVAD["TABLE_NAME_SEPARATOR"]',
                hint='TABLE_NAME_SEPARATOR has been superceded by TABLE_NAME_FORMAT. '
                     'Set it to "%%s%stranslation" to keep the old behavior' % (
                         hvad_settings[key],
                     ),
                obj=key,
                id='hvad.settings.E01',
            ))
        elif key not in _default_settings:
            errors.append(checks.Warning('Unknown setting HVAD[%r]' % key, obj=key,
                                         id='hvad.settings.W01'))

    # Check for common mistakes
    languages = hvad_settings.get('LANGUAGES', ())
    if (not isinstance(languages, (tuple, list)) or
        not all(isinstance(item, str) for item in languages)):
        errors.append(checks.Error('HVAD["LANGUAGES"] must be a sequence of language codes',
                                   obj='LANGUAGES', id='hvad.settings.E02'))

    if hvad_settings.get('TABLE_NAME_FORMAT', '%s').count('%s') != 1:
        errors.append(checks.Error('HVAD["TABLE_NAME_FORMAT"] must contain exactly one string '
                                   'specifier ("%s")',
                                   obj='TABLE_NAME_FORMAT', id='hvad.settings.E03'))
    return errors

def _build():
    user_settings = getattr(djsettings, 'HVAD', {})
    hvad_settings = _default_settings.copy()
    hvad_settings.update({
        'FALLBACK_LANGUAGES': tuple(code for code, name in
                                    user_settings.get('LANGUAGES', djsettings.LANGUAGES)),
    })
    hvad_settings.update(user_settings)
    return namedtuple('HvadSettings', hvad_settings.keys())(*hvad_settings.values())

hvad_settings = SimpleLazyObject(_build)

def invalidate_settings(**kwargs):
    hvad_settings._wrapped = empty
setting_changed.connect(invalidate_settings)
