from django.db import models


class DocReview(models.Model):
    is_ok = models.BooleanField(default=False)
    doc = models.ForeignKey(
        "data.Doc", on_delete=models.CASCADE, related_name='reviews')
    user_created = models.ForeignKey(
        "users.CheckerUser", on_delete=models.CASCADE)
    comment = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateField(auto_now_add=True)

    def __str__(self):
        return "{}... for {}".format(self.comment[:12], self.user_created)
