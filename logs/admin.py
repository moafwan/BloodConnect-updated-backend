from django.contrib import admin
from .models import LogEntry

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'level', 'module', 'user_id', 'request_path')
    list_filter = ('level', 'module', 'timestamp')
    search_fields = ('message', 'request_path')
    readonly_fields = ('timestamp',)
    list_per_page = 50
    
    def has_add_permission(self, request):
        return False  # Prevent manual log entry creation
    
    def has_change_permission(self, request, obj=None):
        return False  # Prevent log modification
    
    def has_delete_permission(self, request, obj=None):
        return True  # Allow deletion for cleanup