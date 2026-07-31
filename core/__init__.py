import django_filters
from .models import Job

class JobFilter(django_filters.FilterSet):
    skills = django_filters.CharFilter(field_name='skills_required', lookup_expr='icontains')
    location = django_filters.CharFilter(field_name='location', lookup_expr='icontains')
    job_type = django_filters.CharFilter(field_name='job_type', lookup_expr='exact')
    min_salary = django_filters.NumberFilter(field_name='salary_min', lookup_expr='gte')
    max_salary = django_filters.NumberFilter(field_name='salary_max', lookup_expr='lte')
    experience = django_filters.CharFilter(field_name='experience_required', lookup_expr='icontains')

    class Meta:
        model = Job
        fields = ['skills', 'location', 'job_type', 'min_salary', 'max_salary', 'experience']