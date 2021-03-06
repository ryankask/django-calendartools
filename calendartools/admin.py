from django.contrib import admin
from django.db.models.loading import get_model
from calendartools import defaults

class AuditedAdmin(admin.ModelAdmin):
    raw_id_fields = ['creator', 'editor']
    readonly_fields = ('creator', 'editor', 'created', 'modified')
    date_hierarchy = 'created'


class CalendarAdmin(AuditedAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ['name', 'slug', 'description', 'status', 'created']
    list_editable = ['status']
    search_fields = ('name',)


class EventAdmin(CalendarAdmin):
    pass


class CancellationInline(admin.TabularInline):
    model = get_model(defaults.CALENDAR_APP_LABEL, 'Cancellation')
    readonly_fields = ('creator', 'editor', 'created', 'modified')


class OccurrenceAdmin(AuditedAdmin):
    list_display = ['calendar', 'event', 'start', 'finish', 'status',
                    'created']
    list_editable = ['status']
    search_fields = ('event__name',)


class AttendanceAdmin(AuditedAdmin):
    raw_id_fields = ['creator', 'editor', 'user', 'occurrence']
    list_display = ['user', 'occurrence', 'status', 'created']
    list_editable = ['status']
    inlines = [CancellationInline]


Calendar = get_model(defaults.CALENDAR_APP_LABEL, 'Calendar')
Event = get_model(defaults.CALENDAR_APP_LABEL, 'Event')
Occurrence = get_model(defaults.CALENDAR_APP_LABEL, 'Occurrence')
Attendance = get_model(defaults.CALENDAR_APP_LABEL, 'Attendance')

admin.site.register(Calendar, CalendarAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Occurrence, OccurrenceAdmin)
admin.site.register(Attendance, AttendanceAdmin)
