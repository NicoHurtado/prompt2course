from django.shortcuts import render


def custom_404(request, exception):
    """Custom 404 error handler that displays the branded Cursia page."""
    return render(request, '404.html', status=404) 