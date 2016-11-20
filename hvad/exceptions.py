__all__ = ('WrongManager', )

class WrongManager(Exception):
    """ Raised when attempting to introspect translated fields from
        shared models without going through hvad. The most likely cause
        for this being accessing translated fields from
        translation-unaware QuerySets.
    """
    def __init__(self, meta, name):
        self.meta = meta
        self.name = name

    def __str__(self):
        return (
            "Accessing translated fields like {model_name}.{field_name} from "
            "an regular model requires a translation-aware queryset, "
            "obtained with the .language() method. "
            "For regular, non-translatable models, you can get one using "
            "hvad.utils.get_translation_aware_manager"
        ).format(
            app_label=self.meta.app_label,
            model_name=self.meta.model_name,
            field_name=self.name,
        )
