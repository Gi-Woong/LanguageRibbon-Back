from django.http import JsonResponse, HttpResponseRedirect


# TODO: 임시로 만든 home 컨트롤러임(추후 삭제 필요)
def home(request):
    data = {
        "message": "welcome!",
        "login": False
    }
    if request.user.is_authenticated:
        data["login"] = True
    return JsonResponse(data)