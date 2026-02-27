from datetime import datetime

def global_dates(request):
    """
    Returns a dictionary of date-related variables 
    available to all templates.
    """
    return {
        'today': datetime.now(),
    }