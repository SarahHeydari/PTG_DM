from django.shortcuts import render

def fire_dashboard(request):
    return render(request, "frontend/fire_dashboard.html")


def dashboard(request):
    return render(request, "frontend/dashboard.html")

def register_page(request):
    return render(request, "frontend/register.html")


def login_page(request):
    return render(request, "frontend/login.html")


def profile_router(request):
    return render(request, "frontend/profile_router.html")

def manager_profile(request):
    return render(request, "frontend/manager_profile.html")

def expert_profile(request):
    return render(request, "frontend/expert_profile.html")

def admin_profile(request):
    return render(request, "frontend/admin_profile.html")



