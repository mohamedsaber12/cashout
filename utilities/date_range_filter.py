
from rangefilter.filter import DateRangeFilter


class CustomDateRangeFilter(DateRangeFilter):
    # overwrite template that exist in DateRangeFilter to
    # fix calendar and DateTimeShortcuts import issue
    def get_template(self):
        return "date_filter.html"

    template = property(get_template)
