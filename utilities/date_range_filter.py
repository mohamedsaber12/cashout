
from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter


class CustomDateRangeFilter(DateRangeFilter):
    # overwrite template that exist in DateRangeFilter to
    # fix calendar and DateTimeShortcuts import issue
    def get_template(self):
        return "date_filter.html"

    template = property(get_template)

class CustomDateTimeRangeFilter(DateTimeRangeFilter):
    def get_template(self):
        return "date_filter.html"

    template = property(get_template)