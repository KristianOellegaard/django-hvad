import django
if django.VERSION >= (1, 4):
    from django.test.signals import setting_changed
    def settings_updater(func):
        func()
        setting_changed.connect(func, dispatch_uid=id(func))
        return func

else: #pragma: no cover
    def settings_updater(func):
        func()
        return func
