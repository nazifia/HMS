
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import AuthorizationCodeForm
from .models import AuthorizationCode

def generate_authorization_code(request):
    if request.method == 'POST':
        form = AuthorizationCodeForm(request.POST)
        if form.is_valid():
            authorization_code = form.save()
            messages.success(request, f'Authorization code {authorization_code.code} generated successfully.')
            return redirect('desk_office:generate_authorization_code')
    else:
        form = AuthorizationCodeForm()
    return render(request, 'desk_office/generate_authorization_code.html', {'form': form})

def verify_authorization_code(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            authorization_code = AuthorizationCode.objects.get(code=code)
            # You can add more logic here to check the status of the code
            messages.success(request, f'Authorization code {authorization_code.code} is valid.')
            return render(request, 'desk_office/verify_authorization_code.html', {'authorization_code': authorization_code})
        except AuthorizationCode.DoesNotExist:
            messages.error(request, 'Invalid authorization code.')
            return redirect('desk_office:verify_authorization_code')
    return render(request, 'desk_office/verify_authorization_code.html')
