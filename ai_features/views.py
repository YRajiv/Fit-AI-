from django.shortcuts import render
def posture_check(request):
    # Change 'ai_features/posture_check.html' to match your current setup:
    return render(request, 'ai_posture/ai_posture.html')