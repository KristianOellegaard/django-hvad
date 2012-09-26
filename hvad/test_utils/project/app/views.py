from django.core.urlresolvers import reverse
from hvad.views import TranslatableUpdateView
from hvad.test_utils.project.app.models import Normal

class NormalUpdateView(TranslatableUpdateView):
    model = Normal
    slug_field = 'shared_field'

    def get_success_url(self):
        return reverse('update_normal', args=[self.object.id])
