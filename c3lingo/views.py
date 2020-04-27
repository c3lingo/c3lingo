from django.shortcuts import render
from django.views import generic

def index(request):
    context = {
        'page_title': 'c3Lingo',
    }
    return render(request, 'index.html', context)
