from django.db import models
from django.utils.translation import gettext_lazy as _


class DocReview(models.Model):
    """
    Reviews made by checker users for uploaded documents
    """
    is_ok = models.BooleanField(default=False, help_text=_("Document is ok to be disbursed"))
    doc = models.ForeignKey("data.Doc", on_delete=models.CASCADE, related_name='reviews')
    user_created = models.ForeignKey("users.CheckerUser", on_delete=models.CASCADE)
    comment = models.CharField(max_length=255, null=True, blank=True, help_text=_("Empty if the review is ok"))
    timestamp = models.DateField(auto_now_add=True)

    def __str__(self):
        """
        :return: String representation for the DocReview model objects
        """
        if self.comment:
            return f"{self.comment[:12]}... by {self.user_created.username}"

        return f"Doc is ok ... by {self.user_created.username}"
