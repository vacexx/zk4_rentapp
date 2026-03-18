from datetime import datetime

def global_dates(request):
    return {
        'today': datetime.now(),
    }