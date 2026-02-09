from django.shortcuts import render

def fire_dashboard(request):
    return render(request, "frontend/fire_dashboard.html")


def dashboard(request):
    return render(request, "frontend/dashboard.html")

def login_view(request):
    return render(request, "frontend/login.html")