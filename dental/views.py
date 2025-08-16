from django.shortcuts import render
from .models import DentalRecord

def dental_records(request):
    records = DentalRecord.objects.all()
    return render(request, 'dental/dental_records.html', {'records': records})